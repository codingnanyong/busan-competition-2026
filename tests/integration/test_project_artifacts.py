import hashlib
import json
import re
from pathlib import Path

import pandas as pd

from busan_imd.collectors.approved_apis import validate_manifest as validate_raw_manifest
from busan_imd.collectors.fire_incidents import validate_manifest as validate_fire_manifest
from busan_imd.collectors.healthcare_facilities import (
    validate_manifest as validate_healthcare_manifest,
)
from busan_imd.collectors.heis_air import validate_manifest as validate_heis_manifest
from busan_imd.collectors.housing import validate_manifest as validate_housing_manifest
from busan_imd.collectors.police_crime import validate_manifest as validate_police_manifest
from busan_imd.collectors.reference_data import MANIFEST_PATH as REFERENCE_MANIFEST_PATH
from busan_imd.collectors.resident_population import (
    validate_manifest as validate_population_manifest,
)
from busan_imd.collectors.supplemental_data import (
    validate_manifest as validate_supplemental_manifest,
)
from busan_imd.collectors.traffic_accidents import validate_manifest as validate_traffic_manifest
from busan_imd.data_catalog import validate_catalog
from busan_imd.income_inference import validate_manifest as validate_income_manifest

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
        "docs/data/manifests/POLICE_CRIME_MANIFEST_2025.json",
        "docs/data/manifests/SGIS_HOUSING_PROXY_MANIFEST_2025.json",
        "docs/data/manifests/BASIC_LIVELIHOOD_INFERENCE_MANIFEST_2025.json",
        "docs/data/manifests/STANDARDIZATION_REPORT_2025.json",
        "docs/data/manifests/DATA_QUALITY_REPORT_2025.json",
        "docs/data/DATA_DICTIONARY_2025.csv",
        "docs/data/DATA_QUALITY.md",
        "docs/data/EDA_2025.md",
        "docs/data/EDA_INDICATOR_DECISIONS_2025.csv",
        "docs/data/manifests/EDA_REPORT_2025.json",
        "docs/data/DOMAIN_SCORE_SPEC_2025.csv",
        "docs/data/manifests/DOMAIN_SCORE_REPORT_2025.json",
        "docs/data/COMPOSITE_INDEX_SPEC_2025.csv",
        "docs/data/manifests/COMPOSITE_INDEX_REPORT_2025.json",
        "docs/data/SENSITIVITY_SCENARIOS_2025.csv",
        "docs/data/manifests/SENSITIVITY_ANALYSIS_REPORT_2025.json",
        "docs/data/manifests/PRIORITY_AREA_REPORT_2025.json",
        "docs/data/manifests/CLUSTER_ANALYSIS_REPORT_2025.json",
        "docs/data/manifests/ENVIRONMENTAL_OVERLAY_REPORT_2025.json",
        "docs/data/manifests/POLICY_MATRIX_REPORT_2025.json",
        "docs/data/manifests/INFOGRAPHIC_REPORT_2025.json",
        "docs/data/manifests/CATEGORY_ASSESSMENT_REPORT_2025.json",
        "docs/data/POLICY_ACTION_CATALOG_2025.csv",
        "docs/data/CATEGORY_ASSESSMENT_SPEC_2025.csv",
        "docs/data/CATEGORY_POLICY_CATALOG_2025.csv",
        "docs/data/DATA_PORTABILITY.md",
        "docs/data/manifests/CONSUMER_SALES_MANIFEST_2025.json",
        "docs/data/manifests/CITY_PARKS_MANIFEST.json",
        "docs/data/STANDARDIZATION.md",
        "docs/en/data/EDA_2025.md",
        "docs/methodology/DOMAIN_SCORES_2025.md",
        "docs/en/methodology/DOMAIN_SCORES_2025.md",
        "docs/methodology/COMPOSITE_INDEX_2025.md",
        "docs/en/methodology/COMPOSITE_INDEX_2025.md",
        "docs/methodology/SENSITIVITY_ANALYSIS_2025.md",
        "docs/en/methodology/SENSITIVITY_ANALYSIS_2025.md",
        "docs/methodology/PRIORITY_AREAS_2025.md",
        "docs/en/methodology/PRIORITY_AREAS_2025.md",
        "docs/methodology/CLUSTER_ANALYSIS_2025.md",
        "docs/en/methodology/CLUSTER_ANALYSIS_2025.md",
        "docs/methodology/ENVIRONMENTAL_OVERLAY_2025.md",
        "docs/en/methodology/ENVIRONMENTAL_OVERLAY_2025.md",
        "docs/methodology/POLICY_MATRIX_2025.md",
        "docs/en/methodology/POLICY_MATRIX_2025.md",
        "docs/methodology/INFOGRAPHIC_2025.md",
        "docs/en/methodology/INFOGRAPHIC_2025.md",
        "docs/methodology/CATEGORY_ASSESSMENT_2025.md",
        "docs/en/methodology/CATEGORY_ASSESSMENT_2025.md",
        "outputs/infographic/busan_imd_one_page_2025.svg",
        "outputs/infographic/busan_imd_one_page_2025.pdf",
        "outputs/infographic/busan_imd_one_page_2025.png",
        "outputs/infographic/busan_admin_dong_category_assessment_2025.csv",
        "outputs/infographic/busan_admin_dong_major_category_assessment_2025.csv",
        "outputs/infographic/busan_admin_dong_category_indicator_scores_2025.csv",
        "notebooks/01_candidate_profile_eda.ipynb",
        "notebooks/02_deprivation_cluster_review.ipynb",
        "notebooks/03_environmental_overlay_review.ipynb",
        "notebooks/04_policy_matrix_review.ipynb",
    )

    assert all((REPOSITORY_ROOT / path).is_dir() for path in required_directories)
    assert all((REPOSITORY_ROOT / path).is_file() for path in required_documents)


