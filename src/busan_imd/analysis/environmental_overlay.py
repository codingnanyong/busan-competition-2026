"""Overlay 2025 ambient particulate exposure with B-IMD social vulnerability."""

from __future__ import annotations

import argparse
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from busan_imd.analysis.composite_index import DEFAULT_OUTPUT as DEFAULT_COMPOSITE
from busan_imd.core.artifacts import sha256_file, write_json
from busan_imd.processing.standardization import DEFAULT_OUTPUT_DIR as STANDARDIZED_OUTPUT_DIR

DEFAULT_PROFILE = STANDARDIZED_OUTPUT_DIR / "busan_admin_dong_candidate_profile_2025.csv"
DEFAULT_OUTPUT = Path("data/processed/scores/2025/busan_admin_dong_environmental_overlay_2025.csv")
DEFAULT_REPORT = Path("docs/data/manifests/ENVIRONMENTAL_OVERLAY_REPORT_2025.json")
EXPECTED_RECORD_COUNT = 206
HIGH_EXPOSURE_SHARE = 0.25
PM25_COLUMN = "annual_pm25_ug_m3_idw_2025"
PM10_COLUMN = "annual_pm10_ug_m3_idw_2025"
SOCIAL_DOMAIN_WEIGHTS = {
    "income": 0.225,
    "employment": 0.225,
    "education": 0.135,
    "health": 0.135,
    "housing_access": 0.093,
}


