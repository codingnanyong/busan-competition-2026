"""Tests for the 2025 Busan police crime collector."""

import json
from pathlib import Path

from busan_imd.collectors.police_crime import build_url, collect, response_rows


def response() -> bytes:
    data = [
        {
            "연번": number,
            "경찰서": f"경찰서-{number}",
            "구분": "경찰서",
            "살인": 1,
            "강도": 2,
            "성범죄": 3,
            "절도": 4,
            "폭력": 5,
        }
        for number in range(1, 17)
    ]
    return json.dumps(
        {"currentCount": 16, "matchCount": 16, "totalCount": 16, "data": data},
        ensure_ascii=False,
    ).encode()


def test_build_url_preserves_encoded_service_key() -> None:
    url = build_url("abc%2Fdef%3D")
    assert "serviceKey=abc%2Fdef%3D" in url
    assert "%252F" not in url


def test_response_rows_normalizes_columns_and_total() -> None:
    rows = response_rows(response())
    assert len(rows) == 16
    assert rows[0]["police_station"] == "경찰서-1"
    assert rows[0]["total_five_major_crimes"] == 15


def test_collect_retains_raw_and_marks_dataset_validation_only(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest = collect(
        "encoded%2Fsecret%3D",
        tmp_path / "raw",
        manifest_path,
        fetcher=lambda _: response(),
    )

    assert manifest["record_count"] == 16
    assert manifest["crime_count_total"] == 240
    assert manifest["analysis_role"] == "validation"
    assert manifest["eligible_for_primary_analysis"] is False
    assert "encoded%2Fsecret%3D" not in manifest_path.read_text(encoding="utf-8")
