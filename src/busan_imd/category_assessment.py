"""Build transparent category-level assessments for the policy dashboard."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from busan_imd.core.artifacts import sha256_file, write_json
from busan_imd.domain_scores import DEFAULT_PROFILE, percentile_score

DEFAULT_SPEC = Path("docs/data/CATEGORY_ASSESSMENT_SPEC_2025.csv")
DEFAULT_POLICY_CATALOG = Path("docs/data/CATEGORY_POLICY_CATALOG_2025.csv")
DEFAULT_OUTPUT_DIR = Path("outputs/infographic")
DEFAULT_CATEGORY_OUTPUT = DEFAULT_OUTPUT_DIR / "busan_admin_dong_category_assessment_2025.csv"
DEFAULT_INDICATOR_OUTPUT = (
    DEFAULT_OUTPUT_DIR / "busan_admin_dong_category_indicator_scores_2025.csv"
)
DEFAULT_REPORT = Path("docs/data/manifests/CATEGORY_ASSESSMENT_REPORT_2025.json")
EXPECTED_DONG_COUNT = 206
SHRINKAGE_POPULATION = 5_000
IDENTITY_COLUMNS = ["admin_dong_code", "sigungu_name", "admin_dong_name"]
SPEC_COLUMNS = [
    "category",
    "category_label",
    "indicator",
    "indicator_label",
    "direction",
    "weight",
    "evidence_type",
    "base_confidence",
    "quality_note",
]


def _smoothed_rate(
    count: pd.Series,
    population: pd.Series,
    scale: float,
    prior_population: int = SHRINKAGE_POPULATION,
) -> pd.Series:
    count = pd.to_numeric(count, errors="raise").astype(float)
    population = pd.to_numeric(population, errors="raise").astype(float)
    global_rate = count.sum() / population.sum()
    return (count + global_rate * prior_population) / (population + prior_population) * scale


def derive_indicators(profile: pd.DataFrame) -> pd.DataFrame:
    """Add explicitly named derived proxies without representing them as observations."""
    derived = profile.copy()
    population = derived["total_population_2025"]
    rate_inputs = {
        "workplace_workers_per_1000_population_2024_smoothed": (
            "workplace_workers_2024",
            1_000,
        ),
        "establishments_per_1000_population_2024_smoothed": ("establishments_2024", 1_000),
        "hospital_per_10000_smoothed": ("hospital_count_2025_candidate", 10_000),
        "clinic_per_10000_smoothed": ("clinic_count_2025_candidate", 10_000),
        "bus_stops_per_10000_smoothed": ("bus_stop_count_2025", 10_000),
        "heat_shelters_per_10000_smoothed": ("heat_shelter_count_2025", 10_000),
        "elderly_alone_per_1000_smoothed": ("elderly_alone_latest_count", 1_000),
    }
    for output, (count_column, scale) in rate_inputs.items():
        derived[output] = _smoothed_rate(derived[count_column], population, scale)
    return derived


def load_spec(path: Path = DEFAULT_SPEC) -> pd.DataFrame:
    """Load and validate the versioned dashboard assessment contract."""
    spec = pd.read_csv(path)
    if list(spec.columns) != SPEC_COLUMNS:
        raise ValueError(f"Category assessment spec columns must be {SPEC_COLUMNS}")
    if spec["indicator"].duplicated().any():
        raise ValueError("Category assessment indicators must be unique")
    if not set(spec["direction"]) <= {"higher", "lower"}:
        raise ValueError("Category assessment direction must be higher or lower")
    weights = spec.groupby("category")["weight"].sum()
    if not np.allclose(weights.to_numpy(dtype=float), 1.0):
        raise ValueError("Category assessment weights must sum to one within each category")
    return spec


def _confidence(profile: pd.DataFrame, rule: Any) -> pd.Series:
    confidence = pd.Series(rule.base_confidence, index=profile.index, dtype="object")
    if rule.category == "income_support_need":
        confidence = profile["inference_quality_tier"].map(
            {"C1_observed_pattern_rescaled": "medium_low", "C2_model_pattern_rescaled": "low"}
        )
    elif rule.category == "air_exposure":
        confidence = pd.Series(
            np.where(profile["nearest_air_station_distance_m"] > 3_000, "low", "medium_low"),
            index=profile.index,
        )
    elif rule.category == "transit_access":
        confidence = pd.Series(
            np.where(profile["bus_stop_count_2025"] == 0, "low", "medium_low"),
            index=profile.index,
        )
    if confidence.isna().any():
        raise ValueError(f"Missing confidence classification for {rule.indicator}")
    return confidence


def build(
    profile: pd.DataFrame,
    spec: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Build long indicator evidence and one row per dong-category assessment."""
    if len(profile) != EXPECTED_DONG_COUNT or profile["admin_dong_code"].duplicated().any():
        raise ValueError("Category assessment requires 206 unique administrative-dong rows")
    derived = derive_indicators(profile)
    missing = sorted(set(spec["indicator"]) - set(derived.columns))
    if missing:
        raise ValueError(f"Profile is missing category assessment indicators: {missing}")

    frames: list[pd.DataFrame] = []
    for rule in spec.itertuples(index=False):
        values = pd.to_numeric(derived[rule.indicator], errors="raise").astype(float)
        score = percentile_score(values, rule.direction)
        frames.append(
            pd.DataFrame(
                {
                    **{column: profile[column] for column in IDENTITY_COLUMNS},
                    "category": rule.category,
                    "category_label": rule.category_label,
                    "indicator": rule.indicator,
                    "indicator_label": rule.indicator_label,
                    "raw_or_derived_value": values.round(6),
                    "deprivation_percentile_0_100": score.round(6),
                    "within_category_weight": float(rule.weight),
                    "weighted_score": (score * float(rule.weight)).round(6),
                    "evidence_type": rule.evidence_type,
                    "confidence_level": _confidence(derived, rule),
                    "quality_note": rule.quality_note,
                    "indicator_policy_triggered": score >= 70,
                }
            )
        )
    indicator_scores = pd.concat(frames, ignore_index=True)
    grouped = indicator_scores.groupby(
        [*IDENTITY_COLUMNS, "category", "category_label"], sort=True, observed=True
    )
    category_scores = grouped.agg(
        category_score_0_100=("weighted_score", "sum"),
        triggered_indicator_count=("indicator_policy_triggered", "sum"),
    ).reset_index()
    triggered = (
        indicator_scores[indicator_scores["indicator_policy_triggered"]]
        .groupby(["admin_dong_code", "category"], observed=True)["indicator_label"]
        .agg("|".join)
        .rename("triggered_indicators")
        .reset_index()
    )
    category_scores = category_scores.merge(
        triggered,
        on=["admin_dong_code", "category"],
        how="left",
        validate="one_to_one",
    )
    category_scores["triggered_indicators"] = category_scores["triggered_indicators"].fillna("")
    category_scores["policy_review_status"] = np.where(
        category_scores["category_score_0_100"] >= 70,
        "candidate_after_validation",
        "monitor",
    )
    confidence_rank = {"low": 0, "medium_low": 1, "medium": 2}
    confidence = (
        indicator_scores.assign(
            _confidence_rank=indicator_scores["confidence_level"].map(confidence_rank)
        )
        .groupby(["admin_dong_code", "category"], observed=True)["_confidence_rank"]
        .min()
        .map({value: key for key, value in confidence_rank.items()})
        .rename("category_confidence")
        .reset_index()
    )
    category_scores = category_scores.merge(
        confidence,
        on=["admin_dong_code", "category"],
        validate="one_to_one",
    ).sort_values(["category", "category_score_0_100"], ascending=[True, False])
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "reference_year": 2025,
        "admin_dong_count": EXPECTED_DONG_COUNT,
        "category_count": int(spec["category"].nunique()),
        "indicator_count": len(spec),
        "indicator_score_row_count": len(indicator_scores),
        "category_score_row_count": len(category_scores),
        "policy_trigger_threshold": 70,
        "small_area_rate_shrinkage_population": SHRINKAGE_POPULATION,
        "decision": "use_for_transparent_category_policy_screening_after_validation",
        "limitations": [
            "Estimated and proxy inputs are retained with row-level evidence labels",
            "Category scores are relative Busan percentiles, not absolute service standards",
            "Policy examples require observed administrative data and field validation",
        ],
    }
    return indicator_scores, category_scores.reset_index(drop=True), report


