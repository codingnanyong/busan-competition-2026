"""Render the reproducible one-page 2025 B-IMD map and infographic draft."""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from pathlib import Path
from textwrap import fill
from typing import Any

import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.font_manager import FontProperties, findSystemFonts
from matplotlib.lines import Line2D

from busan_imd.infographic.config import (
    DOMAIN_COLUMNS,
    EXPECTED_DONG_COUNT,
    EXPECTED_PRIORITY_COUNT,
    PALETTE,
)
from busan_imd.infographic.domain.profiles import build_action_profiles
from busan_imd.infographic.presentation.dashboard import write_dashboard_files


def _font_family() -> str:
    candidates = [path for path in findSystemFonts() if "NotoSansCJK-Regular" in path]
    if not candidates:
        raise RuntimeError(
            "Noto Sans CJK is required to render Korean infographic text; "
            "use the project Docker image or install NotoSansCJK-Regular"
        )
    mpl.font_manager.fontManager.addfont(candidates[0])
    return FontProperties(fname=candidates[0]).get_name()


def _validate(
    composite: pd.DataFrame,
    boundaries: gpd.GeoDataFrame,
    priority: pd.DataFrame,
    overlay: pd.DataFrame,
    policy_matrix: pd.DataFrame,
) -> None:
    required_composite = {
        "admin_dong_code",
        "sigungu_name",
        "admin_dong_name",
        "b_imd_score_0_100",
        "b_imd_rank",
        "b_imd_decile",
    }
    missing = sorted(required_composite - set(composite.columns))
    if missing:
        raise ValueError(f"Composite input is missing columns: {missing}")
    for name, frame in (("Composite", composite), ("Overlay", overlay)):
        if len(frame) != EXPECTED_DONG_COUNT or frame["admin_dong_code"].duplicated().any():
            raise ValueError(f"{name} requires 206 unique administrative-dong rows")
    boundary_codes = boundaries["adm_cd"].astype(str)
    if len(boundaries) != EXPECTED_DONG_COUNT or boundary_codes.duplicated().any():
        raise ValueError("Boundary input requires 206 unique administrative-dong geometries")
    if len(priority) != EXPECTED_PRIORITY_COUNT or priority["admin_dong_code"].duplicated().any():
        raise ValueError("Priority input requires 21 unique administrative-dong rows")
    if set(composite["admin_dong_code"].astype(str)) != set(boundaries["adm_cd"].astype(str)):
        raise ValueError("Composite and boundary administrative-dong codes must match")
    if set(composite["admin_dong_code"].astype(str)) != set(overlay["admin_dong_code"].astype(str)):
        raise ValueError("Composite and overlay administrative-dong codes must match")
    if not set(priority["admin_dong_code"].astype(str)).issubset(
        set(composite["admin_dong_code"].astype(str))
    ):
        raise ValueError("Priority areas must be a subset of the composite")
    comparison_columns = [
        "admin_dong_code",
        "sigungu_name",
        "admin_dong_name",
        "b_imd_score_0_100",
        "b_imd_rank",
        "b_imd_decile",
    ]
    provided_priority = (
        priority[comparison_columns].sort_values("admin_dong_code").reset_index(drop=True)
    )
    canonical_priority = (
        composite[composite["admin_dong_code"].isin(priority["admin_dong_code"])][
            comparison_columns
        ]
        .sort_values("admin_dong_code")
        .reset_index(drop=True)
    )
    try:
        pd.testing.assert_frame_equal(provided_priority, canonical_priority, check_dtype=False)
    except AssertionError as error:
        raise ValueError("Priority rows must match the current composite values") from error
    required_policy = {
        "cluster_id",
        "policy_trigger",
        "policy_title_ko",
        "target_area_count",
        "target_admin_dongs",
    }
    if "double_burden" not in overlay or not required_policy <= set(policy_matrix.columns):
        raise ValueError("Overlay and policy-matrix inputs are missing presentation columns")
    if policy_matrix["cluster_id"].nunique() != 2:
        raise ValueError("One-page policy panel requires exactly two policy clusters")


def _policy_cards(policy_matrix: pd.DataFrame) -> list[tuple[float, str, str, str, str]]:
    """Derive the two one-page policy cards from the regenerated policy matrix."""
    cards: list[tuple[float, str, str, str, str]] = []
    positions = (0.025, 0.515)
    colors = (PALETTE["gold"], PALETTE["blue"])
    for index, (_, rows) in enumerate(policy_matrix.groupby("cluster_id", sort=True)):
        domain_rows = rows[rows["policy_trigger"].str.startswith("domain:")].sort_values(
            "policy_trigger"
        )
        overlay_rows = rows[rows["policy_trigger"].eq("overlay:double_burden")]
        domain_keys = domain_rows["policy_trigger"].str.removeprefix("domain:")
        if domain_rows.empty or not set(domain_keys) <= set(DOMAIN_COLUMNS):
            raise ValueError("Every policy cluster requires known domain-trigger rows")
        labels = [DOMAIN_COLUMNS[key][1] for key in domain_keys]
        target_count = int(domain_rows["target_area_count"].max())
        title = f"{'·'.join(labels)}형 · {target_count}개 동"
        action = fill(
            " + ".join(domain_rows["policy_title_ko"].astype(str)),
            width=30,
            break_long_words=True,
        )
        if overlay_rows.empty:
            detail = "환경 이중부담 병행 대상 없음"
        else:
            overlay = overlay_rows.iloc[0]
            targets = str(overlay["target_admin_dongs"]).replace("|", "·")
            detail = fill(
                f"{targets}: {overlay['policy_title_ko']} 병행",
                width=30,
                break_long_words=True,
            )
        cards.append((positions[index], title, action, detail, colors[index]))
    return cards


def _panel(ax: plt.Axes) -> None:
    ax.set_facecolor(PALETTE["panel"])
    for spine in ax.spines.values():
        spine.set_color(PALETTE["line"])
        spine.set_linewidth(0.8)


