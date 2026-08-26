from __future__ import annotations

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, box

from busan_imd.processing.standardization import (
    attach_combined_source_metadata,
    historical_stop_demand_validation,
    points_from_xy,
    route_demand_access,
    spatial_counts,
    validate_code_frame,
)


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


def test_route_demand_access_maps_unique_routes_and_logs_annual_usage() -> None:
    boundaries = gpd.GeoDataFrame(
        {
            "admin_dong_code": ["21000001", "21000002", "21000003"],
            "adm_nm": [
                "부산광역시 테스트구 가동",
                "부산광역시 테스트구 나동",
                "부산광역시 테스트구 다동",
            ],
        },
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1), box(2, 0, 3, 1)],
        crs="EPSG:4326",
    )
    bus_stops = gpd.GeoDataFrame(
        {
            "bstopid": ["a", "b", "c", "d", "e", "f"],
            "arsno": ["1", "2", "3", "4", "5", "6"],
        },
        geometry=[
            Point(0.2, 0.2),
            Point(1.2, 0.2),
            Point(0.4, 0.4),
            Point(3.5, 3.5),
            Point(0.6, 0.6),
            Point(2.2, 0.2),
        ],
        crs="EPSG:4326",
    )
    route_stops = pd.DataFrame(
        {
            "buslinenum": ["10", "10", "20", "20", "30", "40"],
            "nodeid": ["a", "b", "c", "d", "e", "f"],
            "arsno": ["1", "2", "3", "4", "5", "6"],
        }
    )
    usage = pd.DataFrame(
        {
            "route_no": ["10", "20", "40", "missing"],
            "card_trip_count_2025": [99, 9, 5, 999],
        }
    )
    service = pd.DataFrame(
        {
            "buslinenum": ["10", "20", "30", "40"],
            "firsttime": ["05:00", "06:00", "", ""],
            "endtime": ["23:00", "22:00", "", ""],
            "headwaynorm": [10, 20, None, None],
        }
    )

    result, report = route_demand_access(
        boundaries, bus_stops, route_stops, usage, service
    )
    indexed = result.set_index("admin_dong_code")

    assert indexed.loc["21000001", "matched_bus_routes_2025_current_proxy"] == 2
    assert indexed.loc[
        "21000001", "demand_weighted_bus_route_access_2025_current_proxy"
    ] == pytest.approx(6.907755)
    assert indexed.loc["21000002", "matched_bus_routes_2025_current_proxy"] == 1
    assert indexed.loc[
        "21000001", "scheduled_bus_service_opportunities_current_proxy"
    ] == pytest.approx(156)
    assert indexed.loc["21000001", "current_routes_with_service_schedule"] == 2
    assert pd.isna(
        indexed.loc["21000003", "scheduled_bus_service_opportunities_current_proxy"]
    )
    assert pd.isna(
        indexed.loc["21000003", "late_bus_service_opportunities_current_proxy"]
    )
    assert indexed.loc["21000003", "current_routes_with_service_schedule"] == 0
    assert report["matched_route_count"] == 3
    assert report["route_match_rate"] == pytest.approx(3 / 4, abs=1e-6)


def test_historical_stop_demand_validation_keeps_only_unique_route_name_matches() -> None:
    boundaries = synthetic_boundaries().set_crs("EPSG:4326", allow_override=True)
    bus_stops = gpd.GeoDataFrame(
        {"bstopid": ["a", "b"], "arsno": ["1", "2"]},
        geometry=[Point(0.2, 0.2), Point(1.2, 0.2)],
        crs="EPSG:4326",
    )
    route_stops = pd.DataFrame(
        {
            "buslinenum": ["10", "20"],
            "nodeid": ["a", "b"],
            "arsno": ["1", "2"],
            "bstopnm": ["첫째", "둘째"],
        }
    )
    boarding = pd.DataFrame(
        {
            "노선번호": ["10", "20", "99"],
            "정류장명": ["첫째", "둘째", "없음"],
            "승차합계": [100, 50, 999],
            "하차합계": [50, 50, 999],
            "오전7시00분_승차건수(선탑_후탑)": [20, 10, 999],
            "오후10시00분_하차건수": [5, 4, 999],
        }
    )

    result, report = historical_stop_demand_validation(
        boundaries, bus_stops, route_stops, boarding
    )
    indexed = result.set_index("admin_dong_code")

    assert indexed.loc["21000001", "bus_boarding_alighting_2023_validation"] == 150
    assert indexed.loc["21000002", "peak_bus_demand_share_pct_2023_validation"] == 10
    assert report["matched_records"] == 2
    assert report["decision"] == "validation_only"


def test_attach_combined_source_metadata_keeps_a_single_hex_digest(tmp_path) -> None:
    first = tmp_path / "a.csv"
    second = tmp_path / "b.csv"
    first.write_text("a", encoding="utf-8")
    second.write_text("b", encoding="utf-8")

    report = attach_combined_source_metadata({"dataset_id": "combined"}, [first, second])

    assert report["source_path"] == f"{first.as_posix()};{second.as_posix()}"
    assert report["source_paths"] == [first.as_posix(), second.as_posix()]
    assert len(report["source_sha256"]) == 64
    assert report["source_sha256"].isupper()
    assert isinstance(report["source_sha256"], str)
