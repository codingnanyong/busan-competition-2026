"""Normalize 2025 candidate indicators and calculate experimental domain scores."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from busan_imd.core.artifacts import sha256_file, write_json

DEFAULT_PROFILE = Path(
    "data/processed/standardized/2025/busan_admin_dong_candidate_profile_2025.csv"
)
DEFAULT_SPEC = Path("docs/data/tables/DOMAIN_SCORE_SPEC_2025.csv")
DEFAULT_OUTPUT_DIR = Path("data/processed/scores/2025")
DEFAULT_REPORT = Path("docs/data/manifests/DOMAIN_SCORE_REPORT_2025.json")
IDENTITY_COLUMNS = ["admin_dong_code", "sido_name", "sigungu_name", "admin_dong_name"]
EXPECTED_DOMAINS = {
    "income",
    "employment",
    "education",
    "health",
    "housing_access",
    "living_environment",
}
HELD_DOMAINS = {"safety": "No direct administrative-dong incident indicator is available"}


@dataclass(frozen=True)
class IndicatorRule:
    """Executable normalization contract for one base-model indicator."""

    domain: str
    indicator: str
    source_dataset_id: str
    input_transform: str
    deprivation_direction: str
    normalization: str
    within_domain_weight: float
    evidence_status: str
    quality_note: str


def load_rules(path: Path = DEFAULT_SPEC) -> list[IndicatorRule]:
    """Read and validate the versioned domain-score contract."""
    frame = pd.read_csv(path)
    required = set(IndicatorRule.__dataclass_fields__)
    if set(frame.columns) != required:
        raise ValueError(f"Domain-score specification columns must be {sorted(required)}")
    if frame["indicator"].duplicated().any():
        raise ValueError("Domain-score indicators must be unique")
    if not set(frame["domain"]) == EXPECTED_DOMAINS:
        raise ValueError("Domain-score specification must cover all six scored domains")
    if not set(frame["input_transform"]) <= {"identity", "log1p"}:
        raise ValueError("Unsupported input transform")
    if not set(frame["deprivation_direction"]) <= {"higher", "lower"}:
        raise ValueError("Unsupported deprivation direction")
    if set(frame["normalization"]) != {"percentile_rank"}:
        raise ValueError("The 2025 base model requires percentile-rank normalization")
    weights = frame.groupby("domain")["within_domain_weight"].sum()
    if (
        not np.allclose(weights.to_numpy(dtype=float), 1.0)
        or (frame["within_domain_weight"] <= 0).any()
    ):
        raise ValueError("Positive within-domain weights must sum to one")
    return [IndicatorRule(**row) for row in frame.to_dict(orient="records")]


def transform(values: pd.Series, method: str) -> pd.Series:
    """Apply the contract's monotonic input transform."""
    numeric = pd.to_numeric(values, errors="raise").astype(float)
    if not np.isfinite(numeric).all():
        raise ValueError("Scoring indicators must be complete and finite")
    if method == "identity":
        return numeric
    if method == "log1p":
        if (numeric < 0).any():
            raise ValueError("log1p indicators cannot be negative")
        return np.log1p(numeric)
    raise ValueError(f"Unsupported input transform: {method}")


def percentile_score(values: pd.Series, direction: str) -> pd.Series:
    """Map average ranks to 0-100, where a higher score means more deprivation."""
    numeric = pd.to_numeric(values, errors="raise").astype(float)
    if not np.isfinite(numeric).all() or numeric.nunique() <= 1:
        raise ValueError("Percentile normalization requires finite, non-constant values")
    score = (numeric.rank(method="average") - 1.0) / (len(numeric) - 1.0) * 100.0
    if direction == "lower":
        score = 100.0 - score
    elif direction != "higher":
        raise ValueError(f"Unsupported deprivation direction: {direction}")
    return score


