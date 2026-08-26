from __future__ import annotations

import re
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

import busan_imd.infographic.presentation.rendering as infographic_rendering
from busan_imd.infographic import (
    build_action_profiles,
    render,
    write_action_map,
)
from busan_imd.infographic.presentation.dashboard.assemble import ASSET_ROOT


def dashboard_bundle(html_path: Path) -> str:
    root = html_path.parent
    parts = [html_path.read_text(encoding="utf-8")]
    for folder in ("css", "js"):
        for path in sorted((root / folder).iterdir()):
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def inputs() -> tuple[
    pd.DataFrame,
    gpd.GeoDataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    codes = [f"{index:03d}" for index in range(206)]
    composite = pd.DataFrame(
        {
            "admin_dong_code": codes,
            "sigungu_name": "District",
            "admin_dong_name": [f"Dong {index}" for index in range(206)],
            "b_imd_score_0_100": [100 - index / 3 for index in range(206)],
            "b_imd_rank": list(range(1, 207)),
            "b_imd_decile": [min(index * 10 // 206 + 1, 10) for index in range(206)],
            "education_score_0_100": [90 - index / 4 for index in range(206)],
            "employment_score_0_100": [80 - index / 4 for index in range(206)],
            "health_score_0_100": [70 - index / 4 for index in range(206)],
            "housing_access_score_0_100": [60 - index / 4 for index in range(206)],
            "income_score_0_100": [50 - index / 4 for index in range(206)],
            "living_environment_score_0_100": [40 - index / 4 for index in range(206)],
        }
    )
    boundaries = gpd.GeoDataFrame(
        {"adm_cd": codes},
        geometry=[
            box(index % 20, index // 20, index % 20 + 0.9, index // 20 + 0.9)
            for index in range(206)
        ],
        crs="EPSG:5179",
    )
    priority = composite.iloc[:21].copy()
    overlay = pd.DataFrame(
        {
            "admin_dong_code": codes,
            "double_burden": [index < 4 for index in range(206)],
        }
    )
    policy = pd.DataFrame(
        [
            {
                "cluster_id": "type_1",
                "policy_trigger": "domain:education",
                "policy_title_ko": "교육 접근 점검",
                "target_area_count": 5,
                "target_admin_dongs": "District Dong 0",
            },
            {
                "cluster_id": "type_1",
                "policy_trigger": "overlay:double_burden",
                "policy_title_ko": "대기질 점검",
                "target_area_count": 1,
                "target_admin_dongs": "District Dong 0",
            },
            {
                "cluster_id": "type_2",
                "policy_trigger": "domain:employment",
                "policy_title_ko": "고용 연계",
                "target_area_count": 16,
                "target_admin_dongs": "District Dong 1",
            },
        ]
    )
    return composite, boundaries, priority, overlay, policy


@pytest.mark.filterwarnings("ignore:Glyph .* missing from font")
def test_render_writes_one_page_vector_pdf_and_preview(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    composite, boundaries, priority, overlay, policy = inputs()
    monkeypatch.setattr(infographic_rendering, "_font_family", lambda: "DejaVu Sans")
    svg_path = tmp_path / "visual.svg"
    pdf_path = tmp_path / "visual.pdf"
    png_path = tmp_path / "visual.png"

    summary = render(
        composite,
        boundaries,
        priority,
        overlay,
        policy,
        svg_path,
        pdf_path,
        png_path,
    )

    assert summary["page_count"] == 1
    assert summary["priority_area_count"] == 21
    assert summary["double_burden_area_count"] == 4
    assert svg_path.read_text(encoding="utf-8").count("<svg") == 1
    assert len(re.findall(rb"/Type\s*/Page\b", pdf_path.read_bytes())) == 1
    assert png_path.stat().st_size > 10_000


def test_action_profiles_and_map_cover_every_dong(tmp_path) -> None:
    composite, boundaries, *_ = inputs()
    profiles = build_action_profiles(composite)
    html_path = tmp_path / "action-map.html"
    categories = {
        "income_support_need": "소득·복지수요",
        "local_employment_opportunity": "지역 고용기회",
        "education_access_supply": "교육시설 접근·공급",
        "healthcare_supply": "의료공급 접근",
        "housing_condition": "주거환경",
        "transit_access": "대중교통 접근",
        "air_exposure": "대기오염 노출",
        "heat_response": "폭염 대응",
    }
    category_assessments = pd.DataFrame(
        [
            {
                "admin_dong_code": code,
                "category": category,
                "category_label": label,
                "major_category": (
                    "social"
                    if category in {"income_support_need", "local_employment_opportunity"}
                    else "services"
                ),
                "major_category_weight": (
                    0.5
                    if category in {"income_support_need", "local_employment_opportunity"}
                    else 1 / 6
                ),
                "category_score_0_100": 75,
                "category_confidence": "medium_low",
                "policy_review_status": "candidate_after_validation",
                "triggered_indicators": "평가지표",
            }
            for code in composite["admin_dong_code"]
            for category, label in categories.items()
        ]
    )
    major_labels = {"social": "사회·경제 기반", "services": "생활·환경 기반"}
    major_category_assessments = pd.DataFrame(
        [
            {
                "admin_dong_code": code,
                "major_category": major,
                "major_category_label": label,
                "major_category_score_0_100": 75,
                "major_category_confidence": "low",
                "policy_review_status": "candidate_after_validation",
                "triggered_child_categories": "소득·복지수요",
            }
            for code in composite["admin_dong_code"]
            for major, label in major_labels.items()
        ]
    )
    indicator_scores = pd.DataFrame(
        [
            {
                "admin_dong_code": code,
                "category": category,
                "indicator_label": "평가지표",
                "raw_or_derived_value": 10,
                "deprivation_percentile_0_100": 75,
                "within_category_weight": 1,
                "evidence_type": "proxy",
                "value_status_ko": "추정·보정값",
                "estimate_used": True,
                "estimation_method_ko": "소지역 보정",
                "estimation_reason": "작은 인구 분모의 과대변동 완화",
                "confidence_level": "medium_low",
                "quality_note": "현장 검증 필요",
                "indicator_policy_triggered": True,
            }
            for code in composite["admin_dong_code"]
            for category in categories
        ]
    )
    policy_catalog = pd.DataFrame(
        [
            {
                "category": category,
                "policy_title_ko": f"{label} 정책",
                "lead_implementer": "담당부서",
                "problem_signal_ko": "상대적으로 높은 취약도",
                "priority_target_ko": "현장 검증 대상",
                "implementation_steps_ko": "자료 확인 → 시범사업 → 성과평가",
                "policy_example": "검증 후 개선",
                "monitoring_indicator": "연계율",
                "policy_case_ko": "공공 정책 사례",
                "policy_case_source_url": "https://example.test/policy",
                "case_application_note_ko": "사례를 그대로 복제하지 않음",
                "evidence_limit": "현장 검증 필요",
            }
            for category, label in categories.items()
        ]
    )
    traffic_hotspots = gpd.GeoDataFrame(
        {
            "spot_nm": ["시험 교차로"],
            "occrrnc_cnt": [7],
            "caslt_cnt": [9],
        },
        geometry=gpd.points_from_xy([0.45], [0.45]),
        crs=boundaries.crs,
    )
    reference_context = pd.DataFrame(
        {
            "admin_dong_code": composite["admin_dong_code"],
            "aed_count_current_unverified_per_10000_population": range(206),
            "annual_pm10_ug_m3_idw_2025": range(206),
            "annual_no2_ppm_idw_2025": range(206),
            "annual_o3_ppm_idw_2025": range(206),
            "air_idw_station_count": range(206),
            "nearest_air_station_distance_m": range(206),
            "core_school_students_within_2000m_2025": range(206),
            "core_school_teachers_within_2000m_2025": range(1, 207),
            "students_per_teacher_within_2000m_2025": range(206),
            "core_school_teachers_per_1000_under_20_living_population_2025_context": range(206),
            "healthcare_facilities_per_1000_senior_living_population_2025_context": range(206),
            "boundary_adjusted_healthcare_access_2000m_2025_context": range(206),
            "avg_daily_residential_living_population_2025": range(206),
            "avg_daily_workplace_living_population_2025": range(206),
            "avg_daily_visitor_living_population_2025": range(206),
            "senior_living_population_share_pct_2025": range(206),
            "under_20_living_population_share_pct_2025": range(206),
            "under_30_living_population_share_pct_2025": range(206),
            "daytime_to_residential_living_population_ratio_2025": range(206),
            "reachable_multi_leg_trip_share_pct_2025_current_proxy": range(206),
            "reachable_youth_child_trip_share_pct_2025_current_proxy": range(206),
            "bus_boarding_alighting_2023_validation": range(206),
            "peak_bus_demand_share_pct_2023_validation": range(206),
            "late_bus_demand_share_pct_2023_validation": range(206),
            "bus_service_opportunities_per_1000_total_living_population_context": range(206),
            "bus_service_opportunities_per_1000_senior_living_population_context": range(206),
            "late_bus_service_share_pct_current_proxy": range(206),
            "late_bus_demand_service_mismatch_percentile_2023_current_validation": range(206),
            "boundary_adjusted_bus_stop_access_1000m_2025_context": range(206),
            "consumer_sales_avg_daily_amount_2025": range(206),
            "consumer_sales_avg_daily_transactions_2025": range(206),
            "consumer_sales_under_30_transaction_share_pct_2025": range(206),
            "consumer_sales_senior_transaction_share_pct_2025": range(206),
            "consumer_sales_late_night_transaction_share_pct_2025": range(206),
            "consumer_sales_daytime_transaction_share_pct_2025": range(206),
            "senior_consumer_minus_living_share_pp_2025_context": range(206),
            "under_30_consumer_minus_living_share_pp_2025_context": range(206),
            "living_consumer_age_composition_divergence_pp_2025_context": range(206),
            "heat_shelters_per_1000_senior_living_population_2025_context": range(206),
            "boundary_adjusted_heat_shelter_access_1000m_2025_context": range(206),
            "park_count_current": range(206),
            "nearest_park_distance_m_current": range(206),
            "district_accident_count_2025": range(206),
            "district_accidents_per_100k_2025": range(206),
        }
    )
    safety_risk_areas = gpd.GeoDataFrame(
        {
            "경도": [0.55],
            "위도": [0.55],
            "사고유형": ["수난"],
            "출동횟수": [3],
            "상세위치": ["시험 저수지"],
        },
        geometry=gpd.points_from_xy([0.55], [0.55]),
        crs=boundaries.crs,
    )

    write_action_map(
        profiles,
        boundaries,
        category_assessments,
        major_category_assessments,
        indicator_scores,
        policy_catalog,
        html_path,
        traffic_hotspots,
        reference_context,
        safety_risk_areas,
    )

    assert len(profiles) == 206
    assert profiles.loc[0, "primary_vulnerability_ko"] == "교육"
    assert profiles.loc[0, "relative_low_deprivation_ko"] == "생활환경"
    assert profiles["specialization_evidence_status"].str.contains("특화 확정 불가").all()
    html = html_path.read_text(encoding="utf-8")
    bundle = dashboard_bundle(html_path)
    assert "Assembled dashboard" in html
    assert "__GUIDE__" not in html
    assert "__GUIDE__" in (ASSET_ROOT / "html" / "document.html").read_text(encoding="utf-8")
    assert 'href="css/policy.css"' in html
    assert 'src="js/data.js"' in html
    assert 'src="js/boot.js"' in html
    assert html.count("data-code=") == 206
    assert "부산 행정동 생활여건 진단: 취약 요인과 정책 방향" in html
    assert html.count('class="tree-major"') == 2
    assert html.count('class="tree-child"') == len(categories)
    assert 'role="tree"' in html
    assert "function selectNode(nextMajor,nextCategory=null)" in bundle
    assert "생활여건 영역 점수 산정" in html
    assert "단순 평균이 아니며" in html
    assert "세부 평가항목" in html
    assert "취약도 백분위" in bundle
    assert "영역 점수 반영 비율" in bundle
    assert "percentage(child.weight)" in bundle
    assert '"confidence":"낮음"' in bundle
    assert "자료 신뢰도 ${a.confidence}" in bundle
    assert "큰 카테고리" not in bundle
    assert "하위 카테고리" not in bundle
    assert "추정값 사용" in bundle
    assert "사용 사유" in bundle
    assert "추정값 미사용" not in bundle
    assert "산출 설명" not in bundle
    assert "정책 설계 참고사례" in bundle
    assert "실행 순서" in bundle
    assert html.count('class="accident-hotspot"') == 1
    assert "교통사고 다발지역 표시" in html
    assert "category==='traffic_accident_risk'?accidentHtml(d.code):''" in bundle
    assert "accidentControl.hidden=!accidentSelected" in bundle
    assert "#accident-layer[hidden]{display:none}" in bundle
    assert "accidentLayer.style.display='none'" in bundle
    assert "점수 제외 참고지표" in bundle
    assert "인구 1만 명당 AED" in bundle
    assert "2025 연평균 PM10 추정" in bundle
    assert "일평균 소비매출" in bundle
    assert "행정동 내 도시공원 수" in bundle
    assert "행정동 중심점 최근접 도시공원 거리" in bundle
    assert html.count('class="safety-risk-area"') == 1
    assert "생활안전 위험지역 표시" in html
    assert "majorCategory==='safety'&&category===null" in bundle
    assert '"occurrence_count":7' in bundle
    assert "안전 영역의 교통사고 위험 평가에 반영" in html
    assert 'id="policy-panel"' in html
    assert "function policyHtml(name,code,child)" in bundle
    assert "policyPanel.innerHTML=policyHtml(d.name,d.code,child)" in bundle
    assert "이 동에는 적용하지" in bundle
    assert "이 동의 분포에 따른 정책 판단" in bundle
    assert "정책검토 후보인지 모니터링인지" in html
    assert "오른쪽에서 평가지표, 추정 사유, 신뢰도와 조건부 정책 예시" not in html
    assert "align-items:stretch" in bundle
    assert "height:min(46vh,440px)" in bundle
    assert "function syncPanelHeights()" in bundle
    assert "box-sizing:border-box" in bundle


def test_render_rejects_incomplete_canonical_population(tmp_path) -> None:
    composite, boundaries, priority, overlay, policy = inputs()

    with pytest.raises(ValueError, match="206 unique"):
        render(
            composite.iloc[:-1],
            boundaries.iloc[:-1],
            priority,
            overlay.iloc[:-1],
            policy,
            tmp_path / "visual.svg",
            tmp_path / "visual.pdf",
            tmp_path / "visual.png",
        )


def test_render_rejects_priority_values_from_another_rebuild(tmp_path) -> None:
    composite, boundaries, priority, overlay, policy = inputs()
    priority.loc[0, "b_imd_score_0_100"] = -1

    with pytest.raises(ValueError, match="match the current composite"):
        render(
            composite,
            boundaries,
            priority,
            overlay,
            policy,
            tmp_path / "visual.svg",
            tmp_path / "visual.pdf",
            tmp_path / "visual.png",
        )


def test_render_rejects_overlay_code_drift(tmp_path) -> None:
    composite, boundaries, priority, overlay, policy = inputs()
    overlay.loc[0, "admin_dong_code"] = "missing"

    with pytest.raises(ValueError, match="Composite and overlay"):
        render(
            composite,
            boundaries,
            priority,
            overlay,
            policy,
            tmp_path / "visual.svg",
            tmp_path / "visual.pdf",
            tmp_path / "visual.png",
        )


def test_font_selection_fails_clearly_without_hangul_font(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(infographic_rendering, "findSystemFonts", lambda: [])

    with pytest.raises(RuntimeError, match="Noto Sans CJK"):
        infographic_rendering._font_family()
