"""Unit tests for SGIS administrative-boundary normalization."""

from pathlib import Path

import pytest

from busan_imd.collectors.admin_boundaries import code_rows, read_env_file, validate_boundaries


def feature(code: str, name: str, geometry_type: str = "Polygon") -> dict:
    coordinates = [[[950000.0, 1950000.0], [950001.0, 1950000.0], [950000.0, 1950000.0]]]
    if geometry_type == "MultiPolygon":
        coordinates = [coordinates]
    return {
        "type": "Feature",
        "properties": {"adm_cd": code, "adm_nm": name},
        "geometry": {"type": geometry_type, "coordinates": coordinates},
    }


def test_validate_boundaries_and_build_code_rows() -> None:
    document = {
        "type": "FeatureCollection",
        "errCd": 0,
        "features": [
            feature("21010520", "부산광역시 중구 동광동", "MultiPolygon"),
            feature("21010510", "부산광역시 중구 중앙동"),
        ],
    }

    features = validate_boundaries(document, expected_count=2)
    rows = code_rows(features, 2025)

    assert [row["admin_dong_code"] for row in rows] == ["21010510", "21010520"]
    assert rows[0]["sigungu_code"] == "21010"
    assert rows[0]["admin_dong_name"] == "중앙동"


def test_validate_boundaries_rejects_duplicate_code() -> None:
    item = feature("21010510", "부산광역시 중구 중앙동")
    document = {"type": "FeatureCollection", "errCd": 0, "features": [item, item]}

    with pytest.raises(ValueError, match="not unique"):
        validate_boundaries(document, expected_count=2)


def test_read_env_file_ignores_comments(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text("# secret values\nSGIS_CONSUMER_KEY='example'\n", encoding="utf-8")

    assert read_env_file(path) == {"SGIS_CONSUMER_KEY": "example"}
