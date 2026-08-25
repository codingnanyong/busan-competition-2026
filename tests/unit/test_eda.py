from __future__ import annotations

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from busan_imd.analysis.eda import build, correlation_outputs, morans_i, summarize_indicators


def dictionary_for(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "column_name": columns,
            "source_dataset_id": ["TEST-001"] * len(columns),
            "analysis_role": ["provisional_scoring_proxy"] * len(columns),
            "direction": ["higher is more deprived"] * len(columns),
            "quality_warning": [""] * len(columns),
        }
    )


def test_summary_and_correlation_detect_quality_signals() -> None:
    profile = pd.DataFrame(
        {
            "admin_dong_code": ["1", "2", "3", "4", "5"],
            "indicator_a": [0.0, 1.0, 2.0, 3.0, 100.0],
            "indicator_b": [0.0, 2.0, 4.0, 6.0, 200.0],
            "indicator_c": [1.0, None, 1.0, 1.0, 1.0],
        }
    )
    dictionary = dictionary_for(["indicator_a", "indicator_b", "indicator_c"])

    summary = summarize_indicators(profile, dictionary)
    correlations, high = correlation_outputs(profile, summary)

    row_a = summary.set_index("indicator").loc["indicator_a"]
    row_c = summary.set_index("indicator").loc["indicator_c"]
    assert row_a["iqr_outlier_count"] == 1
    assert row_c["missing_count"] == 1
    assert correlations.loc["indicator_a", "indicator_b"] == pytest.approx(1.0)
    assert len(high) == 1


def test_morans_i_detects_neighbor_similarity() -> None:
    value = morans_i(pd.Series([1.0, 1.0, 10.0, 10.0]), [(0, 1), (1, 2), (2, 3)])

    assert value is not None
    assert value > 0


def test_build_requires_canonical_206_dongs() -> None:
    profile = pd.DataFrame(
        {
            "admin_dong_code": ["1", "2"],
            "sigungu_name": ["A", "A"],
            "indicator": [1.0, 2.0],
        }
    )
    boundaries = gpd.GeoDataFrame(
        {"admin_dong_code": ["1", "2"]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)],
        crs="EPSG:5179",
    )

    with pytest.raises(ValueError, match="206 unique"):
        build(profile, dictionary_for(["indicator"]), boundaries)
