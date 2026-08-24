"""Render the reproducible one-page 2025 B-IMD map and infographic draft."""

from __future__ import annotations

import argparse
import json
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

from busan_imd.composite_index import DEFAULT_OUTPUT as DEFAULT_COMPOSITE
from busan_imd.core.artifacts import sha256_file, write_json
from busan_imd.environmental_overlay import DEFAULT_OUTPUT as DEFAULT_OVERLAY
from busan_imd.policy_matrix import DEFAULT_OUTPUT as DEFAULT_POLICY_MATRIX
from busan_imd.priority_areas import DEFAULT_PRIORITY_OUTPUT

DEFAULT_BOUNDARIES = Path(
    "data/raw/sgis/admin_boundaries/2025/busan_admin_dong_boundaries_2025_valid.geojson"
)
DEFAULT_OUTPUT_DIR = Path("outputs/infographic")
DEFAULT_SVG_OUTPUT = DEFAULT_OUTPUT_DIR / "busan_imd_one_page_2025.svg"
DEFAULT_PDF_OUTPUT = DEFAULT_OUTPUT_DIR / "busan_imd_one_page_2025.pdf"
DEFAULT_PNG_OUTPUT = DEFAULT_OUTPUT_DIR / "busan_imd_one_page_2025.png"
DEFAULT_PROFILE_OUTPUT = DEFAULT_OUTPUT_DIR / "busan_admin_dong_action_profile_2025.csv"
DEFAULT_HTML_OUTPUT = DEFAULT_OUTPUT_DIR / "busan_admin_dong_action_map_2025.html"
DEFAULT_CATEGORY_ASSESSMENT = (
    DEFAULT_OUTPUT_DIR / "busan_admin_dong_category_assessment_2025.csv"
)
DEFAULT_MAJOR_CATEGORY_ASSESSMENT = (
    DEFAULT_OUTPUT_DIR / "busan_admin_dong_major_category_assessment_2025.csv"
)
DEFAULT_INDICATOR_SCORES = Path(
    "outputs/infographic/busan_admin_dong_category_indicator_scores_2025.csv"
)
DEFAULT_POLICY_CATALOG = Path("docs/data/CATEGORY_POLICY_CATALOG_2025.csv")
DEFAULT_REPORT = Path("docs/data/manifests/INFOGRAPHIC_REPORT_2025.json")
EXPECTED_DONG_COUNT = 206
EXPECTED_PRIORITY_COUNT = 21
PALETTE = {
    "ink": "#18323D",
    "muted": "#5D7078",
    "paper": "#F7F4ED",
    "panel": "#FFFFFF",
    "accent": "#D84A3A",
    "blue": "#087E8B",
    "gold": "#D99A25",
    "line": "#D7DED9",
}
DOMAIN_COLUMNS = {
    "education": ("education_score_0_100", "교육"),
    "employment": ("employment_score_0_100", "고용"),
    "health": ("health_score_0_100", "건강"),
    "housing_access": ("housing_access_score_0_100", "주거·접근성"),
    "income": ("income_score_0_100", "소득"),
    "living_environment": ("living_environment_score_0_100", "생활환경"),
}
DOMAIN_COLORS = {
    "education": "#D99A25",
    "employment": "#087E8B",
    "health": "#A44A7A",
    "housing_access": "#596FB7",
    "income": "#D84A3A",
    "living_environment": "#4F8A5B",
}
IMPROVEMENT_ACTIONS = {
    "education": "학습지원·학교 접근성 점검",
    "employment": "주민 고용자료 검증 후 일자리·훈련 연계",
    "health": "의료·건강관리 접근성 점검",
    "housing_access": "주거·교통·생활시설 접근 개선",
    "income": "복지급여 누락 점검·통합사례관리",
    "living_environment": "생활환경·안전·대기질 현장점검",
}
PRESERVATION_DIRECTIONS = {
    "education": "교육 기반 보전·연계 검토",
    "employment": "지역 일자리 기반 보전 검토",
    "health": "건강·의료 접근 기반 보전 검토",
    "housing_access": "주거·교통 접근 기반 보전 검토",
    "income": "경제 안정 기반 보전 검토",
    "living_environment": "생활환경 기반 보전 검토",
}
INDICATOR_PRESENTATION = {
    "basic_livelihood_recipients_per_1000_population_2025_inferred": (
        "추정 기초생활수급자",
        "명/1천명",
        "높을수록 취약",
    ),
    "workplace_workers_2024": ("사업장 종사자", "명", "낮을수록 취약"),
    "nearest_core_school_distance_m_2025": ("핵심학교 최근접 거리", "m", "높을수록 취약"),
    "hospital_count_2025_candidate_per_10000_population": (
        "병원 접근량",
        "개/1만명",
        "낮을수록 취약",
    ),
    "clinic_count_2025_candidate_per_10000_population": (
        "의원 접근량",
        "개/1만명",
        "낮을수록 취약",
    ),
    "old_house_share_30plus_2024_lower_bound_pct": (
        "30년 이상 노후주택 비율",
        "%",
        "높을수록 취약",
    ),
    "bus_stop_count_2025_per_10000_population": (
        "버스정류소 접근량",
        "개/1만명",
        "낮을수록 취약",
    ),
    "heat_shelter_count_2025_per_10000_population": (
        "무더위쉼터 접근량",
        "개/1만명",
        "낮을수록 취약",
    ),
    "annual_pm25_ug_m3_idw_2025": ("연평균 PM2.5", "㎍/㎥", "높을수록 취약"),
}