def run(
    profile_path: Path = DEFAULT_PROFILE,
    spec_path: Path = DEFAULT_SPEC,
    policy_catalog_path: Path = DEFAULT_POLICY_CATALOG,
    category_output: Path = DEFAULT_CATEGORY_OUTPUT,
    indicator_output: Path = DEFAULT_INDICATOR_OUTPUT,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    """Read canonical inputs and write reproducible dashboard assessment artifacts."""
    profile = pd.read_csv(profile_path, dtype={"admin_dong_code": str})
    spec = load_spec(spec_path)
    policies = pd.read_csv(policy_catalog_path)
    if set(policies["category"]) != set(spec["category"]):
        raise ValueError("Every category requires exactly one dashboard policy example")
    indicator_scores, category_scores, report = build(profile, spec)
    category_output.parent.mkdir(parents=True, exist_ok=True)
    category_scores.to_csv(category_output, index=False, encoding="utf-8-sig", lineterminator="\n")
    indicator_scores.to_csv(
        indicator_output,
        index=False,
        encoding="utf-8-sig",
        lineterminator="\n",
    )
    report.update(
        {
            "input_paths": {
                "profile": profile_path.as_posix(),
                "spec": spec_path.as_posix(),
                "policy_catalog": policy_catalog_path.as_posix(),
            },
            "input_sha256": {
                "profile": sha256_file(profile_path),
                "spec": sha256_file(spec_path),
                "policy_catalog": sha256_file(policy_catalog_path),
            },
            "output_paths": {
                "category_assessment": category_output.as_posix(),
                "indicator_scores": indicator_output.as_posix(),
            },
            "output_sha256": {
                "category_assessment": sha256_file(category_output),
                "indicator_scores": sha256_file(indicator_output),
            },
        }
    )
    write_json(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--policy-catalog", type=Path, default=DEFAULT_POLICY_CATALOG)
    parser.add_argument("--category-output", type=Path, default=DEFAULT_CATEGORY_OUTPUT)
    parser.add_argument("--indicator-output", type=Path, default=DEFAULT_INDICATOR_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run(
        args.profile,
        args.spec,
        args.policy_catalog,
        args.category_output,
        args.indicator_output,
        args.report,
    )
    print(
        f"built {report['category_count']} categories and "
        f"{report['indicator_count']} transparent indicators"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
