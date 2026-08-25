from __future__ import annotations

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, box

from busan_imd.processing.standardization import points_from_xy, spatial_counts, validate_code_frame


def synthetic_boundaries() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {
            "admin_dong_code": ["21000001", "21000002"],
            "adm_nm": ["부산광역시 테스트구 가동", "부산광역시 테스트구 나동"],
        },
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)],
        crs="EPSG:5179",
    )


def test_validate_code_frame_reports_complete_match() -> None:
    boundaries = synthetic_boundaries()
    frame = pd.DataFrame({"code": ["21000001", "21000002"]})

    report = validate_code_frame(
        frame,
        boundaries,
        dataset_id="TEST",
        code_column="code",
        expected_complete=True,
    )

    assert report["matched_admin_dongs"] == 2
    assert report["missing_admin_dongs"] == 0
    assert report["match_rate"] == 1.0


def test_validate_code_frame_rejects_duplicate_or_missing_codes() -> None:
    boundaries = synthetic_boundaries()
    frame = pd.DataFrame({"code": ["21000001", "21000001"]})

    with pytest.raises(ValueError, match="code validation failed"):
        validate_code_frame(
            frame,
            boundaries,
            dataset_id="TEST",
            code_column="code",
            expected_complete=True,
        )


def test_points_from_xy_keeps_missing_coordinates_out_of_geometry() -> None:
    frame = pd.DataFrame({"x": [0.5, None], "y": [0.5, 0.5]})

    points, missing = points_from_xy(frame, "x", "y", "EPSG:5179")

    assert len(points) == 1
    assert missing == 1


def test_spatial_counts_reports_unmatched_points_without_assigning_them() -> None:
    boundaries = synthetic_boundaries()
    points = gpd.GeoDataFrame(
        {"name": ["inside-a", "inside-b", "outside"]},
        geometry=[Point(0.5, 0.5), Point(1.5, 0.5), Point(3, 3)],
        crs="EPSG:5179",
    )

    counts, report = spatial_counts(
        boundaries,
        points,
        dataset_id="POINTS",
        input_records=3,
        coordinate_missing=0,
    )

    assert counts.to_dict() == {"21000001": 1, "21000002": 1}
    assert report["matched_records"] == 2
    assert report["unmatched_records"] == 1
    assert report["match_rate"] == pytest.approx(2 / 3, abs=1e-6)
