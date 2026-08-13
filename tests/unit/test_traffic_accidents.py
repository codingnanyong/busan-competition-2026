"""Unit tests for KOROAD collection and response validation."""

import json
from pathlib import Path

from busan_imd.collectors.traffic_accidents import (
    HOTSPOT_DISTRICTS,
    STATISTICS_DISTRICTS,
    build_url,
    collect,
    response_rows,
)


def api_response(row: dict[str, str]) -> bytes:
    return json.dumps(
        {
            "resultCode": "00",
            "resultMsg": "NORMAL_CODE",
            "items": {"item": [row]},
            "totalCount": 1,
            "numOfRows": 100,
            "pageNo": 1,
        }
    ).encode()


def test_build_url_preserves_encoded_key() -> None:
    url = build_url("https://example.test", "abc%2Fdef%3D", {"type": "json"})
    assert "authKey=abc%2Fdef%3D" in url
    assert "%252F" not in url


def test_response_rows_rejects_api_errors() -> None:
    payload = json.dumps({"resultCode": "30", "resultMsg": "ERROR"}).encode()
    try:
        response_rows(payload)
    except ValueError as error:
        assert "30" in str(error)
    else:
        raise AssertionError("API error was not rejected")


def test_collect_writes_outputs_without_credentials(tmp_path: Path) -> None:
    def fetcher(url: str) -> bytes:
        district = url.split("guGun=", maxsplit=1)[1].split("&", maxsplit=1)[0]
        if "/stt?" in url:
            row = {
                "std_year": "2025",
                "sido_sgg_nm": f"부산광역시 구{district}",
                "acc_cl_nm": "전체사고",
                "acc_cnt": "1",
            }
        else:
            row = {
                "afos_id": district,
                "sido_sgg_nm": f"부산 구{district}1",
                "lo_crd": "129.0",
                "la_crd": "35.1",
            }
        return api_response(row)

    manifest_path = tmp_path / "manifest.json"
    manifest = collect("encoded%2Fsecret%3D", tmp_path / "raw", manifest_path, fetcher)

    assert manifest["datasets"][0]["record_count"] == len(STATISTICS_DISTRICTS)
    assert manifest["datasets"][1]["record_count"] == len(HOTSPOT_DISTRICTS)
    assert "encoded%2Fsecret%3D" not in manifest_path.read_text(encoding="utf-8")
