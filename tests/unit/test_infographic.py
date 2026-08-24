from __future__ import annotations

import re

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from busan_imd.infographic import (
    DOMAIN_COLUMNS,
    INDICATOR_PRESENTATION,
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
    policy = pd.DataFrame({"policy_title_ko": ["정책 후보"] * 5})
    return composite, boundaries, priority, overlay, policy


def test_render_writes_one_page_vector_pdf_and_preview(tmp_path) -> None:
    composite, boundaries, priority, overlay, policy = inputs()
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
    indicator_to_domain = {
        "basic_livelihood_recipients_per_1000_population_2025_inferred": "income",
        "workplace_workers_2024": "employment",
        "nearest_core_school_distance_m_2025": "education",
        "hospital_count_2025_candidate_per_10000_population": "health",
        "clinic_count_2025_candidate_per_10000_population": "health",
        "old_house_share_30plus_2024_lower_bound_pct": "housing_access",
        "bus_stop_count_2025_per_10000_population": "housing_access",
        "heat_shelter_count_2025_per_10000_population": "living_environment",
        "annual_pm25_ug_m3_idw_2025": "living_environment",
    }
    indicator_scores = pd.DataFrame(
        [
            {
                "admin_dong_code": code,
                "domain": indicator_to_domain[indicator],
                "indicator": indicator,
                "raw_value": 10,
                "deprivation_percentile_0_100": 75,
                "within_domain_weight": 1,
            }
            for code in composite["admin_dong_code"]
            for indicator in INDICATOR_PRESENTATION
        ]
    )
    policy_catalog = pd.DataFrame(
        [
            {
                "trigger_kind": "domain",
                "trigger_value": domain,
                "policy_title_ko": f"{label} 정책",
                "lead_implementer": "담당부서",
                "expected_effect": "접근성 개선",
                "monitoring_indicator": "연계율",
                "evidence_limit": "현장 검증 필요",
            }
            for domain, (_, label) in DOMAIN_COLUMNS.items()
        ]
    )

    write_action_map(profiles, boundaries, indicator_scores, policy_catalog, html_path)

    assert len(profiles) == 206
    assert profiles.loc[0, "primary_vulnerability_ko"] == "교육"
    assert profiles.loc[0, "relative_low_deprivation_ko"] == "생활환경"
    assert profiles["specialization_evidence_status"].str.contains("특화 확정 불가").all()
    html = html_path.read_text(encoding="utf-8")
    assert html.count("data-code=") == 206
    assert "카테고리별 평가와 정책 예시" in html
    assert html.count("data-domain=") == 6
    assert "취약 백분위" in html


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
