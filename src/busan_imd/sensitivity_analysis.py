"""Test 2025 B-IMD rank stability under weight and missing-domain scenarios."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from busan_imd.composite_index import DEFAULT_DOMAIN_SCORES, DEFAULT_SPEC, load_weights
from busan_imd.core.artifacts import sha256_file, write_json
from busan_imd.domain_scores import IDENTITY_COLUMNS

DEFAULT_SCENARIOS = Path("docs/data/SENSITIVITY_SCENARIOS_2025.csv")
DEFAULT_OUTPUT = Path("data/processed/scores/2025/busan_admin_dong_sensitivity_2025.csv")
DEFAULT_REPORT = Path("docs/data/manifests/SENSITIVITY_ANALYSIS_REPORT_2025.json")
SUPPORTED_WEIGHT_POLICIES = {"baseline", "equal"}
SUPPORTED_MISSING_POLICIES = {
    "complete_case",
    "median_imputation",
    "renormalize_after_systematic_omission",
}


@dataclass(frozen=True)
class Scenario:
    """Executable sensitivity-scenario contract."""

    scenario_id: str
    scenario_type: str
    weight_policy: str
    missing_policy: str
    omitted_domain: str
    rationale: str


def load_scenarios(path: Path = DEFAULT_SCENARIOS) -> list[Scenario]:
    """Read and validate the versioned sensitivity contract."""
    frame = pd.read_csv(path, keep_default_na=False)
    required = set(Scenario.__dataclass_fields__)
    if set(frame.columns) != required:
        raise ValueError(f"Sensitivity scenario columns must be {sorted(required)}")
    if frame["scenario_id"].duplicated().any():
        raise ValueError("Sensitivity scenario IDs must be unique")
    if set(frame["weight_policy"]) - SUPPORTED_WEIGHT_POLICIES:
        raise ValueError("Unsupported sensitivity weight policy")
    if set(frame["missing_policy"]) - SUPPORTED_MISSING_POLICIES:
        raise ValueError("Unsupported sensitivity missing policy")
    if (frame["scenario_id"] == "baseline").sum() != 1:
        raise ValueError("Sensitivity scenarios must contain exactly one baseline")
    return [Scenario(**row) for row in frame.to_dict(orient="records")]


def _rank(values: pd.Series, codes: pd.Series) -> pd.DataFrame:
    ranked = pd.DataFrame({"_score_exact": values, "admin_dong_code": codes}).sort_values(
        ["_score_exact", "admin_dong_code"], ascending=[False, True], kind="stable"
    )
    ranked["sensitivity_rank"] = np.arange(1, len(ranked) + 1)
    ranked["sensitivity_decile"] = (
        ((ranked["sensitivity_rank"] - 1) * 10 // len(ranked)) + 1
    ).astype(int)
    ranked["sensitivity_score_0_100"] = ranked["_score_exact"].round(6)
    return ranked.drop(columns="_score_exact")


def _scenario_scores(
    values: pd.DataFrame,
    base_weights: pd.Series,
    scenario: Scenario,
) -> pd.Series:
    scenario_values = values.copy()
    if scenario.omitted_domain:
        if scenario.omitted_domain not in scenario_values:
            raise ValueError(f"Unknown omitted domain: {scenario.omitted_domain}")
        scenario_values[scenario.omitted_domain] = np.nan

    weights = base_weights.copy()
    if scenario.weight_policy == "equal":
        weights[:] = 1.0 / len(weights)

    if scenario.missing_policy == "median_imputation":
        scenario_values = scenario_values.fillna(scenario_values.median())
    elif scenario.missing_policy == "complete_case":
        if scenario_values.isna().any().any():
            raise ValueError("Complete-case scenario requires complete domain scores")
    elif scenario.missing_policy != "renormalize_after_systematic_omission":
        raise ValueError(f"Unsupported missing policy: {scenario.missing_policy}")

    available = scenario_values.notna().astype(float)
    denominator = available.mul(weights, axis="columns").sum(axis="columns")
    if (denominator <= 0).any():
        raise ValueError("Every row must retain at least one weighted domain")
    numerator = scenario_values.fillna(0.0).mul(weights, axis="columns").sum(axis="columns")
    return numerator / denominator


def build(
    domain_scores: pd.DataFrame,
    base_weights: pd.Series,
    scenarios: list[Scenario],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build long-form scenario scores and rank-stability metrics."""
    codes = domain_scores["admin_dong_code"].astype(str)
    if len(domain_scores) != 206 or codes.duplicated().any():
        raise ValueError("Sensitivity analysis requires 206 unique administrative-dong rows")
    if not scenarios or len({item.scenario_id for item in scenarios}) != len(scenarios):
        raise ValueError("Sensitivity scenarios must be non-empty and unique")
    if [item.scenario_id for item in scenarios].count("baseline") != 1:
        raise ValueError("Sensitivity analysis requires exactly one baseline scenario")
    if not np.isclose(base_weights.sum(), 1.0) or (base_weights <= 0).any():
        raise ValueError("Baseline domain weights must be positive and sum to one")

    columns = {domain: f"{domain}_score_0_100" for domain in base_weights.index}
    missing = sorted(set(columns.values()) - set(domain_scores.columns))
    if missing:
        raise ValueError(f"Domain-score input is missing columns: {missing}")
    values = domain_scores[list(columns.values())].rename(
        columns={column: domain for domain, column in columns.items()}
    )
    values = values.apply(pd.to_numeric, errors="raise")
    finite = values.notna() & np.isfinite(values)
    if not finite.where(values.notna(), True).all().all():
        raise ValueError("Non-missing domain scores must be finite")
    if (((values < 0) | (values > 100)) & values.notna()).any().any():
        raise ValueError("Domain scores must be between 0 and 100")

    frames: list[pd.DataFrame] = []
    for scenario in scenarios:
        scores = _scenario_scores(values, base_weights, scenario)
        ranked = _rank(scores, codes)
        ranked = domain_scores[IDENTITY_COLUMNS].merge(
            ranked, on="admin_dong_code", how="left", validate="one_to_one"
        )
        ranked.insert(0, "scenario_id", scenario.scenario_id)
        frames.append(ranked)

    output = pd.concat(frames, ignore_index=True)
    baseline = output[output["scenario_id"] == "baseline"].set_index("admin_dong_code")
    baseline_rank = baseline["sensitivity_rank"]
    baseline_decile = baseline["sensitivity_decile"]
    summaries: dict[str, dict[str, Any]] = {}
    augmented: list[pd.DataFrame] = []
    for scenario in scenarios:
        frame = output[output["scenario_id"] == scenario.scenario_id].copy()
        indexed = frame.set_index("admin_dong_code")
        rank_change = indexed["sensitivity_rank"] - baseline_rank
        decile_change = indexed["sensitivity_decile"] - baseline_decile
        frame["rank_change_from_baseline"] = frame["admin_dong_code"].map(rank_change)
        frame["absolute_rank_change"] = frame["rank_change_from_baseline"].abs()
        frame["decile_change_from_baseline"] = frame["admin_dong_code"].map(decile_change)
        augmented.append(frame)

        scenario_rank = indexed["sensitivity_rank"]
        scenario_decile = indexed["sensitivity_decile"]
        baseline_top = set(baseline.index[baseline_decile == 1])
        scenario_top = set(indexed.index[scenario_decile == 1])
        overlap = len(baseline_top & scenario_top)
        summaries[scenario.scenario_id] = {
            "scenario_type": scenario.scenario_type,
            "weight_policy": scenario.weight_policy,
            "missing_policy": scenario.missing_policy,
            "omitted_domain": scenario.omitted_domain or None,
            "spearman_rank_correlation": round(float(baseline_rank.corr(scenario_rank)), 6),
            "mean_absolute_rank_change": round(float(rank_change.abs().mean()), 6),
            "maximum_absolute_rank_change": int(rank_change.abs().max()),
            "decile_agreement_rate": round(float((baseline_decile == scenario_decile).mean()), 6),
            "top_decile_overlap_count": overlap,
            "top_decile_overlap_rate": round(overlap / len(baseline_top), 6),
        }

    output = pd.concat(augmented, ignore_index=True)
    output = output[
        [
            "scenario_id",
            *IDENTITY_COLUMNS,
            "sensitivity_score_0_100",
            "sensitivity_rank",
            "sensitivity_decile",
            "rank_change_from_baseline",
            "absolute_rank_change",
            "decile_change_from_baseline",
        ]
    ]
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "reference_year": 2025,
        "record_count": len(domain_scores),
        "scenario_count": len(scenarios),
        "actual_missing_domain_score_count": int(values.isna().sum().sum()),
        "actual_missing_by_domain": {
            domain: int(count) for domain, count in values.isna().sum().items()
        },
        "interpretation": (
            "Rank stability stress test; systematic omission scenarios are not claims that "
            "the omitted domain is actually missing"
        ),
        "rank_change_direction": "positive means less deprived than in the baseline rank",
        "scenario_summaries": summaries,
    }
    return output, report


