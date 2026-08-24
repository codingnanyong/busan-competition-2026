"""Render the reproducible one-page 2025 B-IMD map and infographic draft."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
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


def _font_family() -> str:
    candidates = [path for path in findSystemFonts() if "NotoSansCJK-Regular" in path]
    if not candidates:
        return "DejaVu Sans"
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
    if not set(priority["admin_dong_code"].astype(str)).issubset(
        set(composite["admin_dong_code"].astype(str))
    ):
        raise ValueError("Priority areas must be a subset of the composite")
    if "double_burden" not in overlay or "policy_title_ko" not in policy_matrix:
        raise ValueError("Overlay and policy-matrix inputs are missing presentation columns")


def _panel(ax: plt.Axes) -> None:
    ax.set_facecolor(PALETTE["panel"])
    for spine in ax.spines.values():
        spine.set_color(PALETTE["line"])
        spine.set_linewidth(0.8)


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
    ranked = priority.sort_values("b_imd_rank", kind="stable").head(10)

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
        "부산의 생활취약성, 어디에 집중되는가",
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
                label="PM 이중부담 4개 동",
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
        "상위 10개 우선지역",
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
        "● 대기오염 이중부담  ·  대표 원인: 고용 12개 / 소득 9개",
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
        "분석에서 정책 후보로",
        fontsize=12,
        fontweight="bold",
        color=PALETTE["ink"],
        va="top",
    )
    cards = (
        (
            0.025,
            "교육 중심 상대형 · 5개 동",
            "방과후 학습·학교 접근 취약 점검",
            "가락동은 미세먼지 추가 측정·건강보호 병행",
            PALETTE["gold"],
        ),
        (
            0.515,
            "고용·소득형 · 16개 동",
            "일자리·직업훈련 연계 + 복지급여 누락 점검",
            "모라3·수정4·수정1동은 환경·보건 대응 병행",
            PALETTE["blue"],
        ),
    )
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
        "동일가중에서도 상위 21개 중 18개가 유지되지만, 소득·고용 영역 제외 시 결과가 "
        "크게 달라져 직접 행정자료 검증이 우선입니다.",
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
    svg_output: Path = DEFAULT_SVG_OUTPUT,
    pdf_output: Path = DEFAULT_PDF_OUTPUT,
    png_output: Path = DEFAULT_PNG_OUTPUT,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    """Read canonical artifacts and write the one-page draft plus its manifest."""
    composite = pd.read_csv(composite_path, dtype={"admin_dong_code": str})
    boundaries = gpd.read_file(boundaries_path)
    priority = pd.read_csv(priority_path, dtype={"admin_dong_code": str})
    overlay = pd.read_csv(overlay_path, dtype={"admin_dong_code": str})
    policy_matrix = pd.read_csv(policy_matrix_path)
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
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "reference_year": 2025,
        "artifact_status": "submission_draft",
        "format": "A4 portrait one-page infographic",
        **summary,
        "input_paths": {
            "composite_index": composite_path.as_posix(),
            "boundaries": boundaries_path.as_posix(),
            "priority_areas": priority_path.as_posix(),
            "environmental_overlay": overlay_path.as_posix(),
            "policy_matrix": policy_matrix_path.as_posix(),
        },
        "input_sha256": {
            "composite_index": sha256_file(composite_path),
            "boundaries": sha256_file(boundaries_path),
            "priority_areas": sha256_file(priority_path),
            "environmental_overlay": sha256_file(overlay_path),
            "policy_matrix": sha256_file(policy_matrix_path),
        },
        "output_paths": {
            "svg": svg_output.as_posix(),
            "pdf": pdf_output.as_posix(),
            "png": png_output.as_posix(),
        },
        "output_sha256": {
            "svg": sha256_file(svg_output),
            "pdf": sha256_file(pdf_output),
            "png": sha256_file(png_output),
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
    parser.add_argument("--svg-output", type=Path, default=DEFAULT_SVG_OUTPUT)
    parser.add_argument("--pdf-output", type=Path, default=DEFAULT_PDF_OUTPUT)
    parser.add_argument("--png-output", type=Path, default=DEFAULT_PNG_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run(
        args.composite_index,
        args.boundaries,
        args.priority_areas,
        args.environmental_overlay,
        args.policy_matrix,
        args.svg_output,
        args.pdf_output,
        args.png_output,
        args.report,
    )
    print(
        f"rendered {report['page_count']}-page infographic with "
        f"{report['priority_area_count']} priority areas"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