def test_eda_notebook_is_clean_and_reuses_the_pipeline() -> None:
    notebook_path = REPOSITORY_ROOT / "notebooks/01_candidate_profile_eda.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))

    assert notebook["nbformat"] == 4
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    assert any("from busan_imd.eda import run" in "".join(cell["source"]) for cell in code_cells)
    assert any("os.chdir(project_root)" in "".join(cell["source"]) for cell in code_cells)
    assert all(cell["execution_count"] is None for cell in code_cells)
    assert all(cell["outputs"] == [] for cell in code_cells)


def test_cluster_notebook_is_clean_and_portable() -> None:
    notebook_path = REPOSITORY_ROOT / "notebooks/02_deprivation_cluster_review.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))

    assert notebook["nbformat"] == 4
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    sources = ["".join(cell["source"]) for cell in code_cells]
    assert any("os.chdir(project_root)" in source for source in sources)
    assert any("from busan_imd.cluster_analysis import" in source for source in sources)
    assert any("px.scatter" in source for source in sources)
    assert any("px.imshow" in source for source in sources)
    assert all(cell["execution_count"] is None for cell in code_cells)
    assert all(cell["outputs"] == [] for cell in code_cells)


def test_environmental_overlay_notebook_is_clean_and_portable() -> None:
    notebook_path = REPOSITORY_ROOT / "notebooks/03_environmental_overlay_review.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))

    assert notebook["nbformat"] == 4
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    sources = ["".join(cell["source"]) for cell in code_cells]
    assert any("os.chdir(project_root)" in source for source in sources)
    assert any("from busan_imd.environmental_overlay import" in source for source in sources)
    assert any("px.scatter" in source for source in sources)
    assert any("px.choropleth_mapbox" in source for source in sources)
    assert all(cell["execution_count"] is None for cell in code_cells)
    assert all(cell["outputs"] == [] for cell in code_cells)


def test_policy_matrix_notebook_is_clean_and_portable() -> None:
    notebook_path = REPOSITORY_ROOT / "notebooks/04_policy_matrix_review.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))

    assert notebook["nbformat"] == 4
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    sources = ["".join(cell["source"]) for cell in code_cells]
    assert any("os.chdir(project_root)" in source for source in sources)
    assert any("from busan_imd.policy_matrix import" in source for source in sources)
    assert any("px.bar" in source for source in sources)
    assert any("px.scatter" in source for source in sources)
    assert all(cell["execution_count"] is None for cell in code_cells)
    assert all(cell["outputs"] == [] for cell in code_cells)