def run(
    domain_scores_path: Path = DEFAULT_DOMAIN_SCORES,
    weight_spec_path: Path = DEFAULT_SPEC,
    scenario_path: Path = DEFAULT_SCENARIOS,
    output_path: Path = DEFAULT_OUTPUT,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    """Read inputs and write deterministic sensitivity artifacts."""
    domain_scores = pd.read_csv(domain_scores_path, dtype={"admin_dong_code": str})
    weights = load_weights(weight_spec_path)
    base_weights = pd.Series(
        {weight.domain: weight.scored_model_weight for weight in weights}, dtype=float
    )
    scenarios = load_scenarios(scenario_path)
    output, report = build(domain_scores, base_weights, scenarios)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False, encoding="utf-8-sig")
    report.update(
        {
            "domain_scores_path": domain_scores_path.as_posix(),
            "domain_scores_sha256": sha256_file(domain_scores_path),
            "weight_spec_path": weight_spec_path.as_posix(),
            "weight_spec_sha256": sha256_file(weight_spec_path),
            "scenario_path": scenario_path.as_posix(),
            "scenario_sha256": sha256_file(scenario_path),
            "output_path": output_path.as_posix(),
            "output_sha256": sha256_file(output_path),
        }
    )
    write_json(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain-scores", type=Path, default=DEFAULT_DOMAIN_SCORES)
    parser.add_argument("--weight-spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run(
        args.domain_scores, args.weight_spec, args.scenarios, args.output, args.report
    )
    print(
        f"tested {report['scenario_count']} sensitivity scenarios across "
        f"{report['record_count']} administrative dongs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
