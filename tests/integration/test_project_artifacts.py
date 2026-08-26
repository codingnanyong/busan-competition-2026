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
from busan_imd.processing.data_catalog import validate_catalog
from busan_imd.processing.income_inference import validate_manifest as validate_income_manifest
from busan_imd.submission.report import REQUIRED_SECTION_TITLES

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def dashboard_bundle(html_path: Path) -> str:
    parts = [html_path.read_text(encoding="utf-8")]
    for folder in ("css", "js"):
        for path in sorted((html_path.parent / folder).iterdir()):
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def read_json(relative_path: str) -> dict:
    return json.loads((REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8"))


def test_project_structure_and_required_documents() -> None:
    required_directories = (
        "data/raw",
        "data/processed",
        "notebooks",
        "outputs",
        "outputs/infographic/2025/static",
        "outputs/infographic/2025/interactive",
        "outputs/infographic/2025/interactive/html",
        "outputs/infographic/2025/interactive/css",
        "outputs/infographic/2025/interactive/js",
        "outputs/infographic/2025/tables",
        "outputs/submission/2025",
        "outputs/submission/2025/03_data",
        "docs/data/tables",
        "docs/kor",
        "docs/eng",
        "src/busan_imd/core",
        "src/busan_imd/collectors",
        "src/busan_imd/sources",
        "src/busan_imd/processing",
        "src/busan_imd/analysis",
        "src/busan_imd/infographic",
        "src/busan_imd/infographic/presentation/dashboard",
        "src/busan_imd/submission",
        "tests/integration",
    )
    required_documents = (
        ".env.example",
        "LICENSE",
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "docs/kor/MACOS_SETUP.md",
        "docs/kor/PROJECT_STRUCTURE.md",
        "docs/eng/PROJECT_STRUCTURE.md",
        "docs/kor/data/AED_HISTORY_ASSESSMENT.md",
        "docs/kor/data/DATA_REQUEST_ROADMAP.md",
        "docs/kor/data/DATA_REQUEST_TEMPLATES.md",
        "docs/kor/data/DATA_ACCESS_REQUIREMENTS.md",
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
        "docs/data/tables/DATA_DICTIONARY_2025.csv",
        "docs/kor/data/DATA_QUALITY.md",
        "docs/kor/data/EDA_2025.md",
        "docs/data/tables/EDA_INDICATOR_DECISIONS_2025.csv",
        "docs/data/manifests/EDA_REPORT_2025.json",
        "docs/data/tables/DOMAIN_SCORE_SPEC_2025.csv",
        "docs/data/manifests/DOMAIN_SCORE_REPORT_2025.json",
        "docs/data/tables/COMPOSITE_INDEX_SPEC_2025.csv",
        "docs/data/manifests/COMPOSITE_INDEX_REPORT_2025.json",
        "docs/data/tables/SENSITIVITY_SCENARIOS_2025.csv",
        "docs/data/manifests/SENSITIVITY_ANALYSIS_REPORT_2025.json",
        "docs/data/manifests/PRIORITY_AREA_REPORT_2025.json",
        "docs/data/manifests/CLUSTER_ANALYSIS_REPORT_2025.json",
        "docs/data/manifests/ENVIRONMENTAL_OVERLAY_REPORT_2025.json",
        "docs/data/manifests/POLICY_MATRIX_REPORT_2025.json",
        "docs/data/manifests/INFOGRAPHIC_REPORT_2025.json",
        "docs/data/manifests/SUBMISSION_DRAFT_REPORT_2025.json",
        "docs/data/manifests/CATEGORY_ASSESSMENT_REPORT_2025.json",
        "docs/data/tables/POLICY_ACTION_CATALOG_2025.csv",
        "docs/data/tables/CATEGORY_ASSESSMENT_SPEC_2025.csv",
        "docs/data/tables/CATEGORY_POLICY_CATALOG_2025.csv",
        "docs/kor/data/DATA_PORTABILITY.md",
        "docs/data/manifests/CONSUMER_SALES_MANIFEST_2025.json",
        "docs/data/manifests/CITY_PARKS_MANIFEST.json",
        "docs/kor/data/STANDARDIZATION.md",
        "docs/eng/data/EDA_2025.md",
        "docs/kor/methodology/DOMAIN_SCORES_2025.md",
        "docs/eng/methodology/DOMAIN_SCORES_2025.md",
        "docs/kor/methodology/COMPOSITE_INDEX_2025.md",
        "docs/eng/methodology/COMPOSITE_INDEX_2025.md",
        "docs/kor/methodology/SENSITIVITY_ANALYSIS_2025.md",
        "docs/eng/methodology/SENSITIVITY_ANALYSIS_2025.md",
        "docs/kor/methodology/PRIORITY_AREAS_2025.md",
        "docs/eng/methodology/PRIORITY_AREAS_2025.md",
        "docs/kor/methodology/CLUSTER_ANALYSIS_2025.md",
        "docs/eng/methodology/CLUSTER_ANALYSIS_2025.md",
        "docs/kor/methodology/ENVIRONMENTAL_OVERLAY_2025.md",
        "docs/eng/methodology/ENVIRONMENTAL_OVERLAY_2025.md",
        "docs/kor/methodology/POLICY_MATRIX_2025.md",
        "docs/eng/methodology/POLICY_MATRIX_2025.md",
        "docs/kor/methodology/INFOGRAPHIC_2025.md",
        "docs/eng/methodology/INFOGRAPHIC_2025.md",
        "docs/kor/methodology/SUBMISSION_DRAFT_2025.md",
        "docs/eng/methodology/SUBMISSION_DRAFT_2025.md",
        "docs/kor/methodology/CATEGORY_ASSESSMENT_2025.md",
        "docs/eng/methodology/CATEGORY_ASSESSMENT_2025.md",
        "outputs/infographic/2025/interactive/html/document.html",
        "outputs/infographic/2025/interactive/css/layout.css",
        "outputs/infographic/2025/interactive/js/boot.js",
        "outputs/infographic/2025/static/busan_imd_one_page_2025.svg",
        "outputs/infographic/2025/static/busan_imd_one_page_2025.pdf",
        "outputs/infographic/2025/static/busan_imd_one_page_2025.png",
        "outputs/infographic/2025/tables/busan_admin_dong_category_assessment_2025.csv",
        "outputs/infographic/2025/tables/busan_admin_dong_major_category_assessment_2025.csv",
        "outputs/infographic/2025/tables/busan_admin_dong_category_indicator_scores_2025.csv",
        "outputs/submission/2025/01_data-visualization.pdf",
        "outputs/submission/2025/02_analysis-report.pdf",
        "outputs/submission/2025/02_analysis-report.md",
        "outputs/submission/2025/README.md",
        "outputs/submission/2025/03_data/source-catalog.xlsx",
        "outputs/submission/2025/03_data/source-catalog.csv",
        "outputs/submission/2025/03_data/data-dictionary.xlsx",
        "outputs/submission/2025/03_data/data-dictionary.csv",
        "outputs/submission/2025/03_data/busan_admin_dong_action_profile_2025.csv",
        "outputs/submission/2025/03_data/busan_admin_dong_category_assessment_2025.csv",
        "outputs/submission/2025/03_data/busan_admin_dong_major_category_assessment_2025.csv",
        "outputs/submission/2025/03_data/busan_admin_dong_category_indicator_scores_2025.csv",
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
    assert any(
        "from busan_imd.analysis.eda import run" in "".join(cell["source"]) for cell in code_cells
    )
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
    assert any("from busan_imd.analysis.cluster_analysis import" in source for source in sources)
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
    assert any(
        "from busan_imd.analysis.environmental_overlay import" in source for source in sources
    )
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
    assert any("from busan_imd.analysis.policy_matrix import" in source for source in sources)
    assert any("px.bar" in source for source in sources)
    assert any("px.scatter" in source for source in sources)
    assert all(cell["execution_count"] is None for cell in code_cells)
    assert all(cell["outputs"] == [] for cell in code_cells)


def test_eda_report_covers_the_canonical_profile() -> None:
    report = read_json("docs/data/manifests/EDA_REPORT_2025.json")

    assert report["profile_record_count"] == 206
    assert report["numeric_indicator_count"] == 85
    assert report["scoring_candidate_numeric_count"] == 37
    assert report["constant_numeric_columns"] == ["air_idw_station_count"]
    assert report["columns_with_missing_values"] == {
        "bus_alighting_2023_validation": 10,
        "bus_boarding_2023_validation": 10,
        "bus_boarding_alighting_2023_validation": 10,
        "late_bus_demand_2023_validation": 10,
        "late_bus_demand_service_mismatch_percentile_2023_current_validation": 13,
        "late_bus_demand_share_pct_2023_validation": 13,
        "late_bus_service_share_pct_current_proxy": 3,
        "peak_bus_demand_2023_validation": 10,
        "peak_bus_demand_share_pct_2023_validation": 13,
        "reachable_multi_leg_trip_share_pct_2025_current_proxy": 2,
        "reachable_youth_child_trip_share_pct_2025_current_proxy": 2,
    }
    assert report["high_correlation_pair_count"] == 7
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
    assert all(re.fullmatch(r"[0-9A-F]{64}", value) for value in report["output_sha256"].values())


def test_cluster_analysis_report_records_cod20_typology_decision() -> None:
    report = read_json("docs/data/manifests/CLUSTER_ANALYSIS_REPORT_2025.json")
    priority_report = read_json("docs/data/manifests/PRIORITY_AREA_REPORT_2025.json")

    assert report["record_count"] == 21
    assert report["candidate_cluster_counts"] == [2, 3, 4, 5, 6]
    assert report["selected_cluster_count"] == 2
    assert report["recommended_for_policy_typology"] is True
    assert report["decision"] == "use_as_exploratory_policy_typology"
    assert report["input_sha256"] == priority_report["output_sha256"]["priority_areas"]
    assert (
        report["selected_metrics"]["mean_seed_stability_ari"]
        >= report["quality_gate"]["minimum_mean_seed_stability_ari"]
    )
    assert {item["cluster_label"] for item in report["cluster_summaries"]} == {
        "education_living_environment",
        "employment_income",
    }
    assert all(re.fullmatch(r"[0-9A-F]{64}", value) for value in report["output_sha256"].values())


def test_environmental_overlay_report_records_cod21_scope() -> None:
    report = read_json("docs/data/manifests/ENVIRONMENTAL_OVERLAY_REPORT_2025.json")
    composite_report = read_json("docs/data/manifests/COMPOSITE_INDEX_REPORT_2025.json")
    standardization_report = read_json("docs/data/manifests/STANDARDIZATION_REPORT_2025.json")

    assert report["record_count"] == 206
    assert report["high_exposure_count"] == 52
    assert report["priority_area_count"] == 21
    assert report["double_burden_count"] == 4
    assert sum(report["category_counts"].values()) == 206
    assert report["decision"] == ("use_for_particulate_independent_double_burden_screening_only")
    assert report["port_industrial_overlay"]["status"] == (
        "not_evaluated_no_versioned_site_geometry"
    )
    assert report["input_sha256"]["composite_index"] == composite_report["output_sha256"]
    assert (
        report["input_sha256"]["standardized_profile"] == standardization_report["profile_sha256"]
    )
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
    assert (
        report["input_sha256"]["cluster_assignments"]
        == cluster_report["output_sha256"]["assignments"]
    )
    assert report["input_sha256"]["environmental_overlay"] == overlay_report["output_sha256"]
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
    assert report["traffic_hotspot_count"] == 48
    assert report["mapped_traffic_hotspot_count"] == 48
    assert report["safety_risk_area_count"] == 70
    assert report["mapped_safety_risk_area_count"] == 67
    assert report["aed_point_count"] == 1079
    assert report["mapped_aed_point_count"] == 1078
    assert report["park_point_count"] == 652
    assert report["mapped_park_point_count"] == 651
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
    html_path = REPOSITORY_ROOT / report["output_paths"]["interactive_action_map"]
    action_map = dashboard_bundle(html_path)
    html = html_path.read_text(encoding="utf-8")
    assert 'href="css/layout.css"' in html
    assert 'src="js/policy.js"' in html
    assert "Assembled dashboard" in html
    assert "__GUIDE__" not in html
    assert report["output_paths"]["interactive_action_map_js_data"].endswith("js/data.js")
    assert action_map.count("data-code=") == 206
    assert action_map.count('class="tree-major"') == 4
    assert action_map.count('class="tree-child"') == 10
    assert 'role="tree"' in action_map
    assert "생활여건 영역 점수 산정" in action_map
    assert "세부 평가항목" in action_map
    assert "영역 점수 반영 비율" in action_map
    assert "percentage(child.weight)" in action_map
    assert '"confidence":"낮음"' in action_map
    assert "자료 신뢰도 ${a.confidence}" in action_map
    assert "큰 카테고리" not in action_map
    assert "하위 카테고리" not in action_map
    assert "추정값 미사용" not in action_map
    assert "산출 설명" not in action_map
    assert "생활 인프라·주거" in action_map
    assert 'data-major-category="safety"' in action_map
    assert "교통사고 위험" in action_map
    assert "정책 설계 참고사례" in action_map
    assert "부산형 DRT '타바라'" in action_map
    assert action_map.count('class="accident-hotspot"') == 48
    assert "교통사고 다발지역 표시" in action_map
    assert "안전 영역의 교통사고 위험 평가에 반영" in action_map
    assert "category==='traffic_accident_risk'?accidentHtml(d.code):''" in action_map
    assert "accidentControl.hidden=!accidentSelected" in action_map
    assert "#accident-layer[hidden]{display:none}" in action_map
    assert "accidentLayer.style.display='none'" in action_map
    assert action_map.count('class="safety-risk-area"') == 67
    assert "생활안전 위험지역 표시" in action_map
    assert "majorCategory==='safety'&&category===null" in action_map
    assert "점수 제외 참고지표" in action_map
    assert "인구 1만 명당 AED" in action_map
    assert "2025 연평균 PM10 추정" in action_map
    assert "일평균 소비매출" in action_map
    assert "행정동 내 도시공원 수" in action_map
    assert action_map.count('class="aed-point"') == 1078
    assert action_map.count('class="park-point"') == 651
    assert "category==='healthcare_supply'" in action_map
    assert "majorCategory==='environment'&&category===null" in action_map
    assert "생활인구 구성" in action_map
    assert "소비매출 상위 업종 구성" in action_map
    assert "주변 학교 학생·교원 비율" in action_map
    assert "부산 교통사고 최근 5년 추이" in action_map
    assert 'id="policy-panel"' in action_map
    assert "function policyHtml(name,code,child)" in action_map
    assert "policyPanel.innerHTML=policyHtml(d.name,d.code,child)" in action_map
    assert "이 동에는 적용하지" in action_map
    assert "이 동의 분포에 따른 정책 판단" in action_map
    assert "정책검토 후보인지 모니터링인지" in action_map
    assert "align-items:stretch" in action_map
    assert "height:min(46vh,440px)" in action_map
    assert "function syncPanelHeights()" in action_map


def test_submission_draft_report_covers_cod24_scope() -> None:
    infographic = read_json("docs/data/manifests/INFOGRAPHIC_REPORT_2025.json")
    report = read_json("docs/data/manifests/SUBMISSION_DRAFT_REPORT_2025.json")

    assert report["artifact_status"] == "submission_draft"
    assert report["cover_pages"] == 1
    assert report["body_pages"] <= 10
    assert report["visualization_page_count"] == 1
    assert report["dataset_count"] == 42
    assert report["hwpx_status"] == "hangul_paste_required"
    assert report["output_sha256"]["visualization_pdf"] == infographic["output_sha256"]["pdf"]
    assert not (REPOSITORY_ROOT / "outputs/submission/2025/02_analysis-report.hwpx").exists()
    markdown = (REPOSITORY_ROOT / report["output_paths"]["report_markdown"]).read_text(
        encoding="utf-8"
    )
    for title in REQUIRED_SECTION_TITLES:
        assert f"## {title}" in markdown
    for name, relative_path in report["output_paths"].items():
        path = REPOSITORY_ROOT / relative_path
        assert path.is_file()
        if name in report["output_sha256"]:
            actual_hash = hashlib.sha256(path.read_bytes()).hexdigest().upper()
            assert actual_hash == report["output_sha256"][name]
    for table in report["analysis_tables"]:
        path = REPOSITORY_ROOT / table
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest().upper()
        assert actual_hash == report["output_sha256"][Path(table).name]
    visualization = (REPOSITORY_ROOT / report["output_paths"]["visualization_pdf"]).read_bytes()
    assert len(re.findall(rb"/Type\s*/Page\b", visualization)) == 1
    pdf = (REPOSITORY_ROOT / report["output_paths"]["report_pdf"]).read_bytes()
    assert len(re.findall(rb"/Type\s*/Page\b", pdf)) == report["total_pages"]
    catalog = pd.read_excel(
        REPOSITORY_ROOT / report["output_paths"]["source_catalog"],
        engine="openpyxl",
    )
    catalog_csv = pd.read_csv(REPOSITORY_ROOT / report["output_paths"]["source_catalog_csv"])
    assert len(catalog) == 42
    assert catalog["dataset_id"].tolist() == catalog_csv["dataset_id"].tolist()
    readme_path = REPOSITORY_ROOT / report["output_paths"]["package_readme"]
    assert "Hangul" in readme_path.read_text(encoding="utf-8")
    assert len(report["analysis_tables"]) == 4


def test_category_assessment_is_complete_and_flags_estimation() -> None:
    report = read_json("docs/data/manifests/CATEGORY_ASSESSMENT_REPORT_2025.json")

    assert report["admin_dong_count"] == 206
    assert report["major_category_count"] == 4
    assert report["category_count"] == 10
    assert report["indicator_count"] == 19
    assert report["category_score_row_count"] == 206 * 10
    assert report["major_category_score_row_count"] == 206 * 4
    assert report["indicator_score_row_count"] == 206 * 19
    assert report["policy_trigger_threshold"] == 70
    for name, relative_path in report["output_paths"].items():
        actual = hashlib.sha256((REPOSITORY_ROOT / relative_path).read_bytes()).hexdigest().upper()
        assert actual == report["output_sha256"][name]
    categories = pd.read_csv(
        REPOSITORY_ROOT / report["output_paths"]["category_assessment"],
        dtype={"admin_dong_code": str},
    )
    assert categories.groupby("admin_dong_code")["category"].nunique().eq(10).all()
    major_categories = pd.read_csv(
        REPOSITORY_ROOT / report["output_paths"]["major_category_assessment"],
        dtype={"admin_dong_code": str},
    )
    assert major_categories.groupby("admin_dong_code")["major_category"].nunique().eq(4).all()
    assert major_categories["major_category_score_0_100"].between(0, 100).all()
    myeongji = categories[
        categories["admin_dong_name"].isin(["명지1동", "명지2동"])
        & (categories["category"] == "education_access_supply")
    ]
    assert len(myeongji) == 2
    assert myeongji["category_score_0_100"].lt(70).all()
    indicators = pd.read_csv(REPOSITORY_ROOT / report["output_paths"]["indicator_scores"])
    assert {"estimate_used", "estimation_method_ko", "estimation_reason"} <= set(indicators.columns)
    estimated = indicators[indicators["estimate_used"]]
    assert len(estimated) == 206 * 13
    assert estimated["estimation_reason"].str.len().gt(0).all()


def test_dataset_audit_is_valid() -> None:
    rows = validate_catalog(REPOSITORY_ROOT / "docs/data/tables/DATASET_AUDIT.csv")

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
    manifest = read_json("docs/data/manifests/BASIC_LIVELIHOOD_INFERENCE_MANIFEST_2025.json")
    validate_income_manifest(manifest, REPOSITORY_ROOT)

    assert manifest["reference_period"] == "2025-12"
    assert manifest["district_totals_are_observed"] is True
    assert manifest["admin_dong_values_are_inferred"] is True
    assert manifest["record_count"] == 206
    assert manifest["district_count"] == 16
    assert manifest["observed_pattern_admin_dongs"] == 86
    assert manifest["district_people_total"] == 256393
    assert manifest["analysis_role"] == "provisional_scoring_proxy"
    assert manifest["lineage"]["district_total_dataset_id"] == ("INC-WELFARE-SIGUNGU-2025-001")
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
        "EDU-SCHOOLINFO-2025-001",
        "ENV-AIR-HEIS-DAILY-2025-001",
    }
    assert set(report["analysis_roles"]["validation_only"]) == {
        "SOC-BUSAN-ELDERLY-ALONE-001",
        "HLT-AED-001",
        "DEM-BUSAN-LIVING-001",
    }
    assert set(report["analysis_roles"]["supplemental_category_indicator"]) == {
        "TRN-BUSAN-ROUTE-USAGE-2025-001",
        "TRN-BUSAN-BIMS-CURRENT-001",
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
        "docs/data/manifests/SCHOOLINFO_DISCLOSURE_MANIFEST_2025.json",
        "docs/data/manifests/BUS_SERVICE_CURRENT_MANIFEST.json",
    ):
        text = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
        assert "serviceKey=" not in text
        assert "accessToken=" not in text
        assert "consumer_secret" not in text
        assert "consumer_key" not in text