def test_eda_report_covers_the_canonical_profile() -> None:
    report = read_json("docs/data/manifests/EDA_REPORT_2025.json")

    assert report["profile_record_count"] == 206
    assert report["numeric_indicator_count"] == 48
    assert report["scoring_candidate_numeric_count"] == 36
    assert report["constant_numeric_columns"] == ["air_idw_station_count"]
    assert report["columns_with_missing_values"] == {}
    assert report["high_correlation_pair_count"] == 5
    assert report["contiguity_edge_count"] == 532
    assert report["isolated_admin_dong_count"] == len(report["isolated_admin_dongs"]) == 6
    assert all(re.fullmatch(r"[0-9A-F]{64}", value) for value in report["output_sha256"].values())


def test_domain_score_report_preserves_cod16_scope() -> None:
    report = read_json("docs/data/manifests/DOMAIN_SCORE_REPORT_2025.json")

    assert report["record_count"] == 206
    assert report["indicator_count"] == 9
    assert report["scored_domains"] == [
        "education",
        "employment",
        "health",
        "housing_access",
        "income",
        "living_environment",
    ]
    assert report["held_domains"] == {
        "safety": "No direct administrative-dong incident indicator is available"
    }
    assert report["score_direction"] == "higher means greater relative deprivation"
    assert report["composite_score_created"] is False
    assert all(re.fullmatch(r"[0-9A-F]{64}", value) for value in report["output_sha256"].values())


def test_composite_index_report_covers_cod17_scope() -> None:
    report = read_json("docs/data/manifests/COMPOSITE_INDEX_REPORT_2025.json")

    assert report["record_count"] == 206
    assert report["score_direction"] == "higher means greater relative deprivation"
    assert report["rank_direction"] == "rank 1 is most deprived"
    assert report["decile_direction"] == "decile 1 is most deprived 10 percent"
    assert set(report["decile_counts"]) == {str(value) for value in range(1, 11)}
    assert re.fullmatch(r"[0-9A-F]{64}", report["output_sha256"])


def test_sensitivity_report_covers_cod18_scope() -> None:
    report = read_json("docs/data/manifests/SENSITIVITY_ANALYSIS_REPORT_2025.json")

    assert report["record_count"] == 206
    assert report["scenario_count"] == 9
    assert report["actual_missing_domain_score_count"] == 0
    assert set(report["scenario_summaries"]) == {
        "baseline",
        "equal_domain_weights",
        "median_imputation_observed",
        "omit_income",
        "omit_employment",
        "omit_education",
        "omit_health",
        "omit_housing_access",
        "omit_living_environment",
    }
    assert re.fullmatch(r"[0-9A-F]{64}", report["output_sha256"])


def test_priority_area_report_covers_cod19_scope() -> None:
    report = read_json("docs/data/manifests/PRIORITY_AREA_REPORT_2025.json")

    assert report["record_count"] == 206
    assert report["priority_area_rule"] == "B-IMD decile 1"
    assert report["priority_area_count"] == 21
    assert report["indicator_count"] == 9
    assert sum(report["leading_domain_counts"].values()) == 21
    assert len(report["top_10_priority_areas"]) == 10
    assert all(
        re.fullmatch(r"[0-9A-F]{64}", value)
        for value in report["output_sha256"].values()
    )


def test_cluster_analysis_report_records_cod20_typology_decision() -> None:
    report = read_json("docs/data/manifests/CLUSTER_ANALYSIS_REPORT_2025.json")
    priority_report = read_json("docs/data/manifests/PRIORITY_AREA_REPORT_2025.json")

    assert report["record_count"] == 21
    assert report["candidate_cluster_counts"] == [2, 3, 4, 5, 6]
    assert report["selected_cluster_count"] == 2
    assert report["recommended_for_policy_typology"] is True
    assert report["decision"] == "use_as_exploratory_policy_typology"
    assert report["input_sha256"] == priority_report["output_sha256"]["priority_areas"]
    assert report["selected_metrics"]["mean_seed_stability_ari"] >= report[
        "quality_gate"
    ]["minimum_mean_seed_stability_ari"]
    assert {item["cluster_label"] for item in report["cluster_summaries"]} == {
        "education_living_environment",
        "employment_income",
    }
    assert all(
        re.fullmatch(r"[0-9A-F]{64}", value)
        for value in report["output_sha256"].values()
    )