def _validate(composite: pd.DataFrame, profile: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    composite_required = {
        "admin_dong_code",
        "sigungu_name",
        "admin_dong_name",
        "b_imd_score_0_100",
        "b_imd_rank",
        "b_imd_decile",
        *(f"{domain}_score_0_100" for domain in SOCIAL_DOMAIN_WEIGHTS),
    }
    profile_required = {"admin_dong_code", PM25_COLUMN, PM10_COLUMN}
    missing_composite = sorted(composite_required - set(composite.columns))
    missing_profile = sorted(profile_required - set(profile.columns))
    if missing_composite:
        raise ValueError(f"Composite input is missing columns: {missing_composite}")
    if missing_profile:
        raise ValueError(f"Profile input is missing columns: {missing_profile}")

    composite = composite.copy()
    profile = profile.copy()
    composite["admin_dong_code"] = composite["admin_dong_code"].astype(str)
    profile["admin_dong_code"] = profile["admin_dong_code"].astype(str)
    for name, frame in (("Composite", composite), ("Profile", profile)):
        codes = frame["admin_dong_code"]
        if len(frame) != EXPECTED_RECORD_COUNT or codes.duplicated().any():
            raise ValueError(f"{name} input requires 206 unique administrative-dong rows")
    if set(composite["admin_dong_code"]) != set(profile["admin_dong_code"]):
        raise ValueError("Composite and profile administrative-dong codes must match exactly")

    composite_numeric = [
        "b_imd_score_0_100",
        "b_imd_rank",
        "b_imd_decile",
        *(f"{domain}_score_0_100" for domain in SOCIAL_DOMAIN_WEIGHTS),
    ]
    composite[composite_numeric] = composite[composite_numeric].apply(pd.to_numeric, errors="raise")
    profile[[PM25_COLUMN, PM10_COLUMN]] = profile[[PM25_COLUMN, PM10_COLUMN]].apply(
        pd.to_numeric, errors="raise"
    )
    values = pd.concat([composite[composite_numeric], profile[[PM25_COLUMN, PM10_COLUMN]]], axis=1)
    if not np.isfinite(values).all().all():
        raise ValueError("B-IMD and particulate exposure values must be finite")
    return composite, profile


def _spearman(left: pd.Series, right: pd.Series) -> float:
    return float(left.rank(method="average").corr(right.rank(method="average")))


def build(composite: pd.DataFrame, profile: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return deterministic ambient-air and social-vulnerability overlap results."""
    composite, profile = _validate(composite, profile)
    exposure = profile[["admin_dong_code", PM25_COLUMN, PM10_COLUMN]]
    overlay = composite[
        [
            "admin_dong_code",
            "sigungu_name",
            "admin_dong_name",
            "b_imd_score_0_100",
            "b_imd_rank",
            "b_imd_decile",
            *(f"{domain}_score_0_100" for domain in SOCIAL_DOMAIN_WEIGHTS),
        ]
    ].merge(exposure, on="admin_dong_code", validate="one_to_one")

    social_weight_total = sum(SOCIAL_DOMAIN_WEIGHTS.values())
    social_score = pd.Series(0.0, index=overlay.index)
    for domain, published_weight in SOCIAL_DOMAIN_WEIGHTS.items():
        social_score += overlay[f"{domain}_score_0_100"] * published_weight / social_weight_total
    social_ordered = (
        overlay.assign(_score_exact=social_score)
        .sort_values(
            ["_score_exact", "admin_dong_code"],
            ascending=[False, True],
            kind="stable",
        )
        .index
    )
    overlay["particulate_free_b_imd_score_0_100"] = social_score.round(6)
    overlay["particulate_free_b_imd_rank"] = 0
    overlay.loc[social_ordered, "particulate_free_b_imd_rank"] = np.arange(1, len(overlay) + 1)
    overlay["particulate_free_b_imd_decile"] = (
        (overlay["particulate_free_b_imd_rank"] - 1) * 10 // len(overlay) + 1
    ).astype(int)

    overlay["pm25_exposure_percentile"] = (
        overlay[PM25_COLUMN].rank(method="average", pct=True) * 100
    )
    overlay["pm10_exposure_percentile"] = (
        overlay[PM10_COLUMN].rank(method="average", pct=True) * 100
    )
    overlay["particulate_exposure_score_0_100"] = overlay[
        ["pm25_exposure_percentile", "pm10_exposure_percentile"]
    ].mean(axis=1)
    ordered = overlay.sort_values(
        ["particulate_exposure_score_0_100", "admin_dong_code"],
        ascending=[False, True],
        kind="stable",
    ).index
    overlay["particulate_exposure_rank"] = 0
    overlay.loc[ordered, "particulate_exposure_rank"] = np.arange(1, len(overlay) + 1)
    high_count = math.ceil(len(overlay) * HIGH_EXPOSURE_SHARE)
    overlay["high_particulate_exposure"] = overlay["particulate_exposure_rank"] <= high_count
    overlay["social_vulnerability_priority_area"] = overlay["particulate_free_b_imd_decile"] == 1
    overlay["double_burden"] = (
        overlay["high_particulate_exposure"] & overlay["social_vulnerability_priority_area"]
    )
    overlay["overlay_category"] = np.select(
        [
            overlay["double_burden"],
            overlay["social_vulnerability_priority_area"],
            overlay["high_particulate_exposure"],
        ],
        ["double_burden", "social_priority_only", "high_air_only"],
        default="neither",
    )
    overlay = overlay.sort_values(
        ["double_burden", "particulate_free_b_imd_rank", "particulate_exposure_rank"],
        ascending=[False, True, True],
        kind="stable",
    ).reset_index(drop=True)

    priority = overlay[overlay["social_vulnerability_priority_area"]]
    other = overlay[~overlay["social_vulnerability_priority_area"]]
    double_burden = overlay[overlay["double_burden"]].sort_values("particulate_free_b_imd_rank")
    report: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "reference_year": 2025,
        "record_count": len(overlay),
        "analysis_scope": (
            "ambient particulate exposure and particulate-independent social vulnerability overlap"
        ),
        "exposure_definition": (
            "mean of Busan-wide percentile ranks for annual 2025 PM2.5 and PM10 IDW estimates"
        ),
        "high_exposure_rule": "top 25 percent by particulate exposure score",
        "high_exposure_count": int(overlay["high_particulate_exposure"].sum()),
        "social_vulnerability_definition": (
            "published B-IMD weights renormalized across income, employment, education, "
            "health, and housing/access; the living-environment domain is excluded to avoid "
            "reusing PM2.5"
        ),
        "social_domain_published_weights": SOCIAL_DOMAIN_WEIGHTS,
        "priority_area_rule": "particulate-free B-IMD decile 1",
        "priority_area_count": int(overlay["social_vulnerability_priority_area"].sum()),
        "double_burden_rule": ("high particulate exposure and particulate-free B-IMD decile 1"),
        "double_burden_count": int(overlay["double_burden"].sum()),
        "category_counts": {
            str(key): int(value)
            for key, value in overlay["overlay_category"].value_counts().sort_index().items()
        },
        "spearman_correlations_with_particulate_free_b_imd": {
            "annual_pm25_ug_m3_idw_2025": round(
                _spearman(overlay["particulate_free_b_imd_score_0_100"], overlay[PM25_COLUMN]),
                6,
            ),
            "annual_pm10_ug_m3_idw_2025": round(
                _spearman(overlay["particulate_free_b_imd_score_0_100"], overlay[PM10_COLUMN]),
                6,
            ),
            "particulate_exposure_score_0_100": round(
                _spearman(
                    overlay["particulate_free_b_imd_score_0_100"],
                    overlay["particulate_exposure_score_0_100"],
                ),
                6,
            ),
        },
        "particulate_exposure_score_by_priority_status": {
            "priority_area": {
                "mean": round(float(priority["particulate_exposure_score_0_100"].mean()), 6),
                "median": round(float(priority["particulate_exposure_score_0_100"].median()), 6),
            },
            "other_area": {
                "mean": round(float(other["particulate_exposure_score_0_100"].mean()), 6),
                "median": round(float(other["particulate_exposure_score_0_100"].median()), 6),
            },
        },
        "double_burden_areas": double_burden[
            [
                "admin_dong_code",
                "sigungu_name",
                "admin_dong_name",
                "b_imd_rank",
                "particulate_free_b_imd_rank",
                "particulate_exposure_rank",
            ]
        ].to_dict(orient="records"),
        "port_industrial_overlay": {
            "status": "not_evaluated_no_versioned_site_geometry",
            "reason": (
                "No reproducible 2025 port or industrial-complex boundary dataset is present in "
                "the project data inventory"
            ),
            "interpretation_limit": (
                "Ambient particulate overlap must not be attributed to ports or industrial "
                "complexes without source-location and dispersion evidence"
            ),
        },
        "decision": "use_for_particulate_independent_double_burden_screening_only",
    }
    return overlay, report


def run(
    composite_path: Path = DEFAULT_COMPOSITE,
    profile_path: Path = DEFAULT_PROFILE,
    output_path: Path = DEFAULT_OUTPUT,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    """Read canonical inputs and write the COD-21 overlay artifacts."""
    composite = pd.read_csv(composite_path, dtype={"admin_dong_code": str})
    profile = pd.read_csv(profile_path, dtype={"admin_dong_code": str})
    overlay, report = build(composite, profile)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    overlay.to_csv(output_path, index=False, encoding="utf-8-sig", lineterminator="\n")
    report.update(
        {
            "input_paths": {
                "composite_index": composite_path.as_posix(),
                "standardized_profile": profile_path.as_posix(),
            },
            "input_sha256": {
                "composite_index": sha256_file(composite_path),
                "standardized_profile": sha256_file(profile_path),
            },
            "output_path": output_path.as_posix(),
            "output_sha256": sha256_file(output_path),
        }
    )
    write_json(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--composite-index", type=Path, default=DEFAULT_COMPOSITE)
    parser.add_argument("--standardized-profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run(args.composite_index, args.standardized_profile, args.output, args.report)
    print(
        f"screened {report['record_count']} administrative dongs; "
        f"double-burden areas={report['double_burden_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
