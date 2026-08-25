"""Build transparent category-level assessments for the policy dashboard."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd

from busan_imd.analysis.domain_scores import DEFAULT_PROFILE, percentile_score
from busan_imd.core.artifacts import sha256_file, write_json

DEFAULT_SPEC = Path("docs/data/CATEGORY_ASSESSMENT_SPEC_2025.csv")
DEFAULT_POLICY_CATALOG = Path("docs/data/CATEGORY_POLICY_CATALOG_2025.csv")
DEFAULT_OUTPUT_DIR = Path("outputs/infographic/2025/tables")
DEFAULT_CATEGORY_OUTPUT = DEFAULT_OUTPUT_DIR / "busan_admin_dong_category_assessment_2025.csv"
DEFAULT_MAJOR_CATEGORY_OUTPUT = (
    DEFAULT_OUTPUT_DIR / "busan_admin_dong_major_category_assessment_2025.csv"
)
DEFAULT_INDICATOR_OUTPUT = (
    DEFAULT_OUTPUT_DIR / "busan_admin_dong_category_indicator_scores_2025.csv"
)
DEFAULT_REPORT = Path("docs/data/manifests/CATEGORY_ASSESSMENT_REPORT_2025.json")
DEFAULT_BOUNDARIES = Path(
    "data/raw/sgis/admin_boundaries/2025/busan_admin_dong_boundaries_2025_valid.geojson"
)
DEFAULT_TRAFFIC_HOTSPOTS = Path(
    "data/raw/koroad/traffic_accidents/hotspots/2024/"
    "busan_traffic_accident_hotspots_2024.csv"
)
EXPECTED_DONG_COUNT = 206
SHRINKAGE_POPULATION = 5_000
IDENTITY_COLUMNS = ["admin_dong_code", "sigungu_name", "admin_dong_name"]
SPEC_COLUMNS = [
    "category",
    "category_label",
    "major_category",
    "major_category_label",
    "major_category_weight",
    "indicator",
    "indicator_label",
    "direction",
    "weight",
    "evidence_type",
    "value_status_ko",
    "estimate_used",
    "estimation_method_ko",
    "estimation_reason",
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
        "pharmacy_per_10000_smoothed": ("pharmacy_count_2025_candidate", 10_000),
        "crime_prevention_cctv_per_1000_smoothed": (
            "crime_prevention_cctv_count_2025",
            1_000,
        ),
        "bus_stops_per_10000_smoothed": ("bus_stop_count_2025", 10_000),
        "heat_shelters_per_10000_smoothed": ("heat_shelter_count_2025", 10_000),
        "elderly_alone_per_1000_smoothed": ("elderly_alone_latest_count", 1_000),
    }
    for output, (count_column, scale) in rate_inputs.items():
        derived[output] = _smoothed_rate(derived[count_column], population, scale)
    return derived


def add_traffic_hotspot_indicator(
    profile: pd.DataFrame,
    boundaries: gpd.GeoDataFrame,
    traffic_hotspots: pd.DataFrame,
) -> pd.DataFrame:
    """Attach selected-hotspot occurrences without treating non-selection as zero accidents."""
    required_boundary_columns = {"adm_cd", "geometry"}
    required_hotspot_columns = {"lo_crd", "la_crd", "occrrnc_cnt"}
    if not required_boundary_columns <= set(boundaries.columns):
        raise ValueError("Traffic scoring boundaries require adm_cd and geometry")
    if not required_hotspot_columns <= set(traffic_hotspots.columns):
        raise ValueError("Traffic hotspots require lo_crd, la_crd, and occrrnc_cnt")
    points = gpd.GeoDataFrame(
        traffic_hotspots.copy(),
        geometry=gpd.points_from_xy(traffic_hotspots["lo_crd"], traffic_hotspots["la_crd"]),
        crs="EPSG:4326",
    ).to_crs(boundaries.crs)
    mapped = gpd.sjoin(
        points,
        boundaries[["adm_cd", "geometry"]],
        how="left",
        predicate="within",
    )
    if mapped["adm_cd"].isna().any():
        raise ValueError("Every selected traffic hotspot must map to an administrative dong")
    occurrences = mapped.groupby("adm_cd", observed=True)["occrrnc_cnt"].sum()
    result = profile.copy()
    result["selected_traffic_hotspot_occurrences_2024"] = (
        result["admin_dong_code"].astype(str).map(occurrences).fillna(0).astype(int)
    )
    return result


def _score_indicator(values: pd.Series, rule: Any) -> pd.Series:
    if rule.indicator != "selected_traffic_hotspot_occurrences_2024":
        return percentile_score(values, rule.direction)
    score = pd.Series(0.0, index=values.index)
    selected = values > 0
    score.loc[selected] = values.loc[selected].rank(method="average", pct=True) * 100.0
    return score


def load_spec(path: Path = DEFAULT_SPEC) -> pd.DataFrame:
    """Load and validate the versioned dashboard assessment contract."""
    spec = pd.read_csv(path)
    if list(spec.columns) != SPEC_COLUMNS:
        raise ValueError(f"Category assessment spec columns must be {SPEC_COLUMNS}")
    if spec["indicator"].duplicated().any():
        raise ValueError("Category assessment indicators must be unique")
    if not set(spec["direction"]) <= {"higher", "lower"}:
        raise ValueError("Category assessment direction must be higher or lower")
    estimate_flags = spec["estimate_used"].astype(str).str.lower()
    if not set(estimate_flags) <= {"true", "false"}:
        raise ValueError("Category assessment estimate_used must be true or false")
    if spec[["value_status_ko", "estimation_method_ko", "estimation_reason"]].isna().any().any():
        raise ValueError("Category assessment estimation disclosure must be complete")
    weights = spec.groupby("category")["weight"].sum()
    if not np.allclose(weights.to_numpy(dtype=float), 1.0):
        raise ValueError("Category assessment weights must sum to one within each category")
    category_contract = spec[
        ["category", "major_category", "major_category_label", "major_category_weight"]
    ].drop_duplicates()
    if category_contract["category"].duplicated().any():
        raise ValueError("Each child category must map to exactly one major category")
    major_weights = category_contract.groupby("major_category")["major_category_weight"].sum()
    if not np.allclose(major_weights.to_numpy(dtype=float), 1.0):
        raise ValueError("Child-category weights must sum to one within each major category")
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
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
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
        score = _score_indicator(values, rule)
        frames.append(
            pd.DataFrame(
                {
                    **{column: profile[column] for column in IDENTITY_COLUMNS},
                    "category": rule.category,
                    "category_label": rule.category_label,
                    "major_category": rule.major_category,
                    "major_category_label": rule.major_category_label,
                    "major_category_weight": float(rule.major_category_weight),
                    "indicator": rule.indicator,
                    "indicator_label": rule.indicator_label,
                    "raw_or_derived_value": values.round(6),
                    "deprivation_percentile_0_100": score.round(6),
                    "within_category_weight": float(rule.weight),
                    "weighted_score": (score * float(rule.weight)).round(6),
                    "evidence_type": rule.evidence_type,
                    "value_status_ko": rule.value_status_ko,
                    "estimate_used": str(rule.estimate_used).lower() == "true",
                    "estimation_method_ko": rule.estimation_method_ko,
                    "estimation_reason": rule.estimation_reason,
                    "confidence_level": _confidence(derived, rule),
                    "quality_note": rule.quality_note,
                    "indicator_policy_triggered": score >= 70,
                }
            )
        )
    indicator_scores = pd.concat(frames, ignore_index=True)
    grouped = indicator_scores.groupby(
        [
            *IDENTITY_COLUMNS,
            "major_category",
            "major_category_label",
            "major_category_weight",
            "category",
            "category_label",
        ],
        sort=True,
        observed=True,
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
    major_source = category_scores.assign(
        _major_weighted_score=(
            category_scores["category_score_0_100"] * category_scores["major_category_weight"]
        )
    )
    major_scores = (
        major_source.groupby(
            [*IDENTITY_COLUMNS, "major_category", "major_category_label"],
            sort=True,
            observed=True,
        )
        .agg(
            major_category_score_0_100=("_major_weighted_score", "sum"),
            child_category_count=("category", "nunique"),
        )
        .reset_index()
    )
    triggered_children = (
        category_scores[category_scores["category_score_0_100"] >= 70]
        .groupby(["admin_dong_code", "major_category"], observed=True)["category_label"]
        .agg("|".join)
        .rename("triggered_child_categories")
        .reset_index()
    )
    major_scores = major_scores.merge(
        triggered_children,
        on=["admin_dong_code", "major_category"],
        how="left",
        validate="one_to_one",
    )
    major_scores["triggered_child_categories"] = major_scores["triggered_child_categories"].fillna(
        ""
    )
    major_confidence = (
        category_scores.assign(
            _confidence_rank=category_scores["category_confidence"].map(confidence_rank)
        )
        .groupby(["admin_dong_code", "major_category"], observed=True)["_confidence_rank"]
        .min()
        .map({value: key for key, value in confidence_rank.items()})
        .rename("major_category_confidence")
        .reset_index()
    )
    major_scores = major_scores.merge(
        major_confidence,
        on=["admin_dong_code", "major_category"],
        validate="one_to_one",
    )
    major_scores["policy_review_status"] = np.where(
        major_scores["major_category_score_0_100"] >= 70,
        "candidate_after_validation",
        "monitor",
    )
    major_scores = major_scores.sort_values(
        ["major_category", "major_category_score_0_100"], ascending=[True, False]
    ).reset_index(drop=True)
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "reference_year": 2025,
        "admin_dong_count": EXPECTED_DONG_COUNT,
        "category_count": int(spec["category"].nunique()),
        "major_category_count": int(spec["major_category"].nunique()),
        "indicator_count": len(spec),
        "indicator_score_row_count": len(indicator_scores),
        "category_score_row_count": len(category_scores),
        "major_category_score_row_count": len(major_scores),
        "policy_trigger_threshold": 70,
        "small_area_rate_shrinkage_population": SHRINKAGE_POPULATION,
        "decision": "use_for_transparent_category_policy_screening_after_validation",
        "limitations": [
            "Estimated and proxy inputs are retained with row-level evidence labels",
            "Category scores are relative Busan percentiles, not absolute service standards",
            "Traffic safety uses 48 selected hotspots, not a complete dong-level crash census",
            "Policy examples require observed administrative data and field validation",
        ],
    }
    return indicator_scores, category_scores.reset_index(drop=True), major_scores, report


def run(
    profile_path: Path = DEFAULT_PROFILE,
    spec_path: Path = DEFAULT_SPEC,
    policy_catalog_path: Path = DEFAULT_POLICY_CATALOG,
    category_output: Path = DEFAULT_CATEGORY_OUTPUT,
    major_category_output: Path = DEFAULT_MAJOR_CATEGORY_OUTPUT,
    indicator_output: Path = DEFAULT_INDICATOR_OUTPUT,
    report_path: Path = DEFAULT_REPORT,
    boundaries_path: Path = DEFAULT_BOUNDARIES,
    traffic_hotspots_path: Path = DEFAULT_TRAFFIC_HOTSPOTS,
) -> dict[str, Any]:
    """Read canonical inputs and write reproducible dashboard assessment artifacts."""
    profile = pd.read_csv(profile_path, dtype={"admin_dong_code": str})
    boundaries = gpd.read_file(boundaries_path)
    traffic_hotspots = pd.read_csv(traffic_hotspots_path)
    profile = add_traffic_hotspot_indicator(profile, boundaries, traffic_hotspots)
    spec = load_spec(spec_path)
    policies = pd.read_csv(policy_catalog_path)
    if set(policies["category"]) != set(spec["category"]):
        raise ValueError("Every category requires exactly one dashboard policy example")
    indicator_scores, category_scores, major_scores, report = build(profile, spec)
    category_output.parent.mkdir(parents=True, exist_ok=True)
    category_scores.to_csv(category_output, index=False, encoding="utf-8-sig", lineterminator="\n")
    major_scores.to_csv(
        major_category_output,
        index=False,
        encoding="utf-8-sig",
        lineterminator="\n",
    )
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
                "boundaries": boundaries_path.as_posix(),
                "traffic_accident_hotspots": traffic_hotspots_path.as_posix(),
            },
            "input_sha256": {
                "profile": sha256_file(profile_path),
                "spec": sha256_file(spec_path),
                "policy_catalog": sha256_file(policy_catalog_path),
                "boundaries": sha256_file(boundaries_path),
                "traffic_accident_hotspots": sha256_file(traffic_hotspots_path),
            },
            "output_paths": {
                "category_assessment": category_output.as_posix(),
                "major_category_assessment": major_category_output.as_posix(),
                "indicator_scores": indicator_output.as_posix(),
            },
            "output_sha256": {
                "category_assessment": sha256_file(category_output),
                "major_category_assessment": sha256_file(major_category_output),
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
    parser.add_argument(
        "--major-category-output",
        type=Path,
        default=DEFAULT_MAJOR_CATEGORY_OUTPUT,
    )
    parser.add_argument("--indicator-output", type=Path, default=DEFAULT_INDICATOR_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--boundaries", type=Path, default=DEFAULT_BOUNDARIES)
    parser.add_argument("--traffic-hotspots", type=Path, default=DEFAULT_TRAFFIC_HOTSPOTS)
    args = parser.parse_args()
    report = run(
        args.profile,
        args.spec,
        args.policy_catalog,
        args.category_output,
        args.major_category_output,
        args.indicator_output,
        args.report,
        args.boundaries,
        args.traffic_hotspots,
    )
    print(
        f"built {report['major_category_count']} major categories, "
        f"{report['category_count']} child categories, and "
        f"{report['indicator_count']} transparent indicators"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