def test_environmental_overlay_report_records_cod21_scope() -> None:
    report = read_json("docs/data/manifests/ENVIRONMENTAL_OVERLAY_REPORT_2025.json")
    composite_report = read_json("docs/data/manifests/COMPOSITE_INDEX_REPORT_2025.json")
    standardization_report = read_json("docs/data/manifests/STANDARDIZATION_REPORT_2025.json")

    assert report["record_count"] == 206
    assert report["high_exposure_count"] == 52
    assert report["priority_area_count"] == 21
    assert report["double_burden_count"] == 4
    assert sum(report["category_counts"].values()) == 206
    assert report["decision"] == (
        "use_for_particulate_independent_double_burden_screening_only"
    )
    assert report["port_industrial_overlay"]["status"] == (
        "not_evaluated_no_versioned_site_geometry"
    )
    assert report["input_sha256"]["composite_index"] == composite_report["output_sha256"]
    assert report["input_sha256"]["standardized_profile"] == standardization_report[
        "profile_sha256"
    ]
    assert re.fullmatch(r"[0-9A-F]{64}", report["output_sha256"])


def test_policy_matrix_report_records_cod22_scope() -> None:
    report = read_json("docs/data/manifests/POLICY_MATRIX_REPORT_2025.json")
    cluster_report = read_json("docs/data/manifests/CLUSTER_ANALYSIS_REPORT_2025.json")
    overlay_report = read_json("docs/data/manifests/ENVIRONMENTAL_OVERLAY_REPORT_2025.json")

    assert report["priority_area_count"] == 21
    assert report["cluster_count"] == 2
    assert report["matrix_row_count"] == 5
    assert report["unique_policy_count"] == 4
    assert report["decision_status"] == "candidate_for_field_validation"
    assert report["input_sha256"]["cluster_assignments"] == cluster_report[
        "output_sha256"
    ]["assignments"]
    assert report["input_sha256"]["environmental_overlay"] == overlay_report[
        "output_sha256"
    ]
    assert report["cluster_summaries"][0]["excluded_nonpositive_domains"] == [
        {"domain": "living_environment", "mean_excess_points": -0.252867}
    ]
    assert all(
        re.fullmatch(r"[0-9A-F]{64}", value)
        for value in (*report["input_sha256"].values(), report["output_sha256"])
    )


def test_infographic_report_and_outputs_cover_cod23_scope() -> None:
    report = read_json("docs/data/manifests/INFOGRAPHIC_REPORT_2025.json")

    assert report["artifact_status"] == "submission_draft"
    assert report["page_count"] == 1
    assert report["dong_action_profile_count"] == 206
    assert report["priority_area_count"] == 21
    assert report["double_burden_area_count"] == 4
    assert report["policy_candidate_count"] == 5
    assert len(report["top_10_names"]) == 10
    for format_name, relative_path in report["output_paths"].items():
        path = REPOSITORY_ROOT / relative_path
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest().upper()
        assert actual_hash == report["output_sha256"][format_name]
    pdf = (REPOSITORY_ROOT / report["output_paths"]["pdf"]).read_bytes()
    assert len(re.findall(rb"/Type\s*/Page\b", pdf)) == 1
    svg = (REPOSITORY_ROOT / report["output_paths"]["svg"]).read_text(encoding="utf-8")
    assert "행정동별 취약 원인" in svg
    profiles = pd.read_csv(
        REPOSITORY_ROOT / report["output_paths"]["action_profile_csv"],
        dtype={"admin_dong_code": str},
    )
    assert len(profiles) == 206
    assert profiles["admin_dong_code"].nunique() == 206
    assert profiles["improvement_direction"].notna().all()
    assert profiles["specialization_evidence_status"].str.contains("특화 확정 불가").all()
    action_map = (
        REPOSITORY_ROOT / report["output_paths"]["interactive_action_map"]
    ).read_text(encoding="utf-8")
    assert action_map.count("data-code=") == 206
    assert action_map.count('class="tree-major"') == 3
    assert action_map.count('class="tree-child"') == 8
    assert 'role="tree"' in action_map
    assert "큰 카테고리 점수 =" in action_map


