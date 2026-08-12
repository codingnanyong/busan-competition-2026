import json
from pathlib import Path

import pytest

from busan_imd.admin_boundaries import code_rows, read_env_file, validate_boundaries


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


def test_committed_manifest_has_no_secret_and_matches_reference_table() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest_path = root / "docs/data/BUSAN_ADMIN_DONG_MANIFEST_2025.json"
    codes_path = root / "docs/data/BUSAN_ADMIN_DONG_CODES_2025.csv"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)

    assert "accessToken" not in manifest_text
    assert "consumer_secret" not in manifest_text
    assert manifest["reference_year"] == 2025
    assert manifest["feature_count"] == 206
    assert codes_path.read_text(encoding="utf-8-sig").count("\n") == 207


def test_committed_geometry_report_records_repair() -> None:
    root = Path(__file__).resolve().parents[1]
    report = json.loads(
        (root / "docs/data/BUSAN_ADMIN_DONG_GEOMETRY_VALIDATION_2025.json").read_text(
            encoding="utf-8"
        )
    )

    assert report["source_checks"]["invalid_geometries"] == 1
    assert report["invalid_geometry_details"][0]["adm_cd"] == "21100620"
    assert report["repaired_checks"]["invalid_geometries"] == 0
    assert len(report["source_sha256"]) == 64
    assert len(report["repair_output_sha256"]) == 64