def build_action_profiles(composite: pd.DataFrame) -> pd.DataFrame:
    """Translate six-domain scores into transparent dong-level review directions."""
    required = {
        "admin_dong_code",
        "sigungu_name",
        "admin_dong_name",
        "b_imd_score_0_100",
        "b_imd_rank",
        "b_imd_decile",
        *(column for column, _ in DOMAIN_COLUMNS.values()),
    }
    missing = sorted(required - set(composite.columns))
    if missing:
        raise ValueError(f"Composite input is missing action-profile columns: {missing}")
    profiles = composite.copy()
    score_columns = [column for column, _ in DOMAIN_COLUMNS.values()]
    ordered = profiles[score_columns].apply(
        lambda row: row.sort_values(ascending=False, kind="stable").index.tolist(), axis=1
    )
    column_to_domain = {column: domain for domain, (column, _) in DOMAIN_COLUMNS.items()}
    profiles["primary_vulnerability_domain"] = ordered.map(
        lambda values: column_to_domain[values[0]]
    )
    profiles["secondary_vulnerability_domain"] = ordered.map(
        lambda values: column_to_domain[values[1]]
    )
    profiles["relative_low_deprivation_domain"] = ordered.map(
        lambda values: column_to_domain[values[-1]]
    )
    label = {domain: values[1] for domain, values in DOMAIN_COLUMNS.items()}
    profiles["primary_vulnerability_ko"] = profiles["primary_vulnerability_domain"].map(label)
    profiles["secondary_vulnerability_ko"] = profiles["secondary_vulnerability_domain"].map(label)
    profiles["relative_low_deprivation_ko"] = profiles["relative_low_deprivation_domain"].map(label)
    profiles["improvement_direction"] = profiles["primary_vulnerability_domain"].map(
        IMPROVEMENT_ACTIONS
    )
    profiles["preservation_direction"] = profiles["relative_low_deprivation_domain"].map(
        PRESERVATION_DIRECTIONS
    )
    profiles["review_level"] = pd.cut(
        profiles["b_imd_decile"],
        bins=[0, 1, 3, 7, 10],
        labels=["현장검증 우선", "집중 모니터링", "정기 모니터링", "상대 저취약"],
    ).astype(str)
    profiles["specialization_evidence_status"] = (
        "특화 확정 불가: 산업·상권·관광·생활SOC 자산 데이터 결합 필요"
    )
    columns = [
        "admin_dong_code",
        "sigungu_name",
        "admin_dong_name",
        "b_imd_score_0_100",
        "b_imd_rank",
        "b_imd_decile",
        *score_columns,
        "primary_vulnerability_domain",
        "primary_vulnerability_ko",
        "secondary_vulnerability_domain",
        "secondary_vulnerability_ko",
        "improvement_direction",
        "relative_low_deprivation_domain",
        "relative_low_deprivation_ko",
        "preservation_direction",
        "review_level",
        "specialization_evidence_status",
    ]
    return profiles[columns].sort_values("b_imd_rank", kind="stable").reset_index(drop=True)


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
    if set(composite["admin_dong_code"].astype(str)) != set(
        overlay["admin_dong_code"].astype(str)
    ):
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
    provided_priority = priority[comparison_columns].sort_values("admin_dong_code").reset_index(
        drop=True
    )
    canonical_priority = (
        composite[composite["admin_dong_code"].isin(priority["admin_dong_code"])]
        [comparison_columns]
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


def _write_action_map_legacy(
    profiles: pd.DataFrame,
    boundaries: gpd.GeoDataFrame,
    indicator_scores: pd.DataFrame,
    policy_catalog: pd.DataFrame,
    output_path: Path,
) -> None:
    """Write a category-first dashboard for scores, indicators, and policy examples."""
    map_data = boundaries.copy()
    map_data["adm_cd"] = map_data["adm_cd"].astype(str)
    map_data = map_data.merge(
        profiles,
        left_on="adm_cd",
        right_on="admin_dong_code",
        validate="one_to_one",
    )
    bounds = tuple(float(value) for value in map_data.total_bounds)
    required_indicators = set(INDICATOR_PRESENTATION)
    if set(indicator_scores["indicator"]) != required_indicators:
        raise ValueError("Indicator scores must contain the nine presentation indicators")
    domain_policies = policy_catalog[
        (policy_catalog["trigger_kind"] == "domain")
        & (policy_catalog["trigger_value"].isin(DOMAIN_COLUMNS))
    ]
    if set(domain_policies["trigger_value"]) != set(DOMAIN_COLUMNS):
        raise ValueError("Policy catalog must contain one policy for every scored domain")

    indicator_payload: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for row in indicator_scores.itertuples(index=False):
        label, unit, direction = INDICATOR_PRESENTATION[row.indicator]
        item = {
            "label": label,
            "unit": unit,
            "direction": direction,
            "raw": round(float(row.raw_value), 2),
            "percentile": round(float(row.deprivation_percentile_0_100), 1),
            "weight": float(row.within_domain_weight),
        }
        indicator_payload.setdefault(str(row.admin_dong_code), {}).setdefault(
            str(row.domain), []
        ).append(item)
    policy_payload = {
        str(row.trigger_value): {
            "title": row.policy_title_ko,
            "lead": row.lead_implementer,
            "effect": row.expected_effect,
            "monitor": row.monitoring_indicator,
            "limit": row.evidence_limit,
        }
        for row in domain_policies.itertuples(index=False)
    }
    paths: list[str] = []
    for row in map_data.itertuples(index=False):
        attributes = {
            "code": row.admin_dong_code,
            "name": f"{row.sigungu_name} {row.admin_dong_name}",
            "rank": f"{int(row.b_imd_rank)}위 / 206개 · B-IMD {row.b_imd_score_0_100:.1f}",
            "level": row.review_level,
        }
        for domain, (column, _) in DOMAIN_COLUMNS.items():
            attributes[domain.replace("_", "-")] = f"{getattr(row, column):.1f}"
        encoded = " ".join(
            f'data-{key}="{escape(str(value), quote=True)}"' for key, value in attributes.items()
        )
        paths.append(
            f'<path d="{_geometry_svg_path(row.geometry, bounds)}" '
            f'fill="#f4a261" {encoded}/>'
        )
    buttons = "".join(
        f'<button data-domain="{domain}">{label}</button>'
        for domain, (_, label) in DOMAIN_COLUMNS.items()
    )
    domain_labels = {domain: label for domain, (_, label) in DOMAIN_COLUMNS.items()}
    document = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>2025 부산 행정동 카테고리별 평가·정책 대시보드</title><style>
body{{margin:0;background:#f7f4ed;color:#18323d;font-family:Arial,'Noto Sans KR',sans-serif}}
main{{max-width:1180px;margin:auto;padding:24px}} h1{{margin:0 0 8px;font-size:28px}}
.note{{color:#5d7078;line-height:1.55}}
.layout{{display:grid;grid-template-columns:2fr 1fr;gap:20px}}
.map,.card{{background:white;border:1px solid #d7ded9;border-radius:12px;padding:16px}}
svg{{width:100%;height:72vh;min-height:560px}} path{{stroke:white;stroke-width:.55;cursor:pointer}}
path:hover,path:focus{{stroke:#18323d;stroke-width:2;filter:brightness(1.08)}}
.tabs{{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}}
button{{border:1px solid #d7ded9;background:white;border-radius:20px;padding:9px 16px}}
button{{cursor:pointer}}
button.active{{background:#18323d;color:white;border-color:#18323d}}
.scale{{height:10px;background:linear-gradient(90deg,#fff7bc,#fdae61,#d7301f);border-radius:6px}}
.scale-label{{display:flex;justify-content:space-between;font-size:12px;color:#5d7078}}
.card h2{{margin-top:0}} .card p{{line-height:1.55}} .action{{font-weight:700;color:#d84a3a}}
.scores{{font-size:13px;color:#5d7078}}
.metric{{margin:13px 0}} .metric-head{{display:flex;justify-content:space-between;font-size:13px}}
.bar{{height:8px;background:#edf0ed;border-radius:5px;overflow:hidden;margin-top:5px}}
.bar i{{display:block;height:100%;background:#d84a3a}}
.policy{{background:#f7f4ed;border-radius:9px;padding:12px;margin-top:18px}}
.warning{{border-top:1px solid #d7ded9;padding-top:12px;font-size:12px}}
@media(max-width:800px){{.layout{{grid-template-columns:1fr}} svg{{height:60vh;min-height:420px}}}}
</style></head><body><main><h1>부산 206개 행정동: 카테고리별 평가와 정책 예시</h1>
<p class="note">카테고리를 선택하면 해당 영역 점수의 공간분포가 나타납니다.
행정동을 선택해 구성 평가지표, 취약 백분위, 정책 예시와 성과지표를 확인하세요.</p>
<div class="tabs">{buttons}</div><div class="layout"><div class="map">
<h2 id="map-title"></h2><div class="scale"></div>
<div class="scale-label"><span>0 상대 저취약</span><span>100 상대 고취약</span></div>
<svg viewBox="0 0 900 900" role="img"
aria-label="부산 행정동별 카테고리 취약도 지도">{''.join(paths)}</svg>
</div><aside class="card" id="detail"><h2>지도의 행정동을 선택하세요</h2>
<p>평가지표와 정책 예시가 이곳에 표시됩니다.</p></aside></div>
<p class="note warning">높은 점수는 부산 내 상대적 취약성을 뜻합니다.
개선방향은 현장검증 후보이며 공식 지수·개인 자격·인과효과 판정이 아닙니다.
정책은 카테고리별 예시이며 현장 수요와 행정자료 검증 후 확정해야 합니다.</p>
</main><script>
const indicators={json.dumps(indicator_payload, ensure_ascii=False, separators=(',', ':'))};
const policies={json.dumps(policy_payload, ensure_ascii=False, separators=(',', ':'))};
const labels={json.dumps(domain_labels, ensure_ascii=False, separators=(',', ':'))};
const detail=document.getElementById('detail');let domain='education';let selected=null;
function color(score){{const hue=48-score*.45;return `hsl(${{hue}} 88% ${{62-score*.18}}%)`;}}
function scoreOf(path){{return Number(path.getAttribute('data-'+domain.replace('_','-')));}}
function selectDomain(next){{domain=next;document.querySelectorAll('button').forEach(b=>
 b.classList.toggle('active',b.dataset.domain===domain));
 document.getElementById('map-title').textContent=labels[domain]+' 취약도 분포';
 document.querySelectorAll('path').forEach(p=>p.style.fill=color(scoreOf(p)));
 if(selected)show({{target:selected}});
}}
function show(e){{const d=e.target.dataset;if(!d.name)return;selected=e.target;
 const score=scoreOf(e.target);const policy=policies[domain];
 const metrics=indicators[d.code][domain].map(m=>`<div class="metric">
 <div class="metric-head"><b>${{m.label}}</b><span>${{m.raw}} ${{m.unit}}</span></div>
 <div class="scores">취약 백분위 ${{m.percentile}} · 가중치 ${{m.weight}} · ${{m.direction}}</div>
 <div class="bar"><i style="width:${{m.percentile}}%"></i></div></div>`).join('');
 detail.innerHTML=`<h2>${{d.name}}</h2><p>${{d.rank}} · ${{d.level}}</p>
 <h3>${{labels[domain]}} 영역 점수 ${{score.toFixed(1)}}</h3>${{metrics}}
 <div class="policy"><b>정책 예시</b><h3>${{policy.title}}</h3><p>주관: ${{policy.lead}}</p>
 <p>기대효과: ${{policy.effect}}</p><p>성과지표: ${{policy.monitor}}</p>
 <p class="warning">${{policy.limit}}</p></div>`;
}}
document.querySelectorAll('path').forEach(p=>{{
 p.tabIndex=0;p.addEventListener('mouseenter',show);
 p.addEventListener('click',show);p.addEventListener('focus',show);
}});
document.querySelectorAll('button').forEach(b=>
 b.addEventListener('click',()=>selectDomain(b.dataset.domain)));
selectDomain(domain);
</script></body></html>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8", newline="\n")


def write_action_map(
    profiles: pd.DataFrame,
    boundaries: gpd.GeoDataFrame,
    category_assessments: pd.DataFrame,
    major_category_assessments: pd.DataFrame,
    indicator_scores: pd.DataFrame,
    policy_catalog: pd.DataFrame,
    output_path: Path,
) -> None:
    """Write a category dashboard with explicit evidence labels and policy gates."""
    map_data = boundaries.copy()
    map_data["adm_cd"] = map_data["adm_cd"].astype(str)
    map_data = map_data.merge(
        profiles,
        left_on="adm_cd",
        right_on="admin_dong_code",
        validate="one_to_one",
    )
    bounds = tuple(float(value) for value in map_data.total_bounds)
    categories = policy_catalog["category"].tolist()
    if set(category_assessments["category"]) != set(categories):
        raise ValueError("Assessment and policy categories must match")

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
            "confidence": row.confidence_level,
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
            "confidence": row.category_confidence,
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
            "confidence": row.major_category_confidence,
            "status": row.policy_review_status,
            "triggered_children": (
                str(row.triggered_child_categories)
                if pd.notna(row.triggered_child_categories)
                and str(row.triggered_child_categories)
                else "없음"
            ),
        }
    policy_payload = {
        str(row.category): {
            "title": row.policy_title_ko,
            "lead": row.lead_implementer,
            "example": row.policy_example,
            "monitor": row.monitoring_indicator,
            "limit": row.evidence_limit,
        }
        for row in policy_catalog.itertuples(index=False)
    }
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
            f'<path d="{_geometry_svg_path(row.geometry, bounds)}" '
            f'fill="#f4a261" {encoded}/>'
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
        child_rows
        .groupby("major_category", observed=True)
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
                f'<small>{child["weight"]:.0%}</small></button>'
            )
            for child in children[row.major_category]
        )
        tree_branches.append(
            f'<details class="tree-branch" data-branch="{row.major_category}" open>'
            f'<summary class="tree-major" data-major-category="{row.major_category}" '
            f'role="treeitem"><span>{escape(row.major_category_label)}</span>'
            f'<small>종합분포</small></summary>'
            f'<div class="tree-children" role="group">{child_nodes}</div></details>'
        )
    category_tree = "".join(tree_branches)
    document = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>2025 부산 행정동 생활여건 진단</title><style>
body{{margin:0;background:#f7f4ed;color:#18323d;font-family:Arial,'Noto Sans KR',sans-serif}}
main{{max-width:1540px;margin:auto;padding:24px}} h1{{margin:0 0 8px;font-size:28px}}
.note,.scores{{color:#5d7078;line-height:1.5}}
.layout{{display:grid;grid-template-columns:270px minmax(520px,2fr) minmax(330px,1fr);gap:16px}}
.map,.card{{background:white;border:1px solid #d7ded9;border-radius:12px;padding:16px}}
svg{{width:100%;height:70vh;min-height:540px}} path{{stroke:white;stroke-width:.55;cursor:pointer}}
path:hover,path:focus{{stroke:#18323d;stroke-width:2}}
.category-tree{{align-self:start;position:sticky;top:16px}}
.category-tree h2{{font-size:18px;margin:0 0 5px}}
.category-tree>.scores{{font-size:12px;margin-top:0}}
.tree-branch{{border-top:1px solid #d7ded9;padding:7px 0}}
.tree-branch:last-child{{border-bottom:1px solid #d7ded9}}
.tree-major{{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:10px 8px;
 cursor:pointer;border-radius:7px;font-weight:700}}
.tree-major::marker{{color:#087e8b}}
.tree-major small,.tree-child small{{margin-left:auto;color:#74858b;font-size:11px}}
.tree-major.active{{background:#18323d;color:white}}
.tree-major.active small{{color:#dce8e8}}
.tree-children{{border-left:2px solid #c9d8d8;margin-left:13px;padding:3px 0 6px 8px}}
.tree-child{{display:grid;grid-template-columns:18px 1fr auto;align-items:center;text-align:left;
 width:100%;gap:3px;border:0;background:transparent;border-radius:7px;padding:9px 7px;
 cursor:pointer;color:#29434c}}
.tree-child:hover{{background:#eef5f4}} .tree-child.active{{background:#087e8b;color:white}}
.tree-child.active small{{color:#dce8e8}} .tree-line{{color:#87a5a7}}
.guide{{display:grid;grid-template-columns:1.1fr .9fr;gap:14px;margin:16px 0 20px}}
.guide-card{{background:#eaf2f2;border-left:5px solid #087e8b;border-radius:10px;padding:16px}}
.guide-card h2{{font-size:17px;margin:0 0 12px}}
.steps{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:0;padding:0;list-style:none}}
.step{{background:white;border-radius:8px;padding:10px;font-size:13px;line-height:1.45}}
.step-number{{display:block;color:#087e8b;font-size:12px;font-weight:700;margin-bottom:4px}}
.aggregation-note{{background:#18323d;color:white;border-radius:7px;margin-top:10px;
 padding:10px 12px;font-size:13px;line-height:1.5}}
.aggregation-note strong{{display:block;color:#9ed8d3;margin-bottom:2px}}
.aggregation-caption{{font-size:12px;color:#5d7078;margin:7px 2px 0;line-height:1.45}}
.score-flow{{margin:0;padding:0;list-style:none}}
.score-level{{background:white;border-radius:7px;padding:8px 10px;font-size:13px;line-height:1.4}}
.score-level strong{{color:#087e8b}}
.score-level.level-2{{margin-left:22px}} .score-level.level-3{{margin-left:44px}}
.flow-arrow{{color:#087e8b;font-weight:700;line-height:18px;margin-left:12px}}
.flow-arrow.level-2{{margin-left:34px}}
.estimate-guide{{border-left:4px solid #d84a3a;background:#fff4ed;border-radius:0 7px 7px 0;
 margin:11px 0 0 44px;padding:9px 10px;font-size:12px;line-height:1.45}}
.scale{{height:10px;background:linear-gradient(90deg,#fff7bc,#fdae61,#d7301f)}}
.scale{{border-radius:6px}}
.scale-label,.metric-head{{display:flex;justify-content:space-between;font-size:12px}}
.metric{{margin:14px 0}} .bar{{height:8px;background:#edf0ed;border-radius:5px;overflow:hidden}}
.bar i{{display:block;height:100%;background:#d84a3a}}
.policy{{background:#f7f4ed;border-radius:9px;padding:12px;margin-top:18px}}
.subcategory{{border-top:2px solid #d7ded9;margin-top:20px;padding-top:12px}}
.subcategory h3{{margin-bottom:5px}}
.child-overview{{display:grid;grid-template-columns:1fr auto;gap:4px 12px;
 border-top:1px solid #d7ded9;padding:11px 0}}
.child-overview strong{{color:#d84a3a}} .child-overview .scores{{grid-column:1/-1;font-size:12px}}
.badge{{display:inline-block;border-radius:12px;padding:3px 8px;background:#edf0ed;font-size:12px}}
.estimate{{border-left:4px solid #d84a3a;background:#fff4ed;padding:9px;margin:8px 0}}
.observed{{border-left:4px solid #4f8a5b;background:#f2f8f2;padding:9px;margin:8px 0}}
.trigger{{color:#d84a3a;font-weight:700}}
.warning{{border-top:1px solid #d7ded9;padding-top:12px;font-size:12px}}
@media(max-width:1100px){{.layout{{grid-template-columns:240px 1fr}}.card#detail{{grid-column:1/-1}}
 .category-tree{{position:static}}.guide{{grid-template-columns:1fr}}}}
@media(max-width:720px){{.layout{{grid-template-columns:1fr}}.card#detail{{grid-column:auto}}
 .steps{{grid-template-columns:1fr 1fr}}svg{{height:55vh;min-height:400px}}}}
</style></head><body><main><h1>부산 행정동 생활여건 진단: 취약 요인과 정책 방향</h1>
<section class="guide" aria-label="대시보드 이용 방법과 점수 계산 구조">
<div class="guide-card"><h2>이 화면을 보는 방법</h2><ol class="steps">
<li class="step"><span class="step-number">1 · 항목 선택</span>
왼쪽 트리에서 큰 카테고리 또는 하위 카테고리를 선택합니다.</li>
<li class="step"><span class="step-number">2 · 분포 비교</span>
지도 색으로 부산 행정동의 상대적 취약도 분포를 비교합니다.</li>
<li class="step"><span class="step-number">3 · 지역 선택</span>
관심 행정동을 누르거나 마우스를 올려 해당 지역 결과를 엽니다.</li>
<li class="step"><span class="step-number">4 · 정책 해석</span>
오른쪽에서 평가지표, 추정 사유, 신뢰도와 조건부 정책 예시를 확인합니다.</li>
</ol><div class="aggregation-note"><strong>큰 카테고리 종합점수 산정</strong>
하위 카테고리별 취약도에 화면에 표시된 반영 비율을 적용한 뒤 합산합니다.
단순 평균이 아니며, 각 하위 항목이 종합점수에 미치는 비중을 함께 보여줍니다.</div>
<p class="aggregation-caption">점수가 높을수록 부산 안에서 상대적으로 더 취약하다는 뜻입니다.
절대적 결핍 판정이나 정책 확정 점수가 아닙니다.</p></div>
<div class="guide-card"><h2>점수는 이렇게 만들어집니다</h2><ol class="score-flow">
<li class="score-level level-1"><strong>1단계 · 평가지표 {indicator_count}개</strong><br>
교육시설 수, 의료 접근성, 대기오염 노출처럼 측정 가능한 근거를 정리합니다.</li>
<li class="flow-arrow" aria-hidden="true">↓ 지표별 방향과 가중치 반영</li>
<li class="score-level level-2"><strong>2단계 · 하위 카테고리 8개</strong><br>
관련 지표를 묶어 각 세부 영역의 취약도 점수를 계산합니다.</li>
<li class="flow-arrow level-2" aria-hidden="true">↓ 하위 점수의 가중합</li>
<li class="score-level level-3"><strong>3단계 · 큰 카테고리 3개</strong><br>
하위 카테고리 결과를 합산해 최종 종합분포를 만듭니다.</li>
</ol><div class="estimate-guide"><b>⚠ 추정값 사용 표시</b><br>
원자료가 행정동 단위로 없거나 기준연도·공간단위를 맞춰야 할 때만 추정·보정합니다.
사용한 방법과 이유는 선택한 행정동의 세부 평가지표 아래에 함께 표시합니다.</div></div>
</section>
<div class="layout"><nav class="card category-tree" aria-label="카테고리 선택 트리" role="tree">
<h2>분석 카테고리</h2><p class="scores">▸를 눌러 하위 항목을 접거나 펼치고, 항목명을 선택하세요.</p>
{category_tree}</nav><div class="map"><h2 id="map-title"></h2>
<div class="scale"></div><div class="scale-label">
<span>0 상대 저취약</span><span>100 상대 고취약</span></div>
<svg viewBox="0 0 900 900" aria-label="부산 행정동별 선택 카테고리 취약도 분포">
{''.join(paths)}</svg>
</div><aside class="card" id="detail"><h2>행정동을 선택하세요</h2>
<p>트리에서 큰 카테고리를 선택하면 종합 결과를, 하위 항목을 선택하면
세부 평가지표와 정책 예시를 표시합니다.</p></aside></div>
<p class="note warning">70점 이상은 정책 확정이 아니라 추가 행정자료·현장 검증 후보입니다.
기존 B-IMD 순위는 비교용이며 개선형 카테고리 점수와 혼합하지 않습니다.</p></main><script>
const indicators={json.dumps(indicator_payload, ensure_ascii=False, separators=(',', ':'))};
const assessments={json.dumps(assessment_payload, ensure_ascii=False, separators=(',', ':'))};
const majorAssessments={json.dumps(major_payload, ensure_ascii=False, separators=(',', ':'))};
const children={json.dumps(children, ensure_ascii=False, separators=(',', ':'))};
const policies={json.dumps(policy_payload, ensure_ascii=False, separators=(',', ':'))};
const labels={json.dumps(labels, ensure_ascii=False, separators=(',', ':'))};
const categoryLabels={json.dumps(category_labels, ensure_ascii=False, separators=(',', ':'))};
const detail=document.getElementById('detail');
let majorCategory='{major_categories[0]}';let category=null;let selected=null;
function color(score){{const hue=48-score*.45;return `hsl(${{hue}} 88% ${{62-score*.18}}%)`;}}
function scoreOf(path){{return category
 ?assessments[path.dataset.code][category].score
 :majorAssessments[path.dataset.code][majorCategory].score;}}
function selectNode(nextMajor,nextCategory=null){{majorCategory=nextMajor;category=nextCategory;
 document.querySelectorAll('.tree-major').forEach(node=>node.classList.toggle('active',
  category===null&&node.dataset.majorCategory===majorCategory));
 document.querySelectorAll('.tree-child').forEach(node=>node.classList.toggle('active',
  node.dataset.category===category));
 const selectedLabel=category?categoryLabels[category]:labels[majorCategory];
 const levelLabel=category?'하위 카테고리':'큰 카테고리 종합';
 document.getElementById('map-title').textContent=selectedLabel+' · '+levelLabel+' 취약도 분포';
 document.querySelectorAll('path').forEach(p=>p.style.fill=color(scoreOf(p)));
 if(selected)show({{target:selected}});
}}
function metricHtml(m){{const disclosure=m.estimate_used
  ?`<div class="estimate"><b>⚠ 추정값 사용</b><br>방법: ${{m.estimation_method}}<br>
  사용 사유: ${{m.estimation_reason}}</div>`
  :`<div class="observed"><b>추정값 미사용</b> · ${{m.value_status}}<br>
  산출 설명: ${{m.estimation_reason}}</div>`;return `<div class="metric">
 <div class="metric-head"><b>${{m.label}}</b><span>${{m.raw}}</span></div>
 <div class="scores">취약 백분위 ${{m.percentile}} · 가중치 ${{m.weight}} ·
 값 구분 ${{m.value_status}} · 신뢰 ${{m.confidence}}</div>${{disclosure}}
 <div class="bar"><i style="width:${{m.percentile}}%"></i></div>
 <div class="scores">원자료 한계: ${{m.quality}} ·
 기술 근거: ${{m.evidence}}</div></div>`;}}
function childHtml(code,child){{const a=assessments[code][child.category];
 const policy=policies[child.category];const metrics=indicators[code][child.category]
  .map(metricHtml).join('');const gate=a.status==='candidate_after_validation'
  ?'<span class="trigger">검증 후 정책검토 후보</span>'
  :'<span class="badge">모니터링</span>';return `<section class="subcategory">
 <h3>하위 카테고리 · ${{child.label}} ${{a.score.toFixed(1)}}</h3>
 <p class="scores">큰 카테고리 반영 가중치 ${{child.weight}} ·
 신뢰 ${{a.confidence}} · ${{gate}}</p><p class="scores">임계지표: ${{a.triggers}}</p>
 ${{metrics}}<div class="policy"><b>조건부 정책 예시</b><h3>${{policy.title}}</h3>
 <p>주관: ${{policy.lead}}</p><p>${{policy.example}}</p>
 <p>성과지표: ${{policy.monitor}}</p><p class="warning">${{policy.limit}}</p></div>
 </section>`;}}
function childOverviewHtml(code,child){{const a=assessments[code][child.category];return `
 <div class="child-overview"><span>${{child.label}} · 가중치 ${{child.weight}}</span>
 <strong>${{a.score.toFixed(1)}}</strong><span class="scores">신뢰 ${{a.confidence}} ·
 임계지표 ${{a.triggers}}</span></div>`;}}
function show(e){{const d=e.target.dataset;if(!d.name)return;selected=e.target;
 const major=majorAssessments[d.code][majorCategory];
 const gate=major.status==='candidate_after_validation'
  ?'<span class="trigger">검증 후 큰 카테고리 정책검토 후보</span>'
  :'<span class="badge">모니터링</span>';
 const heading=`<h2>${{d.name}}</h2><p class="scores">${{d.rank}}</p>`;
 if(category){{const child=children[majorCategory].find(c=>c.category===category);
  detail.innerHTML=heading+`<p class="scores">상위 · ${{labels[majorCategory]}}
  종합점수 ${{major.score.toFixed(1)}}</p>`+childHtml(d.code,child);return;}}
 const childOverview=children[majorCategory].map(c=>childOverviewHtml(d.code,c)).join('');
 detail.innerHTML=heading+`<h3>큰 카테고리 · ${{labels[majorCategory]}}
 ${{major.score.toFixed(1)}}</h3><p>종합 신뢰 <span class="badge">${{major.confidence}}</span>
 · ${{gate}}</p><p class="scores">70점 이상 하위 카테고리:
 ${{major.triggered_children}}</p><p class="scores">하위 점수 × 가중치의 합산 결과입니다.
 트리에서 하위 항목을 선택하면 평가지표와 정책 예시가 열립니다.</p>${{childOverview}}`;
}}
document.querySelectorAll('path').forEach(p=>{{p.tabIndex=0;p.addEventListener('mouseenter',show);
p.addEventListener('click',show);p.addEventListener('focus',show);}});
document.querySelectorAll('.tree-major').forEach(node=>node.addEventListener('click',()=>
 selectNode(node.dataset.majorCategory)));
document.querySelectorAll('.tree-child').forEach(node=>node.addEventListener('click',()=>{{
 node.closest('details').open=true;selectNode(node.dataset.majorCategory,node.dataset.category);
}}));
selectNode(majorCategory);
</script></body></html>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8", newline="\n")


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
        "top_10_names": (
            ranked["sigungu_name"] + " " + ranked["admin_dong_name"]
        ).tolist(),
        "policy_candidate_count": len(policy_matrix),
        "font_family": family,
    }


def run(
    composite_path: Path = DEFAULT_COMPOSITE,
    boundaries_path: Path = DEFAULT_BOUNDARIES,
    priority_path: Path = DEFAULT_PRIORITY_OUTPUT,
    overlay_path: Path = DEFAULT_OVERLAY,
    policy_matrix_path: Path = DEFAULT_POLICY_MATRIX,
    category_assessment_path: Path = DEFAULT_CATEGORY_ASSESSMENT,
    major_category_assessment_path: Path = DEFAULT_MAJOR_CATEGORY_ASSESSMENT,
    indicator_scores_path: Path = DEFAULT_INDICATOR_SCORES,
    policy_catalog_path: Path = DEFAULT_POLICY_CATALOG,
    svg_output: Path = DEFAULT_SVG_OUTPUT,
    pdf_output: Path = DEFAULT_PDF_OUTPUT,
    png_output: Path = DEFAULT_PNG_OUTPUT,
    profile_output: Path = DEFAULT_PROFILE_OUTPUT,
    html_output: Path = DEFAULT_HTML_OUTPUT,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    """Write the one-page draft, 206-dong action profiles, map, and manifest."""
    composite = pd.read_csv(composite_path, dtype={"admin_dong_code": str})
    boundaries = gpd.read_file(boundaries_path)
    priority = pd.read_csv(priority_path, dtype={"admin_dong_code": str})
    overlay = pd.read_csv(overlay_path, dtype={"admin_dong_code": str})
    policy_matrix = pd.read_csv(policy_matrix_path)
    category_assessments = pd.read_csv(
        category_assessment_path,
        dtype={"admin_dong_code": str},
    )
    major_category_assessments = pd.read_csv(
        major_category_assessment_path,
        dtype={"admin_dong_code": str},
    )
    indicator_scores = pd.read_csv(indicator_scores_path, dtype={"admin_dong_code": str})
    policy_catalog = pd.read_csv(policy_catalog_path)
    summary = render(
        composite,
        boundaries,
        priority,
        overlay,
        policy_matrix,
        svg_output,
        pdf_output,
        png_output,
    )
    profiles = build_action_profiles(composite)
    profile_output.parent.mkdir(parents=True, exist_ok=True)
    profiles.to_csv(profile_output, index=False, encoding="utf-8-sig", lineterminator="\n")
    write_action_map(
        profiles,
        boundaries,
        category_assessments,
        major_category_assessments,
        indicator_scores,
        policy_catalog,
        html_output,
    )
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "reference_year": 2025,
        "artifact_status": "submission_draft",
        "format": "A4 portrait one-page infographic",
        "dong_action_profile_count": len(profiles),
        **summary,
        "input_paths": {
            "composite_index": composite_path.as_posix(),
            "boundaries": boundaries_path.as_posix(),
            "priority_areas": priority_path.as_posix(),
            "environmental_overlay": overlay_path.as_posix(),
            "policy_matrix": policy_matrix_path.as_posix(),
            "category_assessment": category_assessment_path.as_posix(),
            "major_category_assessment": major_category_assessment_path.as_posix(),
            "indicator_scores": indicator_scores_path.as_posix(),
            "policy_catalog": policy_catalog_path.as_posix(),
        },
        "input_sha256": {
            "composite_index": sha256_file(composite_path),
            "boundaries": sha256_file(boundaries_path),
            "priority_areas": sha256_file(priority_path),
            "environmental_overlay": sha256_file(overlay_path),
            "policy_matrix": sha256_file(policy_matrix_path),
            "category_assessment": sha256_file(category_assessment_path),
            "major_category_assessment": sha256_file(major_category_assessment_path),
            "indicator_scores": sha256_file(indicator_scores_path),
            "policy_catalog": sha256_file(policy_catalog_path),
        },
        "output_paths": {
            "svg": svg_output.as_posix(),
            "pdf": pdf_output.as_posix(),
            "png": png_output.as_posix(),
            "action_profile_csv": profile_output.as_posix(),
            "interactive_action_map": html_output.as_posix(),
        },
        "output_sha256": {
            "svg": sha256_file(svg_output),
            "pdf": sha256_file(pdf_output),
            "png": sha256_file(png_output),
            "action_profile_csv": sha256_file(profile_output),
            "interactive_action_map": sha256_file(html_output),
        },
        "interpretation": (
            "Public-data experimental screening; not an official index, causal estimate, "
            "individual eligibility rule, or final funding decision"
        ),
    }
    write_json(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--composite-index", type=Path, default=DEFAULT_COMPOSITE)
    parser.add_argument("--boundaries", type=Path, default=DEFAULT_BOUNDARIES)
    parser.add_argument("--priority-areas", type=Path, default=DEFAULT_PRIORITY_OUTPUT)
    parser.add_argument("--environmental-overlay", type=Path, default=DEFAULT_OVERLAY)
    parser.add_argument("--policy-matrix", type=Path, default=DEFAULT_POLICY_MATRIX)
    parser.add_argument(
        "--category-assessment",
        type=Path,
        default=DEFAULT_CATEGORY_ASSESSMENT,
    )
    parser.add_argument(
        "--major-category-assessment",
        type=Path,
        default=DEFAULT_MAJOR_CATEGORY_ASSESSMENT,
    )
    parser.add_argument("--indicator-scores", type=Path, default=DEFAULT_INDICATOR_SCORES)
    parser.add_argument("--policy-catalog", type=Path, default=DEFAULT_POLICY_CATALOG)
    parser.add_argument("--svg-output", type=Path, default=DEFAULT_SVG_OUTPUT)
    parser.add_argument("--pdf-output", type=Path, default=DEFAULT_PDF_OUTPUT)
    parser.add_argument("--png-output", type=Path, default=DEFAULT_PNG_OUTPUT)
    parser.add_argument("--profile-output", type=Path, default=DEFAULT_PROFILE_OUTPUT)
    parser.add_argument("--html-output", type=Path, default=DEFAULT_HTML_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run(
        args.composite_index,
        args.boundaries,
        args.priority_areas,
        args.environmental_overlay,
        args.policy_matrix,
        args.category_assessment,
        args.major_category_assessment,
        args.indicator_scores,
        args.policy_catalog,
        args.svg_output,
        args.pdf_output,
        args.png_output,
        args.profile_output,
        args.html_output,
        args.report,
    )
    print(
        f"rendered {report['page_count']}-page infographic with "
        f"{report['priority_area_count']} priority areas"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