def test_category_assessment_is_complete_and_flags_estimation() -> None:
    report = read_json("docs/data/manifests/CATEGORY_ASSESSMENT_REPORT_2025.json")

    assert report["admin_dong_count"] == 206
    assert report["major_category_count"] == 3
    assert report["category_count"] == 8
    assert report["indicator_count"] == 13
    assert report["category_score_row_count"] == 206 * 8
    assert report["major_category_score_row_count"] == 206 * 3
    assert report["indicator_score_row_count"] == 206 * 13
    assert report["policy_trigger_threshold"] == 70
    for name, relative_path in report["output_paths"].items():
        actual = hashlib.sha256((REPOSITORY_ROOT / relative_path).read_bytes()).hexdigest().upper()
        assert actual == report["output_sha256"][name]
    categories = pd.read_csv(
        REPOSITORY_ROOT / report["output_paths"]["category_assessment"],
        dtype={"admin_dong_code": str},
    )
    assert categories.groupby("admin_dong_code")["category"].nunique().eq(8).all()
    major_categories = pd.read_csv(
        REPOSITORY_ROOT / report["output_paths"]["major_category_assessment"],
        dtype={"admin_dong_code": str},
    )
    assert major_categories.groupby("admin_dong_code")["major_category"].nunique().eq(3).all()
    assert major_categories["major_category_score_0_100"].between(0, 100).all()
    myeongji = categories[
        categories["admin_dong_name"].isin(["명지1동", "명지2동"])
        & (categories["category"] == "education_access_supply")
    ]
    assert len(myeongji) == 2
    assert myeongji["category_score_0_100"].lt(70).all()
    indicators = pd.read_csv(
        REPOSITORY_ROOT / report["output_paths"]["indicator_scores"]
    )
    assert {"estimate_used", "estimation_method_ko", "estimation_reason"} <= set(
        indicators.columns
    )
    estimated = indicators[indicators["estimate_used"]]
    assert len(estimated) == 206 * 9
    assert estimated["estimation_reason"].str.len().gt(0).all()


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
    assert manifest["dataset_count"] == 10
    living = entries["DEM-BUSAN-LIVING-001"]
    assert living["record_count"] == 44340
    assert living["reference_month_min"] == "202301"
    assert living["reference_month_max"] == "202512"
    assert living["admin_dong_count"] == 206
    assert entries["TRN-BUSAN-VILLAGE-BUS-001"]["record_count"] == 136
    assert entries["TRN-BUSAN-ROUTE-USAGE-2025-001"]["record_count"] == 333
    assert entries["INC-BLF-HAEUNDAE-2025-001"]["record_count"] == 19
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


def test_police_crime_manifest_covers_2025_as_validation_only() -> None:
    manifest = read_json("docs/data/manifests/POLICE_CRIME_MANIFEST_2025.json")
    validate_police_manifest(manifest, REPOSITORY_ROOT)

    assert manifest["reference_period"] == "2025-01-01/2025-12-31"
    assert manifest["record_count"] == 16
    assert manifest["police_station_count"] == 16
    assert manifest["crime_count_total"] == 31470
    assert manifest["eligible_for_primary_analysis"] is False


def test_housing_proxy_discloses_2024_to_2025_inference() -> None:
    manifest = read_json("docs/data/manifests/SGIS_HOUSING_PROXY_MANIFEST_2025.json")
    validate_housing_manifest(manifest, REPOSITORY_ROOT)

    assert manifest["reference_period"] == "2024-12-31"
    assert manifest["inference_target_year"] == 2025
    assert manifest["lag_years"] == 1
    assert manifest["record_count"] == 206
    assert manifest["analysis_role"] == "provisional_scoring_proxy"


def test_basic_livelihood_proxy_discloses_dong_inference() -> None:
    manifest = read_json(
        "docs/data/manifests/BASIC_LIVELIHOOD_INFERENCE_MANIFEST_2025.json"
    )
    validate_income_manifest(manifest, REPOSITORY_ROOT)

    assert manifest["reference_period"] == "2025-12"
    assert manifest["district_totals_are_observed"] is True
    assert manifest["admin_dong_values_are_inferred"] is True
    assert manifest["record_count"] == 206
    assert manifest["district_count"] == 16
    assert manifest["observed_pattern_admin_dongs"] == 86
    assert manifest["district_people_total"] == 256393
    assert manifest["analysis_role"] == "provisional_scoring_proxy"
    assert manifest["lineage"]["district_total_dataset_id"] == (
        "INC-WELFARE-SIGUNGU-2025-001"
    )
    assert set(manifest["lineage"]["model_feature_dataset_ids"].values()) == {
        "SOC-BUSAN-ELDERLY-ALONE-001",
        "HOU-SGIS-OLD-001",
        "DEM-MOIS-POP-2025-001",
    }