def build(
    profile: pd.DataFrame, rules: list[IndicatorRule]
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Build long-form indicator scores and one row of scores per canonical dong."""
    if len(profile) != 206 or profile["admin_dong_code"].astype(str).duplicated().any():
        raise ValueError("Domain scoring requires 206 unique administrative-dong rows")
    missing = sorted({rule.indicator for rule in rules} - set(profile.columns))
    if missing:
        raise ValueError(f"Profile is missing contracted indicators: {missing}")
    scored_domains = sorted({rule.domain for rule in rules})

    indicator_frames: list[pd.DataFrame] = []
    for rule in rules:
        raw = pd.to_numeric(profile[rule.indicator], errors="raise").astype(float)
        transformed = transform(raw, rule.input_transform)
        score = percentile_score(transformed, rule.deprivation_direction)
        indicator_frames.append(
            pd.DataFrame(
                {
                    "admin_dong_code": profile["admin_dong_code"].astype(str),
                    "sigungu_name": profile["sigungu_name"],
                    "admin_dong_name": profile["admin_dong_name"],
                    "domain": rule.domain,
                    "indicator": rule.indicator,
                    "source_dataset_id": rule.source_dataset_id,
                    "raw_value": raw.round(6),
                    "transformed_value": transformed.round(6),
                    "deprivation_percentile_0_100": score.round(6),
                    "within_domain_weight": rule.within_domain_weight,
                    "weighted_score": (score * rule.within_domain_weight).round(6),
                    "evidence_status": rule.evidence_status,
                }
            )
        )
    indicator_scores = pd.concat(indicator_frames, ignore_index=True)

    totals = indicator_scores.groupby(["admin_dong_code", "domain"], sort=True, observed=True)[
        "weighted_score"
    ].sum()
    wide = totals.unstack("domain").reset_index()
    wide = wide.rename(columns={domain: f"{domain}_score_0_100" for domain in scored_domains})
    domain_scores = profile[IDENTITY_COLUMNS].merge(
        wide, on="admin_dong_code", how="left", validate="one_to_one"
    )
    score_columns = sorted(column for column in domain_scores if column.endswith("_score_0_100"))
    domain_scores = domain_scores[IDENTITY_COLUMNS + score_columns]
    if domain_scores[score_columns].isna().any().any():
        raise ValueError("Every canonical dong must receive every scored-domain value")

    summaries = {
        column.removesuffix("_score_0_100"): {
            "minimum": round(float(domain_scores[column].min()), 6),
            "median": round(float(domain_scores[column].median()), 6),
            "maximum": round(float(domain_scores[column].max()), 6),
        }
        for column in score_columns
    }
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "reference_year": 2025,
        "record_count": len(domain_scores),
        "indicator_count": len(rules),
        "scored_domains": scored_domains,
        "held_domains": HELD_DOMAINS,
        "normalization": "average percentile rank mapped to 0-100",
        "score_direction": "higher means greater relative deprivation",
        "within_domain_aggregation": "weighted arithmetic mean",
        "domain_summaries": summaries,
        "composite_score_created": False,
    }
    return indicator_scores, domain_scores, report


def run(
    profile_path: Path = DEFAULT_PROFILE,
    spec_path: Path = DEFAULT_SPEC,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    """Read canonical inputs and write deterministic indicator and domain scores."""
    profile = pd.read_csv(profile_path, dtype={"admin_dong_code": str})
    rules = load_rules(spec_path)
    indicator_scores, domain_scores, report = build(profile, rules)
    output_dir.mkdir(parents=True, exist_ok=True)
    indicator_path = output_dir / "busan_admin_dong_indicator_scores_2025.csv"
    domain_path = output_dir / "busan_admin_dong_domain_scores_2025.csv"
    indicator_scores.to_csv(indicator_path, index=False, encoding="utf-8-sig")
    domain_scores.to_csv(domain_path, index=False, encoding="utf-8-sig")
    report.update(
        {
            "profile_path": profile_path.as_posix(),
            "profile_sha256": sha256_file(profile_path),
            "spec_path": spec_path.as_posix(),
            "spec_sha256": sha256_file(spec_path),
            "output_paths": {
                "indicator_scores": indicator_path.as_posix(),
                "domain_scores": domain_path.as_posix(),
            },
            "output_sha256": {
                "indicator_scores": sha256_file(indicator_path),
                "domain_scores": sha256_file(domain_path),
            },
        }
    )
    write_json(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run(args.profile, args.spec, args.output_dir, args.report)
    print(
        f"scored {report['record_count']} administrative dongs across "
        f"{len(report['scored_domains'])} domains"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
