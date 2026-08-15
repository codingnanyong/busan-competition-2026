"""Tests for the SGIS lagged housing proxy collector."""

import json
from pathlib import Path

from busan_imd.collectors.housing import collect, normalize


def rows(count: object = "100") -> list[dict[str, object]]:
    return [
        {"adm_cd": f"21{number:05d}", "adm_nm": f"동-{number}", "house_cnt": count}
        for number in range(206)
    ]


def payload(source_rows: list[dict[str, object]]) -> bytes:
    return json.dumps(
        {"errCd": 0, "errMsg": "Success", "result": source_rows}, ensure_ascii=False
    ).encode()


def test_normalize_creates_disclosed_lower_bound() -> None:
    total = rows()
    age = {code: rows("10") for code in ("10", "11", "12")}
    age["12"][0]["house_cnt"] = "N/A"
    age["11"] = age["11"][1:]

    normalized, quality = normalize(total, age)

    assert normalized[0]["old_house_count_30plus_2024_lower_bound"] == 10
    assert normalized[0]["old_house_share_30plus_2024_lower_bound_pct"] == 10
    assert normalized[0]["suppressed_age_cells"] == 1
    assert normalized[0]["absent_age_cells_imputed_zero"] == 1
    assert quality == {"suppressed_age_cells": 1, "absent_age_cells_imputed_zero": 1}


def test_collect_writes_secret_free_manifest(tmp_path: Path) -> None:
    responses = {
        "total": payload(rows()),
        "10": payload(rows("10")),
        "11": payload(rows("20")),
        "12": payload(rows("30")),
    }

    def fetcher(url: str) -> bytes:
        code = url.split("house_use_prid_cd=", maxsplit=1)[1] if "house_use" in url else "total"
        return responses[code]

    manifest_path = tmp_path / "manifest.json"
    manifest = collect("private-token", tmp_path / "raw", manifest_path, fetcher=fetcher)

    assert manifest["record_count"] == 206
    assert manifest["reference_period"] == "2024-12-31"
    assert manifest["inference_target_year"] == 2025
    assert manifest["analysis_role"] == "provisional_scoring_proxy"
    assert "private-token" not in manifest_path.read_text(encoding="utf-8")