def test_standardization_report_covers_canonical_dongs_and_discloses_failures() -> None:
    report = read_json("docs/data/manifests/STANDARDIZATION_REPORT_2025.json")
    entries = {entry["dataset_id"]: entry for entry in report["datasets"]}

    assert report["reference_year"] == 2025
    assert report["reference_crs"] == "EPSG:5179"
    assert report["canonical_admin_dong_count"] == 206
    assert report["profile_record_count"] == 206
    assert report["profile_checks"]["total_population_2025"] == 3241600
    assert report["profile_checks"]["sex_total_mismatch_admin_dongs"] == 0
    assert report["profile_checks"]["count_column_totals"]["bus_stop_count_2025"] == 7940
    assert report["analysis_roles"]["primary_denominator"] == ["DEM-MOIS-POP-2025-001"]
    assert set(report["analysis_roles"]["provisional_scoring_proxy"]) == {
        "EMP-SGIS-001",
        "HOU-SGIS-OLD-001",
        "INC-BLF-INFERRED-2025-001",
        "HLT-HOSPITAL-001",
        "HLT-CLINIC-001",
        "HLT-PHARMACY-001",
        "HOU-BUSSTOP-001",
        "SAF-BUSAN-CCTV-001",
        "ENV-HEAT-SHELTER-001",
        "EDU-SCHOOL-001",
        "ENV-AIR-HEIS-DAILY-2025-001",
    }
    assert set(report["analysis_roles"]["validation_only"]) == {
        "SOC-BUSAN-ELDERLY-ALONE-001",
        "HLT-AED-001",
        "DEM-BUSAN-LIVING-001",
    }
    assert entries["DEM-MOIS-POP-2025-001"]["matched_admin_dongs"] == 206
    assert entries["INC-BLF-INFERRED-2025-001"]["matched_admin_dongs"] == 206
    assert entries["HOU-BUSSTOP-001"]["matched_records"] == 7940
    assert entries["HOU-BUSSTOP-001"]["unmatched_records"] == 582
    assert entries["HLT-HOSPITAL-001"]["coordinate_missing_records"] == 29
    assert entries["SAF-BUSAN-CCTV-001"]["coordinate_invalid_records"] == 43
    assert all(re.fullmatch(r"[0-9A-F]{64}", entry["source_sha256"]) for entry in entries.values())


def test_committed_manifests_do_not_contain_credentials() -> None:
    for relative_path in (
        "docs/data/manifests/RAW_DATA_MANIFEST.json",
        REFERENCE_MANIFEST_PATH.as_posix(),
        "docs/data/manifests/HEIS_AIR_MANIFEST_2025.json",
        "docs/data/manifests/HEIS_AIR_MANIFEST_2026.json",
        "docs/data/manifests/HEALTHCARE_FACILITY_MANIFEST_2025.json",
        "docs/data/manifests/KOROAD_TRAFFIC_ACCIDENT_MANIFEST.json",
        "docs/data/manifests/POLICE_CRIME_MANIFEST_2025.json",
        "docs/data/manifests/SGIS_HOUSING_PROXY_MANIFEST_2025.json",
        "docs/data/manifests/BASIC_LIVELIHOOD_INFERENCE_MANIFEST_2025.json",
        "docs/data/manifests/MOIS_RESIDENT_POPULATION_MANIFEST_2025.json",
        "docs/data/manifests/BUSAN_SUPPLEMENTAL_DATA_MANIFEST.json",
        "docs/data/manifests/FIRE_SUMMARY_MANIFEST_2025.json",
        "docs/data/manifests/STANDARDIZATION_REPORT_2025.json",
        "docs/data/manifests/CANDIDATE_PROCESSING_REPORT_2025.json",
        "docs/data/manifests/DATA_QUALITY_REPORT_2025.json",
        "docs/data/manifests/CONSUMER_SALES_MANIFEST_2025.json",
        "docs/data/manifests/CITY_PARKS_MANIFEST.json",
    ):
        text = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
        assert "serviceKey=" not in text
        assert "accessToken=" not in text
        assert "consumer_secret" not in text
        assert "consumer_key" not in text