def _geometry_svg_path(geometry: Any, bounds: tuple[float, float, float, float]) -> str:
    min_x, min_y, max_x, max_y = bounds
    width = max_x - min_x
    height = max_y - min_y

    def point(x: float, y: float) -> str:
        return f"{(x - min_x) / width * 900:.2f},{(max_y - y) / height * 900:.2f}"

    polygons = [geometry] if geometry.geom_type == "Polygon" else list(geometry.geoms)
    parts: list[str] = []
    for polygon in polygons:
        for ring in (polygon.exterior, *polygon.interiors):
            coordinates = list(ring.coords)
            parts.append("M" + " L".join(point(x, y) for x, y in coordinates) + " Z")
    return " ".join(parts)


def write_action_map(
    profiles: pd.DataFrame,
    boundaries: gpd.GeoDataFrame,
    category_assessments: pd.DataFrame,
    major_category_assessments: pd.DataFrame,
    indicator_scores: pd.DataFrame,
    policy_catalog: pd.DataFrame,
    output_path: Path,
    traffic_hotspots: pd.DataFrame | gpd.GeoDataFrame | None = None,
    reference_context: pd.DataFrame | None = None,
    safety_risk_areas: pd.DataFrame | gpd.GeoDataFrame | None = None,
    consumer_sales_by_category: pd.DataFrame | None = None,
    aed_points: gpd.GeoDataFrame | None = None,
    park_points: pd.DataFrame | gpd.GeoDataFrame | None = None,
    traffic_citywide_trend: pd.DataFrame | None = None,
) -> dict[str, int]:
    """Write a category dashboard with explicit evidence labels and policy gates."""
    confidence_labels = {
        "high": "높음",
        "medium": "보통",
        "medium_low": "다소 낮음",
        "low": "낮음",
    }

    def confidence_label(value: Any) -> str:
        normalized = str(value).strip().lower()
        return confidence_labels.get(normalized, str(value))

    map_data = boundaries.copy()
    map_data["adm_cd"] = map_data["adm_cd"].astype(str)
    map_data = map_data.merge(
        profiles,
        left_on="adm_cd",
        right_on="admin_dong_code",
        validate="one_to_one",
    )
    bounds = tuple(float(value) for value in map_data.total_bounds)
    if boundaries.crs is None:
        raise ValueError("Boundary geometry requires a declared CRS for reference layers")
    boundary_lookup = boundaries[["adm_cd", "geometry"]].copy()
    boundary_lookup["adm_cd"] = boundary_lookup["adm_cd"].astype(str)
    accident_summary: dict[str, dict[str, int]] = {}
    hotspot_circles: list[str] = []
    mapped_hotspot_count = 0
    if traffic_hotspots is not None and not traffic_hotspots.empty:
        required_hotspot_columns = {"spot_nm", "occrrnc_cnt", "caslt_cnt"}
        missing_hotspot_columns = required_hotspot_columns - set(traffic_hotspots.columns)
        if missing_hotspot_columns:
            raise ValueError(
                f"Traffic hotspots are missing columns: {sorted(missing_hotspot_columns)}"
            )
        if isinstance(traffic_hotspots, gpd.GeoDataFrame):
            hotspot_points = traffic_hotspots.copy()
            if hotspot_points.crs is None:
                raise ValueError("Traffic hotspot geometry requires a declared CRS")
        else:
            coordinate_columns = {"lo_crd", "la_crd"}
            missing_coordinates = coordinate_columns - set(traffic_hotspots.columns)
            if missing_coordinates:
                raise ValueError(
                    f"Traffic hotspots are missing coordinates: {sorted(missing_coordinates)}"
                )
            hotspot_points = gpd.GeoDataFrame(
                traffic_hotspots.copy(),
                geometry=gpd.points_from_xy(
                    pd.to_numeric(traffic_hotspots["lo_crd"]),
                    pd.to_numeric(traffic_hotspots["la_crd"]),
                ),
                crs="EPSG:4326",
            )
        hotspot_points = hotspot_points.to_crs(boundaries.crs)
        hotspot_points = gpd.sjoin(
            hotspot_points,
            boundary_lookup,
            how="left",
            predicate="within",
        )
        mapped_hotspots = hotspot_points[hotspot_points["adm_cd"].notna()].copy()
        mapped_hotspot_count = len(mapped_hotspots)
        for code, rows in mapped_hotspots.groupby("adm_cd", sort=False):
            accident_summary[str(code)] = {
                "location_count": int(len(rows)),
                "occurrence_count": int(pd.to_numeric(rows["occrrnc_cnt"]).sum()),
                "casualty_count": int(pd.to_numeric(rows["caslt_cnt"]).sum()),
            }
        min_x, min_y, max_x, max_y = bounds
        width = max_x - min_x
        height = max_y - min_y
        for row in mapped_hotspots.itertuples(index=False):
            occurrence_count = int(row.occrrnc_cnt)
            cx = (row.geometry.x - min_x) / width * 900
            cy = (max_y - row.geometry.y) / height * 900
            radius = min(10.0, 3.0 + occurrence_count**0.5 * 0.55)
            title = escape(
                f"{row.spot_nm}: 사고 {occurrence_count}건, 사상자 {int(row.caslt_cnt)}명"
            )
            hotspot_circles.append(
                f'<circle class="accident-hotspot" cx="{cx:.2f}" cy="{cy:.2f}" '
                f'r="{radius:.2f}" data-hotspot-code="{row.adm_cd}">'
                f"<title>{title}</title></circle>"
            )
    safety_risk_markers: list[str] = []
    mapped_safety_risk_count = 0
    if safety_risk_areas is not None and not safety_risk_areas.empty:
        required_risk_columns = {"경도", "위도", "사고유형", "출동횟수", "상세위치"}
        missing_risk_columns = required_risk_columns - set(safety_risk_areas.columns)
        if missing_risk_columns:
            raise ValueError(
                f"Safety risk areas are missing columns: {sorted(missing_risk_columns)}"
            )
        if isinstance(safety_risk_areas, gpd.GeoDataFrame):
            risk_points = safety_risk_areas.copy()
            if risk_points.crs is None:
                raise ValueError("Safety risk geometry requires a declared CRS")
        else:
            risk_points = gpd.GeoDataFrame(
                safety_risk_areas.copy(),
                geometry=gpd.points_from_xy(
                    pd.to_numeric(safety_risk_areas["경도"], errors="coerce"),
                    pd.to_numeric(safety_risk_areas["위도"], errors="coerce"),
                ),
                crs="EPSG:4326",
            )
        risk_points = risk_points.to_crs(boundaries.crs)
        risk_points = gpd.sjoin(
            risk_points,
            boundary_lookup,
            how="left",
            predicate="within",
        )
        mapped_risks = risk_points[risk_points["adm_cd"].notna()].copy()
        mapped_safety_risk_count = len(mapped_risks)
        min_x, min_y, max_x, max_y = bounds
        width = max_x - min_x
        height = max_y - min_y
        for row in mapped_risks.itertuples(index=False):
            cx = (row.geometry.x - min_x) / width * 900
            cy = (max_y - row.geometry.y) / height * 900
            title = escape(f"{row.사고유형}: {row.상세위치} · 출동 {int(row.출동횟수)}회")
            safety_risk_markers.append(
                f'<rect class="safety-risk-area" x="{cx - 3.8:.2f}" y="{cy - 3.8:.2f}" '
                f'width="7.6" height="7.6" transform="rotate(45 {cx:.2f} {cy:.2f})" '
                f'data-safety-risk-code="{row.adm_cd}"><title>{title}</title></rect>'
            )

    def point_markers(
        source: pd.DataFrame | gpd.GeoDataFrame | None,
        css_class: str,
        title_columns: tuple[str, ...],
    ) -> tuple[list[str], int]:
        if source is None or source.empty:
            return [], 0
        if isinstance(source, gpd.GeoDataFrame):
            points = source.copy()
            if points.crs is None:
                raise ValueError(f"{css_class} geometry requires a declared CRS")
        else:
            points = gpd.GeoDataFrame(
                source.copy(),
                geometry=gpd.points_from_xy(
                    pd.to_numeric(source["longitude"], errors="coerce"),
                    pd.to_numeric(source["latitude"], errors="coerce"),
                ),
                crs="EPSG:4326",
            )
        points = points[points.geometry.notna() & ~points.geometry.is_empty].to_crs(boundaries.crs)
        points = gpd.sjoin(points, boundary_lookup, how="left", predicate="within")
        points = points[points["adm_cd"].notna()].copy()
        min_x, min_y, max_x, max_y = bounds
        width, height = max_x - min_x, max_y - min_y
        markers = []
        for row in points.itertuples(index=False):
            cx = (row.geometry.x - min_x) / width * 900
            cy = (max_y - row.geometry.y) / height * 900
            details = " · ".join(
                str(getattr(row, column))
                for column in title_columns
                if hasattr(row, column) and pd.notna(getattr(row, column))
            )
            markers.append(
                f'<circle class="{css_class}" cx="{cx:.2f}" cy="{cy:.2f}" r="2.8" '
                f'data-reference-code="{row.adm_cd}"><title>{escape(details)}</title></circle>'
            )
        return markers, len(points)

    aed_markers, mapped_aed_count = point_markers(aed_points, "aed-point", ("org", "addrs"))
    park_markers, mapped_park_count = point_markers(
        park_points, "park-point", ("parkNm", "parkSe", "parkAr")
    )
    categories = policy_catalog["category"].tolist()
    if set(category_assessments["category"]) != set(categories):
        raise ValueError("Assessment and policy categories must match")
    required_policy_columns = {
        "problem_signal_ko",
        "priority_target_ko",
        "implementation_steps_ko",
        "policy_case_ko",
        "policy_case_source_url",
        "case_application_note_ko",
    }
    missing_policy_columns = required_policy_columns - set(policy_catalog.columns)
    if missing_policy_columns:
        raise ValueError(f"Policy catalog is missing columns: {sorted(missing_policy_columns)}")

    indicator_payload: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for row in indicator_scores.itertuples(index=False):
        estimate_used = str(row.estimate_used).strip().lower() in {"true", "1"}
        item = {
            "label": row.indicator_label,
            "raw": round(float(row.raw_or_derived_value), 2),
            "percentile": round(float(row.deprivation_percentile_0_100), 1),
            "weight": float(row.within_category_weight),
            "evidence": row.evidence_type,
            "value_status": row.value_status_ko,
            "estimate_used": estimate_used,
            "estimation_method": row.estimation_method_ko,
            "estimation_reason": row.estimation_reason,
            "confidence": confidence_label(row.confidence_level),
            "quality": row.quality_note,
            "triggered": bool(row.indicator_policy_triggered),
        }
        indicator_payload.setdefault(str(row.admin_dong_code), {}).setdefault(
            str(row.category), []
        ).append(item)
    assessment_payload: dict[str, dict[str, dict[str, Any]]] = {}
    for row in category_assessments.itertuples(index=False):
        assessment_payload.setdefault(str(row.admin_dong_code), {})[str(row.category)] = {
            "label": row.category_label,
            "major_category": row.major_category,
            "major_weight": float(row.major_category_weight),
            "score": round(float(row.category_score_0_100), 1),
            "confidence": confidence_label(row.category_confidence),
            "status": row.policy_review_status,
            "triggers": (
                str(row.triggered_indicators)
                if pd.notna(row.triggered_indicators) and str(row.triggered_indicators)
                else "없음"
            ),
        }
    major_payload: dict[str, dict[str, dict[str, Any]]] = {}
    for row in major_category_assessments.itertuples(index=False):
        major_payload.setdefault(str(row.admin_dong_code), {})[str(row.major_category)] = {
            "score": round(float(row.major_category_score_0_100), 1),
            "confidence": confidence_label(row.major_category_confidence),
            "status": row.policy_review_status,
            "triggered_children": (
                str(row.triggered_child_categories)
                if pd.notna(row.triggered_child_categories) and str(row.triggered_child_categories)
                else "없음"
            ),
        }
    policy_payload = {
        str(row.category): {
            "title": row.policy_title_ko,
            "lead": row.lead_implementer,
            "signal": row.problem_signal_ko,
            "target": row.priority_target_ko,
            "steps": row.implementation_steps_ko,
            "example": row.policy_example,
            "monitor": row.monitoring_indicator,
            "case": row.policy_case_ko,
            "case_url": row.policy_case_source_url,
            "case_note": row.case_application_note_ko,
            "limit": row.evidence_limit,
        }
        for row in policy_catalog.itertuples(index=False)
    }
    reference_payload: dict[str, dict[str, list[dict[str, Any]]]] = {}
    reference_specs = (
        (
            "healthcare_supply",
            "aed_count_current_unverified_per_10000_population",
            "인구 1만 명당 AED",
            1.0,
            "대/1만 명",
            "2026-08-12 조회 현재 목록이며 2025 점수에는 반영하지 않음",
        ),
        (
            "air_exposure",
            "annual_pm10_ug_m3_idw_2025",
            "2025 연평균 PM10 추정",
            1.0,
            "㎍/㎥",
            "32개 측정소 IDW 보간 참고값",
        ),
        (
            "air_exposure",
            "annual_no2_ppm_idw_2025",
            "2025 연평균 NO₂ 추정",
            1.0,
            "ppm",
            "32개 측정소 IDW 보간 참고값",
        ),
        (
            "air_exposure",
            "annual_o3_ppm_idw_2025",
            "2025 연평균 O₃ 추정",
            1.0,
            "ppm",
            "32개 측정소 IDW 보간 참고값",
        ),
        (
            "air_exposure",
            "air_idw_station_count",
            "보간에 사용한 대기측정소 수",
            1.0,
            "곳",
            "측정망 밀도를 보여 주는 불확실성 정보이며 취약점수가 아님",
        ),
        (
            "air_exposure",
            "nearest_air_station_distance_m",
            "최근접 대기측정소 거리",
            1.0,
            "m",
            "거리가 멀수록 공간보간 불확실성이 커질 수 있으며 취약점수가 아님",
        ),
        (
            "education_access_supply",
            "core_school_students_within_2000m_2025",
            "중심점 2km 내 학교 재학생",
            1.0,
            "명",
            "학교알리미 2025 재학생 합계이며 해당 동 거주 학령인구를 뜻하지 않음",
        ),
        (
            "education_access_supply",
            "core_school_teachers_within_2000m_2025",
            "중심점 2km 내 현원 교원",
            1.0,
            "명",
            "학교알리미 2025 현원 교원 합계이며 반경 중첩으로 인접 동과 중복될 수 있음",
        ),
        (
            "education_access_supply",
            "students_per_teacher_within_2000m_2025",
            "주변 학교 학생·교원 비율",
            1.0,
            "명/교원 1명",
            "2km 내 학교 재학생÷현원 교원 참고값이며 학급당 학생 수와 다름",
        ),
        (
            "education_access_supply",
            "core_school_teachers_per_1000_under_20_living_population_2025_context",
            "20대 미만 생활인구 1천명당 주변 교원",
            1.0,
            "명/1천명",
            "통신 생활인구 수요 대비 2km 교원 공급 참고값이며 거주 학령인구가 아님",
        ),
        (
            "healthcare_supply",
            "healthcare_facilities_per_1000_senior_living_population_2025_context",
            "고령 생활인구 1천명당 의료시설",
            1.0,
            "곳/1천명",
            "동 내부 병원·의원·약국을 60대 이상 생활인구로 나눈 점수 제외 참고값",
        ),
        (
            "healthcare_supply",
            "boundary_adjusted_healthcare_access_2000m_2025_context",
            "경계보정 의료시설 접근량",
            1.0,
            "가중 곳",
            "동 내부는 1, 경계 밖 2km 이내는 거리감쇠한 직선거리 접근 참고값",
        ),
        (
            "transit_access",
            "reachable_multi_leg_trip_share_pct_2025_current_proxy",
            "연결 노선의 2·3통행 비율",
            1.0,
            "%",
            "2025 노선 이용구성과 현재 노선망의 결합값이며 환승 불편을 직접 뜻하지 않음",
        ),
        (
            "transit_access",
            "reachable_youth_child_trip_share_pct_2025_current_proxy",
            "연결 노선의 청소년·어린이 통행 비율",
            1.0,
            "%",
            "2025 노선 이용구성 기반 정책대상 참고값이며 동 거주자의 이용률이 아님",
        ),
        (
            "transit_access",
            "bus_boarding_alighting_2023_validation",
            "2023 매칭 정류장 승하차",
            1.0,
            "건",
            "현재 노선·정류장명으로 재매칭한 과거 수요 검증값이며 2025 점수에서 제외",
        ),
        (
            "transit_access",
            "peak_bus_demand_share_pct_2023_validation",
            "2023 출퇴근시간 승하차 비율",
            1.0,
            "%",
            "07~09시·17~19시 30분 구간의 과거 수요 검증값",
        ),
        (
            "transit_access",
            "late_bus_demand_share_pct_2023_validation",
            "2023 심야 승하차 비율",
            1.0,
            "%",
            "22~04시 30분 구간의 과거 수요 검증값",
        ),
        (
            "transit_access",
            "bus_service_opportunities_per_1000_total_living_population_context",
            "생활인구 1천명당 버스 서비스 기회",
            1.0,
            "회/1천명",
            "현재 배차계획과 2025 생활인구를 결합한 혼합시점 공급 참고값",
        ),
        (
            "transit_access",
            "bus_service_opportunities_per_1000_senior_living_population_context",
            "고령 생활인구 1천명당 버스 서비스 기회",
            1.0,
            "회/1천명",
            "현재 배차계획을 60대 이상 생활인구로 나눈 정책대상 진단값",
        ),
        (
            "transit_access",
            "late_bus_service_share_pct_current_proxy",
            "현재 심야 서비스 기회 비율",
            1.0,
            "%",
            "22~04시 운행시간과 평시 배차로 근사했으며 실제 심야 운행횟수가 아님",
        ),
        (
            "transit_access",
            "late_bus_demand_service_mismatch_percentile_2023_current_validation",
            "심야 수요·공급 불일치 백분위",
            1.0,
            "점",
            "2023 심야수요 상위와 현재 심야서비스 하위를 결합한 혼합시점 검증값",
        ),
        (
            "transit_access",
            "boundary_adjusted_bus_stop_access_1000m_2025_context",
            "경계보정 버스정류장 접근량",
            1.0,
            "가중 곳",
            "동 내부는 1, 경계 밖 1km 이내는 거리감쇠한 직선거리 접근 참고값",
        ),
        (
            "local_employment_opportunity",
            "avg_daily_residential_living_population_2025",
            "일평균 거주 생활인구",
            1.0,
            "명/일",
            "생활활동 규모 참고값이며 고용기회 점수에는 반영하지 않음",
        ),
        (
            "local_employment_opportunity",
            "avg_daily_workplace_living_population_2025",
            "일평균 직장 생활인구",
            1.0,
            "명/일",
            "생활활동 규모 참고값이며 고용기회 점수에는 반영하지 않음",
        ),
        (
            "local_employment_opportunity",
            "avg_daily_visitor_living_population_2025",
            "일평균 방문 생활인구",
            1.0,
            "명/일",
            "생활활동 규모 참고값이며 고용기회 점수에는 반영하지 않음",
        ),
        (
            "local_employment_opportunity",
            "senior_living_population_share_pct_2025",
            "60대 이상 생활인구 비율",
            1.0,
            "%",
            "거주·직장·방문 생활인구를 합친 서비스 수요 구성비이며 취약점수가 아님",
        ),
        (
            "local_employment_opportunity",
            "under_20_living_population_share_pct_2025",
            "20대 미만 생활인구 비율",
            1.0,
            "%",
            "거주·직장·방문 생활인구를 합친 교육·교통 수요 참고값",
        ),
        (
            "local_employment_opportunity",
            "under_30_living_population_share_pct_2025",
            "30대 미만 생활인구 비율",
            1.0,
            "%",
            "20대 미만·20대 생활인구 구성비이며 주민등록 연령구조가 아님",
        ),
        (
            "local_employment_opportunity",
            "daytime_to_residential_living_population_ratio_2025",
            "직장·방문/거주 생활인구 비",
            1.0,
            "배",
            "주간 서비스 압력 참고값이며 주민 고용률이나 소득을 뜻하지 않음",
        ),
        (
            "local_employment_opportunity",
            "consumer_sales_avg_daily_amount_2025",
            "일평균 소비매출",
            1_000_000.0,
            "백만원/일",
            "점포 소재지 소비활동이며 주민소득이나 고용기회 점수에는 반영하지 않음",
        ),
        (
            "local_employment_opportunity",
            "consumer_sales_avg_daily_transactions_2025",
            "일평균 소비건수",
            1.0,
            "건/일",
            "점포 소재지 소비활동이며 주민소득이나 고용기회 점수에는 반영하지 않음",
        ),
        (
            "local_employment_opportunity",
            "consumer_sales_under_30_transaction_share_pct_2025",
            "30대 미만 소비건수 비율",
            1.0,
            "%",
            "가맹점 소재지의 20대 미만·20대 결제 구성으로 주민 연령구조가 아님",
        ),
        (
            "local_employment_opportunity",
            "consumer_sales_senior_transaction_share_pct_2025",
            "60대 이상 소비건수 비율",
            1.0,
            "%",
            "가맹점 소재지 결제 구성으로 고령 주민의 소비수준이나 소득을 뜻하지 않음",
        ),
        (
            "local_employment_opportunity",
            "consumer_sales_late_night_transaction_share_pct_2025",
            "22~05시 소비건수 비율",
            1.0,
            "%",
            "22~05시 가맹점 결제 구성으로 야간 서비스 수요 참고값이며 취약점수가 아님",
        ),
        (
            "local_employment_opportunity",
            "consumer_sales_daytime_transaction_share_pct_2025",
            "09~17시 소비건수 비율",
            1.0,
            "%",
            "09~17시 가맹점 결제 구성으로 주간 상권활동 참고값이며 취약점수가 아님",
        ),
        (
            "local_employment_opportunity",
            "senior_consumer_minus_living_share_pp_2025_context",
            "고령 소비－생활인구 구성 차이",
            1.0,
            "%p",
            "60대 이상 소비건수 비율에서 생활인구 비율을 뺀 교차검증값",
        ),
        (
            "local_employment_opportunity",
            "under_30_consumer_minus_living_share_pp_2025_context",
            "청년 소비－생활인구 구성 차이",
            1.0,
            "%p",
            "30대 미만 소비건수 비율에서 생활인구 비율을 뺀 교차검증값",
        ),
        (
            "local_employment_opportunity",
            "living_consumer_age_composition_divergence_pp_2025_context",
            "생활·소비 연령구성 평균 차이",
            1.0,
            "%p",
            "고령·청년 구성 차이의 절댓값 평균이며 소득이나 소비취약도를 뜻하지 않음",
        ),
        (
            "heat_response",
            "heat_shelters_per_1000_senior_living_population_2025_context",
            "고령 생활인구 1천명당 무더위쉼터",
            1.0,
            "곳/1천명",
            "60대 이상 생활인구 수요 대비 동 내부 쉼터 공급 참고값",
        ),
        (
            "heat_response",
            "boundary_adjusted_heat_shelter_access_1000m_2025_context",
            "경계보정 무더위쉼터 접근량",
            1.0,
            "가중 곳",
            "동 내부는 1, 경계 밖 1km 이내는 거리감쇠한 직선거리 접근 참고값",
        ),
        (
            "major_environment",
            "park_count_current",
            "행정동 내 도시공원 수",
            1.0,
            "곳",
            "2026-08-14 조회 공원목록 참고값이며 2025 환경점수에는 반영하지 않음",
        ),
        (
            "major_environment",
            "nearest_park_distance_m_current",
            "행정동 중심점 최근접 도시공원 거리",
            1.0,
            "m",
            "직선거리 참고값이며 실제 보행경로·공원 입구·이용 가능성을 뜻하지 않음",
        ),
        (
            "major_safety",
            "district_accident_count_2025",
            "소속 구·군 교통사고 발생",
            1.0,
            "건",
            "도로교통공단 2025 구·군 전체사고 통계이며 행정동 점수에는 반영하지 않음",
        ),
        (
            "major_safety",
            "district_accidents_per_100k_2025",
            "소속 구·군 인구 10만 명당 교통사고",
            1.0,
            "건/10만 명",
            "구·군 비교용 통계이며 행정동 단위 위험도로 해석할 수 없음",
        ),
    )
    if reference_context is not None:
        if (
            len(reference_context) != EXPECTED_DONG_COUNT
            or reference_context["admin_dong_code"].astype(str).duplicated().any()
        ):
            raise ValueError("Reference context requires 206 unique administrative-dong rows")
        missing_reference = sorted(
            {column for _, column, *_ in reference_specs} - set(reference_context.columns)
        )
        if missing_reference:
            raise ValueError(f"Reference context is missing columns: {missing_reference}")
        for category_key, column, label, divisor, unit, note in reference_specs:
            values = pd.to_numeric(reference_context[column], errors="raise").astype(float)
            percentiles = values.rank(method="average", pct=True) * 100.0
            for code, value, percentile in zip(
                reference_context["admin_dong_code"].astype(str),
                values,
                percentiles,
                strict=True,
            ):
                if pd.isna(value):
                    continue
                reference_payload.setdefault(code, {}).setdefault(category_key, []).append(
                    {
                        "label": label,
                        "value": round(float(value) / divisor, 2),
                        "unit": unit,
                        "percentile": round(float(percentile), 1),
                        "note": note,
                    }
                )
    composition_payload: dict[str, dict[str, list[dict[str, Any]]]] = {}
    if reference_context is not None:
        living_columns = {
            "거주": "avg_daily_residential_living_population_2025",
            "직장": "avg_daily_workplace_living_population_2025",
            "방문": "avg_daily_visitor_living_population_2025",
        }
        for row in reference_context.itertuples(index=False):
            values = {
                label: float(getattr(row, column)) for label, column in living_columns.items()
            }
            total = sum(values.values())
            composition_payload.setdefault(str(row.admin_dong_code), {})["living_population"] = [
                {"label": label, "share": round(value / total * 100, 1) if total else 0}
                for label, value in values.items()
            ]
    if consumer_sales_by_category is not None:
        required_sales_columns = {
            "admin_dong_code",
            "industry_category",
            "consumer_sales_avg_daily_amount_2025",
        }
        missing_sales = required_sales_columns - set(consumer_sales_by_category.columns)
        if missing_sales:
            raise ValueError(f"Sales composition is missing columns: {sorted(missing_sales)}")
        sales = consumer_sales_by_category.copy()
        sales["admin_dong_code"] = sales["admin_dong_code"].astype(str)
        sales["amount"] = pd.to_numeric(
            sales["consumer_sales_avg_daily_amount_2025"], errors="raise"
        )
        for code, rows in sales.groupby("admin_dong_code", sort=False):
            rows = rows.sort_values("amount", ascending=False)
            total = float(rows["amount"].sum())
            composition_payload.setdefault(str(code), {})["sales"] = [
                {
                    "label": str(row.industry_category),
                    "share": round(float(row.amount) / total * 100, 1) if total else 0,
                }
                for row in rows.head(5).itertuples(index=False)
            ]
    trend_payload: list[dict[str, int]] = []
    if traffic_citywide_trend is not None:
        trend = traffic_citywide_trend.tail(5).copy()
        for column in trend.columns:
            trend[column] = pd.to_numeric(
                trend[column].astype(str).str.replace(",", "", regex=False), errors="raise"
            )
        trend_payload = [
            {
                "year": int(row[0]),
                "accidents": int(row[1]),
                "deaths": int(row[2]),
                "injuries": int(row[3]),
            }
            for row in trend.itertuples(index=False, name=None)
        ]
    paths: list[str] = []
    for row in map_data.itertuples(index=False):
        attributes = {
            "code": row.admin_dong_code,
            "name": f"{row.sigungu_name} {row.admin_dong_name}",
            "rank": f"기존 B-IMD {int(row.b_imd_rank)}위 · {row.b_imd_score_0_100:.1f}",
        }
        encoded = " ".join(
            f'data-{key}="{escape(str(value), quote=True)}"' for key, value in attributes.items()
        )
        paths.append(
            f'<path d="{_geometry_svg_path(row.geometry, bounds)}" fill="#f4a261" {encoded}/>'
        )
    major_rows = major_category_assessments[
        ["major_category", "major_category_label"]
    ].drop_duplicates()
    category_to_major = (
        category_assessments[["category", "major_category"]]
        .drop_duplicates()
        .set_index("category")["major_category"]
        .to_dict()
    )
    major_order = list(dict.fromkeys(category_to_major[category] for category in categories))
    major_rows = major_rows.assign(
        _display_order=major_rows["major_category"].map(
            {value: index for index, value in enumerate(major_order)}
        )
    ).sort_values("_display_order")
    labels = dict(
        major_rows[["major_category", "major_category_label"]].itertuples(
            index=False,
            name=None,
        )
    )
    major_categories = major_rows["major_category"].tolist()
    child_rows = category_assessments[
        [
            "major_category",
            "category",
            "category_label",
            "major_category_weight",
        ]
    ].drop_duplicates()
    child_rows = child_rows.assign(
        _display_order=child_rows["category"].map(
            {value: index for index, value in enumerate(categories)}
        )
    ).sort_values(["major_category", "_display_order"])
    children = (
        child_rows.groupby("major_category", observed=True)
        .apply(
            lambda rows: [
                {
                    "category": row.category,
                    "label": row.category_label,
                    "weight": float(row.major_category_weight),
                }
                for row in rows.itertuples(index=False)
            ],
            include_groups=False,
        )
        .to_dict()
    )
    category_labels = dict(
        child_rows[["category", "category_label"]].itertuples(index=False, name=None)
    )
    indicator_key = "indicator" if "indicator" in indicator_scores else "indicator_label"
    indicator_count = int(indicator_scores[indicator_key].nunique())
    tree_branches: list[str] = []
    for row in major_rows.itertuples(index=False):
        child_nodes = "".join(
            (
                f'<button class="tree-child" data-major-category="{row.major_category}" '
                f'data-category="{child["category"]}" role="treeitem">'
                f'<span class="tree-line">└</span><span>{escape(child["label"])}</span>'
                f"<small>{child['weight']:.0%}</small></button>"
            )
            for child in children[row.major_category]
        )
        tree_branches.append(
            f'<details class="tree-branch" data-branch="{row.major_category}" open>'
            f'<summary class="tree-major" data-major-category="{row.major_category}" '
            f'role="treeitem"><span>{escape(row.major_category_label)}</span>'
            f"<small>종합분포</small></summary>"
            f'<div class="tree-children" role="group">{child_nodes}</div></details>'
        )
    category_tree = "".join(tree_branches)
    dashboard_outputs = write_dashboard_files(
        output_path,
        replacements={
            "INDICATOR_COUNT": str(indicator_count),
            "CATEGORY_COUNT": str(len(categories)),
            "MAJOR_COUNT": str(len(major_categories)),
            "CATEGORY_TREE": category_tree,
            "HOTSPOT_COUNT": str(len(hotspot_circles)),
            "SAFETY_RISK_COUNT": str(len(safety_risk_markers)),
            "AED_COUNT": str(len(aed_markers)),
            "PARK_COUNT": str(len(park_markers)),
            "DONG_PATHS": "".join(paths),
            "HOTSPOT_MARKERS": "".join(hotspot_circles),
            "SAFETY_RISK_MARKERS": "".join(safety_risk_markers),
            "AED_MARKERS": "".join(aed_markers),
            "PARK_MARKERS": "".join(park_markers),
        },
        payloads={
            "indicators": indicator_payload,
            "assessments": assessment_payload,
            "majorAssessments": major_payload,
            "children": children,
            "policies": policy_payload,
            "labels": labels,
            "categoryLabels": category_labels,
            "accidentSummary": accident_summary,
            "referenceContext": reference_payload,
            "referenceCompositions": composition_payload,
            "trafficTrend": trend_payload,
        },
        major_category=major_categories[0],
    )
    return {
        "traffic_hotspot_count": len(traffic_hotspots) if traffic_hotspots is not None else 0,
        "mapped_traffic_hotspot_count": mapped_hotspot_count,
        "safety_risk_area_count": len(safety_risk_areas) if safety_risk_areas is not None else 0,
        "mapped_safety_risk_area_count": mapped_safety_risk_count,
        "aed_point_count": len(aed_points) if aed_points is not None else 0,
        "mapped_aed_point_count": mapped_aed_count,
        "park_point_count": len(park_points) if park_points is not None else 0,
        "mapped_park_point_count": mapped_park_count,
        "dashboard_outputs": dashboard_outputs,
    }


