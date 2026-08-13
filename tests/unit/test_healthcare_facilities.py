"""Unit tests for migrated healthcare-facility collection."""

import json
from pathlib import Path

from busan_imd.collectors.healthcare_facilities import collect, was_operating_on
from busan_imd.sources.local_licenses import build_url, response_rows


def api_response(rows: list[dict[str, str]]) -> bytes:
    return json.dumps(
        {
            "response": {
                "header": {"resultCode": "0", "resultMsg": "정상"},
                "body": {
                    "items": {"item": rows},
                    "totalCount": len(rows),
                    "pageNo": 1,
                    "numOfRows": 10000,
                },
            }
        },
        ensure_ascii=False,
    ).encode()


def test_build_url_preserves_encoded_service_key() -> None:
    url = build_url("https://example.test", "abc%2Fdef%3D", {"returnType": "json"})
    assert "serviceKey=abc%2Fdef%3D" in url
    assert "%252F" not in url


def test_response_rows_accepts_one_paginated_response() -> None:
    payload = json.dumps(
        {
            "response": {
                "header": {"resultCode": "0", "resultMsg": "정상"},
                "body": {"items": {"item": [{"MNG_NO": "1"}]}, "totalCount": 2},
            }
        }
    ).encode()
    rows, total = response_rows(payload)
    assert rows == [{"MNG_NO": "1"}]
    assert total == 2


def test_2025_operating_reconstruction() -> None:
    assert was_operating_on({"LCPMT_YMD": "20200101"})
    assert not was_operating_on({"LCPMT_YMD": "20260101"})
    assert not was_operating_on({"LCPMT_YMD": "20200101", "CLSBIZ_YMD": "20251231"})
    assert was_operating_on({"LCPMT_YMD": "20200101", "CLSBIZ_YMD": "20260101"})
    assert not was_operating_on(
        {"LCPMT_YMD": "20200101", "TCBIZ_BGNG_YMD": "20251201", "TCBIZ_END_YMD": ""}
    )


def test_collect_writes_secret_free_outputs(tmp_path: Path) -> None:
    def fetcher(url: str) -> bytes:
        name = {
            "hospitals": "병원",
            "clinics": "의원",
            "pharmacies": "약국",
        }[url.split("/")[-2]]
        return api_response(
            [
                {
                    "MNG_NO": f"{name}-1",
                    "BPLC_NM": name,
                    "LCPMT_YMD": "20200101",
                    "ROAD_NM_ADDR": "부산광역시 중구 중앙대로 1",
                    "CRD_INFO_X": "1",
                    "CRD_INFO_Y": "2",
                }
            ]
        )

    manifest_path = tmp_path / "manifest.json"
    manifest = collect("encoded%2Fsecret%3D", tmp_path / "raw", manifest_path, fetcher)

    assert [dataset["record_count"] for dataset in manifest["datasets"]] == [1, 1, 1]
    assert "encoded%2Fsecret%3D" not in manifest_path.read_text(encoding="utf-8")
