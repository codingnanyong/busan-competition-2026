from __future__ import annotations

import re

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from busan_imd.infographic import render


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