def render(
    composite: pd.DataFrame,
    boundaries: gpd.GeoDataFrame,
    priority: pd.DataFrame,
    overlay: pd.DataFrame,
    policy_matrix: pd.DataFrame,
    svg_output: Path,
    pdf_output: Path,
    png_output: Path,
) -> dict[str, Any]:
    """Render one deterministic A4 page to SVG and PDF."""
    for frame in (composite, priority, overlay):
        frame["admin_dong_code"] = frame["admin_dong_code"].astype(str)
    boundaries = boundaries.copy()
    boundaries["adm_cd"] = boundaries["adm_cd"].astype(str)
    _validate(composite, boundaries, priority, overlay, policy_matrix)

    family = _font_family()
    mpl.rcParams.update(
        {
            "font.family": family,
            "axes.unicode_minus": False,
            "svg.hashsalt": "busan-imd-2025",
        }
    )
    page = boundaries.merge(
        composite[
            [
                "admin_dong_code",
                "sigungu_name",
                "admin_dong_name",
                "b_imd_score_0_100",
                "b_imd_rank",
                "b_imd_decile",
            ]
        ],
        left_on="adm_cd",
        right_on="admin_dong_code",
        validate="one_to_one",
    ).merge(
        overlay[["admin_dong_code", "double_burden"]],
        on="admin_dong_code",
        validate="one_to_one",
    )
    priority_codes = set(priority["admin_dong_code"])
    priority_map = page[page["admin_dong_code"].isin(priority_codes)]
    burden_map = page[page["double_burden"].astype(str).str.lower() == "true"]
    profiles = build_action_profiles(composite)
    ranked = (
        priority.sort_values("b_imd_rank", kind="stable")
        .head(10)
        .merge(
            profiles[
                [
                    "admin_dong_code",
                    "primary_vulnerability_ko",
                    "improvement_direction",
                ]
            ],
            on="admin_dong_code",
            validate="one_to_one",
        )
    )

    fig = plt.figure(figsize=(8.27, 11.69), facecolor=PALETTE["paper"])
    grid = fig.add_gridspec(
        12,
        12,
        left=0.055,
        right=0.955,
        top=0.865,
        bottom=0.065,
        hspace=0.8,
        wspace=0.75,
    )
    fig.text(
        0.055,
        0.952,
        "행정동별 취약 원인에서 맞춤형 개선 방향까지",
        fontsize=22,
        fontweight="bold",
        color=PALETTE["ink"],
    )
    fig.text(
        0.055,
        0.918,
        "2025 부산형 다중박탈지수(B-IMD) 공개형 실험 분석 · 행정동 206개",
        fontsize=9.5,
        color=PALETTE["muted"],
    )
    metrics = (
        ("206", "분석 행정동"),
        ("21", "1분위 우선지역"),
        ("2", "탐색적 취약유형"),
        (str(len(burden_map)), "대기오염 이중부담"),
    )
    for index, (value, label) in enumerate(metrics):
        x = 0.055 + index * 0.225
        fig.text(x, 0.882, value, fontsize=16, fontweight="bold", color=PALETTE["accent"])
        fig.text(x + 0.055, 0.884, label, fontsize=8.3, color=PALETTE["ink"])

    ax_map = fig.add_subplot(grid[:7, :7])
    _panel(ax_map)
    page.plot(
        ax=ax_map,
        column="b_imd_score_0_100",
        cmap="YlOrRd",
        linewidth=0.13,
        edgecolor="#FFFFFF",
        vmin=0,
        vmax=100,
    )
    priority_map.boundary.plot(ax=ax_map, color=PALETTE["ink"], linewidth=0.75)
    if not burden_map.empty:
        centers = burden_map.geometry.centroid
        ax_map.scatter(
            centers.x,
            centers.y,
            s=28,
            facecolor=PALETTE["blue"],
            edgecolor="white",
            linewidth=0.7,
            zorder=4,
        )
    ax_map.set_axis_off()
    ax_map.set_title(
        "행정동별 B-IMD 점수",
        loc="left",
        fontsize=12,
        fontweight="bold",
        color=PALETTE["ink"],
        pad=10,
    )
    scale = mpl.cm.ScalarMappable(norm=mpl.colors.Normalize(0, 100), cmap="YlOrRd")
    colorbar = fig.colorbar(scale, ax=ax_map, orientation="horizontal", fraction=0.035, pad=0.015)
    colorbar.set_label("높을수록 부산 내 상대적 생활취약성이 큼", fontsize=7.5)
    colorbar.ax.tick_params(labelsize=7)
    ax_map.legend(
        handles=[
            Line2D([0], [0], color=PALETTE["ink"], lw=1.4, label="1분위 21개 동"),
            Line2D(
                [0],
                [0],
                marker="o",
                color="none",
                markerfacecolor=PALETTE["blue"],
                markeredgecolor="white",
                markersize=6,
                label=f"PM 이중부담 {len(burden_map)}개 동",
            ),
        ],
        loc="lower left",
        fontsize=7.2,
        frameon=False,
    )

    ax_rank = fig.add_subplot(grid[:7, 7:])
    _panel(ax_rank)
    ax_rank.set_xlim(0, 1)
    ax_rank.set_ylim(0, 1)
    ax_rank.set_xticks([])
    ax_rank.set_yticks([])
    ax_rank.text(
        0.06,
        0.94,
        "상위 10개: 주요 취약 → 개선 검토",
        fontsize=12,
        fontweight="bold",
        color=PALETTE["ink"],
        va="top",
    )
    burden_codes = set(burden_map["admin_dong_code"])
    for row_index, row in enumerate(ranked.itertuples(index=False), 1):
        y = 0.88 - (row_index - 1) * 0.078
        marker = "●" if row.admin_dong_code in burden_codes else ""
        ax_rank.text(0.06, y, f"{int(row.b_imd_rank):02d}", fontsize=8, color=PALETTE["muted"])
        ax_rank.text(
            0.16,
            y,
            f"{row.sigungu_name} {row.admin_dong_name}",
            fontsize=8.4,
            color=PALETTE["ink"],
        )
        ax_rank.text(
            0.16,
            y - 0.027,
            f"{row.primary_vulnerability_ko} → {row.improvement_direction}",
            fontsize=6.25,
            color=PALETTE["muted"],
        )
        ax_rank.text(
            0.84,
            y,
            f"{row.b_imd_score_0_100:.1f}",
            fontsize=8.4,
            ha="right",
            color=PALETTE["accent"],
            fontweight="bold",
        )
        ax_rank.text(0.90, y, marker, fontsize=8, color=PALETTE["blue"])
        ax_rank.plot([0.06, 0.94], [y - 0.025, y - 0.025], color=PALETTE["line"], lw=0.45)
    ax_rank.text(
        0.06,
        0.055,
        "● 대기오염 이중부담  ·  전체 206개 동은 탐색형 지도에서 조회",
        fontsize=7.3,
        color=PALETTE["muted"],
    )

    ax_policy = fig.add_subplot(grid[7:10, :])
    _panel(ax_policy)
    ax_policy.set_xlim(0, 1)
    ax_policy.set_ylim(0, 1)
    ax_policy.set_xticks([])
    ax_policy.set_yticks([])
    ax_policy.text(
        0.025,
        0.91,
        "취약 원인에서 지역별 개선 후보로",
        fontsize=12,
        fontweight="bold",
        color=PALETTE["ink"],
        va="top",
    )
    cards = _policy_cards(policy_matrix)
    for x, title, action, detail, color in cards:
        ax_policy.add_patch(
            mpl.patches.FancyBboxPatch(
                (x, 0.13),
                0.46,
                0.58,
                boxstyle="round,pad=0.012,rounding_size=0.015",
                facecolor="#F8FAF8",
                edgecolor=color,
                linewidth=1.2,
            )
        )
        ax_policy.text(x + 0.025, 0.61, title, fontsize=9.3, fontweight="bold", color=color)
        ax_policy.text(x + 0.025, 0.40, action, fontsize=8.3, color=PALETTE["ink"], wrap=True)
        ax_policy.text(x + 0.025, 0.22, detail, fontsize=7.4, color=PALETTE["muted"], wrap=True)

    ax_note = fig.add_subplot(grid[10:, :])
    _panel(ax_note)
    ax_note.set_xlim(0, 1)
    ax_note.set_ylim(0, 1)
    ax_note.set_xticks([])
    ax_note.set_yticks([])
    ax_note.text(
        0.025,
        0.78,
        "어떻게 읽을까",
        fontsize=10.5,
        fontweight="bold",
        color=PALETTE["ink"],
    )
    ax_note.text(
        0.025,
        0.49,
        "9개 공개 대리지표를 6개 영역으로 묶어 부산 안의 상대순위를 비교했습니다. "
        "가중치와 소득·고용 대리지표 포함 범위에 따라 순위가 달라질 수 있어 직접 행정자료 "
        "검증이 우선입니다. 낮은 취약점수는 특화산업의 증거가 아니며 "
        "지역자산 데이터를 결합해야 특화 방향을 판단할 수 있습니다.",
        fontsize=7.8,
        color=PALETTE["ink"],
        wrap=True,
    )
    ax_note.text(
        0.025,
        0.14,
        "주의  비공식·실험 지수 / 인과·개인 자격 판정 금지 / 정책은 현장 검증 후보 / "
        "PM 노출은 IDW 추정이며 항만·산단 배출원 귀속이 아님",
        fontsize=7.4,
        color=PALETTE["accent"],
        fontweight="bold",
    )
    fig.text(
        0.055,
        0.027,
        "자료 기준: 2025년(일부 2024 대리자료) · 기준지리: SGIS 2025 행정동 · "
        "재현 코드와 전체 한계: codingnanyong/busan-competition-2026",
        fontsize=6.7,
        color=PALETTE["muted"],
    )

    svg_output.parent.mkdir(parents=True, exist_ok=True)
    pdf_output.parent.mkdir(parents=True, exist_ok=True)
    png_output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(svg_output, format="svg", metadata={"Date": None})
    fixed_date = datetime(2025, 12, 31, tzinfo=UTC)
    fig.savefig(
        pdf_output,
        format="pdf",
        metadata={
            "Title": "2025 Busan Index of Multiple Deprivation infographic",
            "Author": "busan-competition-2026",
            "CreationDate": fixed_date,
            "ModDate": fixed_date,
        },
    )
    fig.savefig(png_output, format="png", dpi=180, metadata={"Software": "busan-imd"})
    plt.close(fig)
    return {
        "page_count": 1,
        "priority_area_count": len(priority),
        "double_burden_area_count": len(burden_map),
        "top_10_names": (ranked["sigungu_name"] + " " + ranked["admin_dong_name"]).tolist(),
        "policy_candidate_count": len(policy_matrix),
        "font_family": family,
    }
