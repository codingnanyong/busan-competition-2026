import json
import re
from pathlib import Path

from busan_imd.collectors.approved_apis import validate_manifest as validate_raw_manifest
from busan_imd.collectors.fire_incidents import validate_manifest as validate_fire_manifest
from busan_imd.collectors.healthcare_facilities import (
    validate_manifest as validate_healthcare_manifest,
)
from busan_imd.collectors.heis_air import validate_manifest as validate_heis_manifest
from busan_imd.collectors.reference_data import MANIFEST_PATH as REFERENCE_MANIFEST_PATH
from busan_imd.collectors.resident_population import (
    validate_manifest as validate_population_manifest,
)
from busan_imd.collectors.supplemental_data import (
    validate_manifest as validate_supplemental_manifest,
)
from busan_imd.collectors.traffic_accidents import validate_manifest as validate_traffic_manifest
from busan_imd.data_catalog import validate_catalog

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def read_json(relative_path: str) -> dict:
    return json.loads((REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8"))


def test_project_structure_and_required_documents() -> None:
    required_directories = (
        "data/raw",
        "data/processed",
        "notebooks",
        "outputs",
        "src/busan_imd/core",
        "src/busan_imd/collectors",
        "src/busan_imd/sources",
        "tests/integration",
    )
    required_documents = (
        ".env.example",
        "docs/MACOS_SETUP.md",
        "docs/PROJECT_STRUCTURE.md",
        "docs/data/AED_HISTORY_ASSESSMENT.md",
        "docs/data/DATA_REQUEST_ROADMAP.md",
        "docs/data/DATA_REQUEST_TEMPLATES.md",
        "docs/data/DATA_ACCESS_REQUIREMENTS.md",
        "docs/data/manifests/HEALTHCARE_FACILITY_MANIFEST_2025.json",
        "docs/data/manifests/KOROAD_TRAFFIC_ACCIDENT_MANIFEST.json",
        "docs/data/manifests/MOIS_RESIDENT_POPULATION_MANIFEST_2025.json",
        "docs/data/manifests/BUSAN_SUPPLEMENTAL_DATA_MANIFEST.json",
        "docs/data/manifests/FIRE_SUMMARY_MANIFEST_2025.json",
    )

    assert all((REPOSITORY_ROOT / path).is_dir() for path in required_directories)
    assert all((REPOSITORY_ROOT / path).is_file() for path in required_documents)


def test_dataset_audit_is_valid() -> None:
    rows = validate_catalog(REPOSITORY_ROOT / "docs/data/DATASET_AUDIT.csv")

    assert len(rows) >= 18
    assert {row["availability_grade"] for row in rows} >= {"B", "C"}
    assert {row["availability_grade"] for row in rows} <= {"A", "B", "C", "D"}
    assert {row["decision"] for row in rows} >= {"hold", "exclude", "validation-only"}


def test_admin_boundary_artifacts_are_consistent() -> None:
    manifest_path = REPOSITORY_ROOT / "docs/data/manifests/BUSAN_ADMIN_DONG_MANIFEST_2025.json"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)
    report = read_json("docs/data/manifests/BUSAN_ADMIN_DONG_GEOMETRY_VALIDATION_2025.json")

    assert "accessToken" not in manifest_text
    assert "consumer_secret" not in manifest_text
    assert manifest["reference_year"] == 2025
    assert manifest["feature_count"] == 206
    assert report["source_checks"]["invalid_geometries"] == 1
    assert report["repaired_checks"]["invalid_geometries"] == 0


def test_raw_collection_manifest_and_bus_stops_are_valid() -> None:
    manifest = read_json("docs/data/manifests/RAW_DATA_MANIFEST.json")
    validate_raw_manifest(manifest, REPOSITORY_ROOT)

    assert manifest["primary_reference_year"] == 2025
    assert manifest["dataset_count"] == 14
    assert manifest["cutoff_status_counts"] == {
        "eligible": 11,
        "outside_cutoff": 1,
        "unverified": 2,
    }
    bus_stops = read_json("docs/data/manifests/BUS_STOP_MANIFEST_2025.json")
    assert bus_stops["record_count"] == 8522
    assert bus_stops["crs"] == "EPSG:4326"
    assert bus_stops["null_geometry_count"] == 0
    assert re.fullmatch(r"[0-9A-F]{64}", bus_stops["sha256"])


def test_reference_manifest_includes_demographics_and_schools() -> None:
    manifest = read_json(REFERENCE_MANIFEST_PATH.as_posix())
    entries = {entry["dataset_id"]: entry for entry in manifest["datasets"]}

    assert manifest["primary_reference_year"] == 2025
    assert manifest["dataset_count"] == 2
    assert entries["DEM-SGIS-001"]["record_count"] == 206
    assert entries["DEM-SGIS-001"]["analysis_role"] == "fallback"
    assert entries["DEM-SGIS-001"]["lag_years"] == 1
    schools = entries["EDU-SCHOOL-NEIS-001"]
    assert schools["record_count"] == 667
    assert schools["analysis_eligible_record_count"] == 662
    assert schools["excluded_after_cutoff_record_count"] == 5
    assert schools["facility_opening_cutoff"] == "2025-12-31"


def test_mois_population_manifest_covers_all_2025_admin_dongs() -> None:
    manifest = read_json("docs/data/manifests/MOIS_RESIDENT_POPULATION_MANIFEST_2025.json")
    validate_population_manifest(manifest, REPOSITORY_ROOT)

    assert manifest["reference_period"] == "2025-12-31"
    assert manifest["analysis_role"] == "primary"
    assert manifest["source_file_count"] == 16
    assert manifest["record_count"] == 206
    assert manifest["matched_reference_count"] == 206
    assert manifest["unmatched_reference_count"] == 0


def test_supplemental_manifest_records_all_selected_sources() -> None:
    manifest = read_json("docs/data/manifests/BUSAN_SUPPLEMENTAL_DATA_MANIFEST.json")
    validate_supplemental_manifest(manifest, REPOSITORY_ROOT)

    entries = {entry["dataset_id"]: entry for entry in manifest["datasets"]}
    assert manifest["dataset_count"] == 8
    living = entries["DEM-BUSAN-LIVING-001"]
    assert living["record_count"] == 44340
    assert living["reference_month_min"] == "202301"
    assert living["reference_month_max"] == "202512"
    assert living["admin_dong_count"] == 206
    assert entries["TRN-BUSAN-VILLAGE-BUS-001"]["record_count"] == 136
    elderly = entries["SOC-BUSAN-ELDERLY-ALONE-001"]
    assert elderly["collection_status"] == "collected"
    assert elderly["record_count"] == 206
    assert elderly["raw_record_count"] == 241
    assert entries["INC-WELFARE-SIGUNGU-2025-001"]["record_count"] > 0
    assert entries["SAF-BUSAN-CCTV-001"]["record_count"] == 21060
    assert entries["TRN-BUSAN-BOARDING-2023-001"]["record_count"] == 17088


def test_heis_manifests_cover_2025_and_2026_cutoff() -> None:
    manifest_2025 = read_json("docs/data/manifests/HEIS_AIR_MANIFEST_2025.json")
    manifest_2026 = read_json("docs/data/manifests/HEIS_AIR_MANIFEST_2026.json")
    validate_heis_manifest(manifest_2025, REPOSITORY_ROOT)
    validate_heis_manifest(manifest_2026, REPOSITORY_ROOT)

    assert manifest_2025["reference_period"] == "2025-01-01/2025-12-31"
    assert manifest_2025["analysis_role"] == "primary"
    assert manifest_2025["eligible_for_primary_analysis"] is True
    assert manifest_2025["record_count"] == 12045
    assert manifest_2026["reference_period"] == "2026-01-01/2026-07-31"
    assert manifest_2026["analysis_role"] == "supplemental_validation"
    assert manifest_2026["eligible_for_primary_analysis"] is False
    assert manifest_2026["record_count"] == 6996


def test_healthcare_and_traffic_manifests_are_complete() -> None:
    healthcare = read_json("docs/data/manifests/HEALTHCARE_FACILITY_MANIFEST_2025.json")
    traffic = read_json("docs/data/manifests/KOROAD_TRAFFIC_ACCIDENT_MANIFEST.json")
    validate_healthcare_manifest(healthcare, REPOSITORY_ROOT)
    validate_traffic_manifest(traffic, REPOSITORY_ROOT)

    health_entries = {entry["dataset_id"]: entry for entry in healthcare["datasets"]}
    assert health_entries["HLT-HOSPITAL-001"]["record_count"] == 406
    assert health_entries["HLT-CLINIC-001"]["record_count"] == 5320
    assert health_entries["HLT-PHARMACY-001"]["record_count"] == 1731
    assert all(not entry["eligible_for_primary_analysis"] for entry in health_entries.values())

    traffic_entries = {entry["dataset_id"]: entry for entry in traffic["datasets"]}
    assert traffic_entries["SAF-KOROAD-STT-001"]["record_count"] == 202
    assert traffic_entries["SAF-KOROAD-HOTSPOT-001"]["record_count"] == 48


def test_fire_manifest_covers_complete_2025_as_validation_only() -> None:
    manifest = read_json("docs/data/manifests/FIRE_SUMMARY_MANIFEST_2025.json")
    validate_fire_manifest(manifest, REPOSITORY_ROOT)

    assert manifest["reference_period"] == "2025-01-01/2025-12-31"
    assert manifest["request_count"] == 365
    assert manifest["record_count"] == 3156
    assert manifest["station_count"] == 12
    assert manifest["eligible_for_primary_analysis"] is False


def test_committed_manifests_do_not_contain_credentials() -> None:
    for relative_path in (
        "docs/data/manifests/RAW_DATA_MANIFEST.json",
        REFERENCE_MANIFEST_PATH.as_posix(),
        "docs/data/manifests/HEIS_AIR_MANIFEST_2025.json",
        "docs/data/manifests/HEIS_AIR_MANIFEST_2026.json",
        "docs/data/manifests/HEALTHCARE_FACILITY_MANIFEST_2025.json",
        "docs/data/manifests/KOROAD_TRAFFIC_ACCIDENT_MANIFEST.json",
        "docs/data/manifests/MOIS_RESIDENT_POPULATION_MANIFEST_2025.json",
        "docs/data/manifests/BUSAN_SUPPLEMENTAL_DATA_MANIFEST.json",
        "docs/data/manifests/FIRE_SUMMARY_MANIFEST_2025.json",
    ):
        text = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
        assert "serviceKey=" not in text
        assert "accessToken=" not in text
        assert "consumer_secret" not in text
        assert "consumer_key" not in text
