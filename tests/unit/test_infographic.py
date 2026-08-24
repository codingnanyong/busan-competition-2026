from __future__ import annotations

import re

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

import busan_imd.infographic as infographic
from busan_imd.infographic import (
    build_action_profiles,
    render,
    write_action_map,
)


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
    monkeypatch.setattr(infographic, "_font_family", lambda: "DejaVu Sans")
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
                    "social" if category in {"income_support_need", "local_employment_opportunity"}
                    else "services"
                ),
                "major_category_weight": (
                    0.5 if category in {"income_support_need", "local_employment_opportunity"}
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
                "triggered_child_categories": "하위 카테고리",
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
                "policy_example": "검증 후 개선",
                "monitoring_indicator": "연계율",
                "evidence_limit": "현장 검증 필요",
            }
            for category, label in categories.items()
        ]
    )

    write_action_map(
        profiles,
        boundaries,
        category_assessments,
        major_category_assessments,
        indicator_scores,
        policy_catalog,
        html_path,
    )

    assert len(profiles) == 206
    assert profiles.loc[0, "primary_vulnerability_ko"] == "교육"
    assert profiles.loc[0, "relative_low_deprivation_ko"] == "생활환경"
    assert profiles["specialization_evidence_status"].str.contains("특화 확정 불가").all()
    html = html_path.read_text(encoding="utf-8")
    assert html.count("data-code=") == 206
    assert "근거가 보이는 평가와 정책 예시" in html
    assert html.count("data-major-category=") == 2
    assert "큰 카테고리 점수 =" in html
    assert "하위 카테고리" in html
    assert "취약 백분위" in html
    assert "추정값 사용" in html
    assert "사용 사유" in html


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
    monkeypatch.setattr(infographic, "findSystemFonts", lambda: [])

    with pytest.raises(RuntimeError, match="Noto Sans CJK"):
        infographic._font_family()
