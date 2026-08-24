from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from busan_imd.environmental_overlay import build, run


def inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    index = np.arange(206)
    codes = pd.Series(index).map(lambda value: f"{value:03d}")
    composite = pd.DataFrame(
        {
            "admin_dong_code": codes,
            "sigungu_name": "District",
            "admin_dong_name": codes.map(lambda value: f"Dong {value}"),
            "b_imd_score_0_100": 100 - index / 3,
            "b_imd_rank": index + 1,
            "b_imd_decile": np.where(index < 21, 1, 2),
            **{
                f"{domain}_score_0_100": 100 - index / 3
                for domain in (
                    "income",
                    "employment",
                    "education",
                    "health",
                    "housing_access",
                )
            },
        }
    )
    profile = pd.DataFrame(
        {
            "admin_dong_code": codes,
            "annual_pm25_ug_m3_idw_2025": 206 - index,
            "annual_pm10_ug_m3_idw_2025": 412 - index * 2,
        }
    )
    return composite, profile


def test_build_identifies_exact_top_quartile_and_double_burden() -> None:
    composite, profile = inputs()

    overlay, report = build(composite, profile)

    assert len(overlay) == 206
    assert report["high_exposure_count"] == 52
    assert report["priority_area_count"] == 21
    assert report["double_burden_count"] == 21
    assert report["category_counts"] == {
        "double_burden": 21,
        "high_air_only": 31,
        "neither": 154,
    }
    assert report["spearman_correlations_with_particulate_free_b_imd"][
        "particulate_exposure_score_0_100"
    ] == 1.0
    assert report["port_industrial_overlay"]["status"] == (
        "not_evaluated_no_versioned_site_geometry"
    )
    assert overlay["particulate_exposure_rank"].nunique() == 206
    assert overlay["particulate_free_b_imd_rank"].nunique() == 206


def test_build_rejects_mismatched_or_incomplete_inputs() -> None:
    composite, profile = inputs()

    with pytest.raises(ValueError, match="must match exactly"):
        build(composite, profile.assign(admin_dong_code=lambda frame: frame.index + 1))
    with pytest.raises(ValueError, match="206 unique"):
        build(composite.iloc[:-1], profile.iloc[:-1])
    with pytest.raises(ValueError, match="missing columns"):
        build(composite, profile.drop(columns="annual_pm25_ug_m3_idw_2025"))


def test_run_creates_independent_output_directories(tmp_path) -> None:
    composite, profile = inputs()
    composite_path = tmp_path / "input" / "composite.csv"
    profile_path = tmp_path / "input" / "profile.csv"
    output_path = tmp_path / "output" / "overlay.csv"
    report_path = tmp_path / "report" / "overlay.json"
    composite_path.parent.mkdir(parents=True)
    composite.to_csv(composite_path, index=False)
    profile.to_csv(profile_path, index=False)

    report = run(composite_path, profile_path, output_path, report_path)

    assert output_path.is_file()
    assert report_path.is_file()
    assert report["double_burden_count"] == 21
