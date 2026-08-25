"""Generate the 2025 candidate-profile data dictionary and quality report."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from busan_imd.core.artifacts import sha256_file, write_json

DEFAULT_PROFILE = Path(
    "data/processed/standardized/2025/busan_admin_dong_candidate_profile_2025.csv"
)
DEFAULT_STANDARDIZATION_REPORT = Path("docs/data/manifests/STANDARDIZATION_REPORT_2025.json")
DEFAULT_DICTIONARY = Path("docs/data/DATA_DICTIONARY_2025.csv")
DEFAULT_REPORT = Path("docs/data/manifests/DATA_QUALITY_REPORT_2025.json")


@dataclass(frozen=True)
class ColumnSpec:
    source_dataset_id: str
    analysis_role: str
    reference_period: str
    unit: str
    transformation: str
    direction: str
    description: str
    quality_warning: str = ""


def column_spec(column: str) -> ColumnSpec:
    """Return provenance and interpretation metadata for every standardized column."""
    if column in {"admin_dong_code", "sido_name", "sigungu_name", "admin_dong_name"}:
        return ColumnSpec(
            "GEO-ADM-001", "identifier", "2025", "text", "canonical join", "none", column
        )
    if column in {
        "total_population_2025",
        "households_2025",
        "male_population_2025",
        "female_population_2025",
    }:
        return ColumnSpec(
            "DEM-MOIS-POP-2025-001",
            "primary_denominator",
            "2025-12-31",
            "persons or households",
            "16 district files mapped to SGIS codes",
            "none",
            column,
        )
    if column in {"establishments_2024", "workplace_workers_2024"}:
        return ColumnSpec(
            "EMP-SGIS-001",
            "provisional_scoring_proxy",
            "2024",
            "count",
            "SGIS administrative-dong join",
            "lower is more deprived",
            column,
            "One-year lag; workplace rather than resident employment",
        )
    if column.startswith(
        ("total_house_count_", "old_house_", "suppressed_age_cells", "absent_age_cells")
    ):
        return ColumnSpec(
            "HOU-SGIS-OLD-001",
            "provisional_scoring_proxy",
            "2024",
            "count or percent",
            "30-plus-year bands aggregated; suppression reported",
            "higher old-house share is more deprived",
            column,
            "One-year-lag lower-bound proxy",
        )
    if column.startswith("elderly_alone_"):
        return ColumnSpec(
            "SOC-BUSAN-ELDERLY-ALONE-001",
            "validation_only",
            "mixed latest dates",
            "count, date, or per 1,000",
            "latest available dong row joined",
            "none",
            column,
            "Reference dates differ by dong",
        )
    if column.startswith("bus_stop_"):
        return ColumnSpec(
            "HOU-BUSSTOP-001",
            "provisional_scoring_proxy",
            "2025-01-21",
            "count or per 10,000",
            "point-in-polygon then population rate",
            "lower is more deprived",
            column,
            "582 source points fall outside canonical polygons",
        )
    if column.startswith("hospital_"):
        return _facility_spec("HLT-HOSPITAL-001", column)
    if column.startswith("clinic_"):
        return _facility_spec("HLT-CLINIC-001", column)
    if column.startswith("pharmacy_"):
        return _facility_spec("HLT-PHARMACY-001", column)
    if column.startswith("aed_"):
        return ColumnSpec(
            "HLT-AED-001",
            "validation_only",
            "current unverified",
            "count or per 10,000",
            "WKT point-in-polygon then population rate",
            "none",
            column,
            "2025-12-31 status cannot be verified",
        )
    if column.startswith("crime_prevention_cctv_"):
        return ColumnSpec(
            "SAF-BUSAN-CCTV-001",
            "provisional_scoring_proxy",
            "2025",
            "count or per 10,000",
            "point-in-polygon then population rate",
            "direction tested both ways",
            column,
            "Infrastructure is not observed crime incidence",
        )
    if column.startswith("heat_shelter_"):
        return ColumnSpec(
            "ENV-HEAT-SHELTER-001",
            "provisional_scoring_proxy",
            "2025",
            "count or per 10,000",
            "point-in-polygon then population rate",
            "lower is more deprived",
            column,
        )
    if column.startswith("basic_livelihood_") or column in {
        "allocation_method",
        "pattern_source_dataset_id",
        "pattern_source_period",
        "district_total_source_dataset_id",
        "inference_pattern_source_dataset_ids",
        "inference_feature_source_dataset_ids",
        "inference_basis",
        "inference_quality_tier",
        "is_inferred",
        "value_status",
    }:
        return ColumnSpec(
            "INC-BLF-INFERRED-2025-001",
            "provisional_scoring_proxy",
            "2025-12",
            "count, per 1,000, or lineage text",
            "district-constrained allocation using observed or ridge-estimated dong patterns",
            "higher rate is more deprived",
            column,
            "All 206 dong values are inferred, not observed",
        )
    if column == "observed_months_2025" or column.startswith("avg_daily_"):
        return ColumnSpec(
            "DEM-BUSAN-LIVING-001",
            "validation_only",
            "2025",
            "months or persons/day",
            "monthly age rows aggregated to annual daily mean",
            "none",
            column,
            "Service-demand context, not deprivation",
        )
    if column == "core_school_teachers_within_2000m_2025":
        return ColumnSpec(
            "EDU-SCHOOL-001|EDU-SCHOOLINFO-2025-001",
            "provisional_scoring_proxy",
            "2025",
            "active teachers",
            "2025 SchoolInfo staffing joined to official coordinates within 2 km of centroid",
            "fewer is more deprived",
            column,
            "Staffing is observed by school; centroid-based access allocation is a spatial proxy",
        )
    if column in {
        "elementary",
        "middle",
        "high",
        "school_count_2025",
        "nearest_core_school_distance_m_2025",
        "core_schools_within_2000m_2025",
    }:
        return ColumnSpec(
            "EDU-SCHOOL-001",
            "provisional_scoring_proxy",
            "2025",
            "count or metres",
            "official coordinates and centroid-distance calculation",
            "farther/fewer is more deprived",
            column,
            "Measures access, not resident outcomes",
        )
    if (
        column.startswith("air_")
        or column.startswith("nearest_air_")
        or column.startswith("annual_")
    ):
        return ColumnSpec(
            "ENV-AIR-HEIS-DAILY-2025-001",
            "provisional_scoring_proxy",
            "2025",
            "pollutant unit or metres",
            "annual station mean and four-nearest inverse-distance-squared interpolation",
            "higher pollution is more deprived",
            column,
            "Spatial interpolation uncertainty increases with station distance",
        )
    raise ValueError(f"No data-dictionary specification for column: {column}")


def _facility_spec(dataset_id: str, column: str) -> ColumnSpec:
    return ColumnSpec(
        dataset_id,
        "provisional_scoring_proxy",
        "2025-12-31 reconstructed",
        "count or per 10,000",
        "licence-date filter, coordinate validation, point-in-polygon, population rate",
        "lower is more deprived",
        column,
        "Historical completeness is reconstructed from current licence data",
    )


def build(
    profile: pd.DataFrame, standardization: dict[str, Any]
) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for column in profile.columns:
        spec = column_spec(column)
        values = profile[column]
        numeric = pd.to_numeric(values, errors="coerce")
        is_numeric = bool(values.notna().sum() and numeric.notna().sum() == values.notna().sum())
        row = {
            "column_name": column,
            "dtype": str(values.dtype),
            **asdict(spec),
            "missing_count": int(values.isna().sum()),
            "missing_rate": round(float(values.isna().mean()), 6),
            "unique_count": int(values.nunique(dropna=True)),
            "minimum": float(numeric.min()) if is_numeric else "",
            "maximum": float(numeric.max()) if is_numeric else "",
        }
        rows.append(row)
    dictionary = pd.DataFrame(rows)
    role_counts = dictionary.groupby("analysis_role")["column_name"].count().to_dict()
    warnings = dictionary.loc[dictionary["quality_warning"] != "", "column_name"].tolist()
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "reference_year": 2025,
        "profile_record_count": len(profile),
        "profile_column_count": len(profile.columns),
        "canonical_admin_dong_count": standardization["canonical_admin_dong_count"],
        "unique_admin_dong_codes": not profile["admin_dong_code"].duplicated().any(),
        "columns_with_missing_values": {
            column: int(count) for column, count in profile.isna().sum().items() if count
        },
        "analysis_role_column_counts": {str(key): int(value) for key, value in role_counts.items()},
        "quality_warning_column_count": len(warnings),
        "quality_warning_columns": warnings,
        "standardized_dataset_count": len(standardization["datasets"]),
        "minimum_source_match_rate": min(
            float(item["match_rate"]) for item in standardization["datasets"]
        ),
    }
    if (
        len(profile) != int(standardization["canonical_admin_dong_count"])
        or report["unique_admin_dong_codes"] is not True
    ):
        raise ValueError("Quality report requires the complete unique canonical geography")
    return dictionary, report


def run(
    profile_path: Path = DEFAULT_PROFILE,
    standardization_path: Path = DEFAULT_STANDARDIZATION_REPORT,
    dictionary_path: Path = DEFAULT_DICTIONARY,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    profile = pd.read_csv(profile_path, encoding="utf-8-sig", dtype={"admin_dong_code": str})
    standardization = json.loads(standardization_path.read_text(encoding="utf-8"))
    dictionary, report = build(profile, standardization)
    dictionary_path.parent.mkdir(parents=True, exist_ok=True)
    dictionary.to_csv(dictionary_path, index=False, encoding="utf-8-sig")
    report.update(
        {
            "profile_path": profile_path.as_posix(),
            "profile_sha256": sha256_file(profile_path),
            "dictionary_path": dictionary_path.as_posix(),
            "dictionary_sha256": sha256_file(dictionary_path),
            "standardization_report_path": standardization_path.as_posix(),
            "standardization_report_sha256": sha256_file(standardization_path),
        }
    )
    write_json(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument(
        "--standardization-report", type=Path, default=DEFAULT_STANDARDIZATION_REPORT
    )
    parser.add_argument("--dictionary", type=Path, default=DEFAULT_DICTIONARY)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run(args.profile, args.standardization_report, args.dictionary, args.report)
    print(
        f"documented {report['profile_column_count']} columns across "
        f"{report['profile_record_count']} dongs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
