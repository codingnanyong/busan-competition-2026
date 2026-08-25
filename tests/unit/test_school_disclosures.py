"""Unit tests for SchoolInfo disclosure collection."""

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from busan_imd.collectors.school_disclosures import collect


def test_collect_writes_complete_secret_free_disclosures(tmp_path: Path) -> None:
    def fetcher(url: str) -> bytes:
        query = parse_qs(urlparse(url).query)
        school_code = f"{query['sggCode'][0]}{query['schulKndCode'][0]}"
        row = {
            "SCHUL_CODE": school_code,
            "SCHUL_NM": f"School {school_code}",
        }
        if query["apiType"] == ["10"]:
            row["STDNT_SUM"] = "100"
        else:
            row["COL_S"] = "20"
        return json.dumps({"resultCode": "success", "list": [row]}).encode()

    raw_path = tmp_path / "schoolinfo.json"
    manifest_path = tmp_path / "manifest.json"
    manifest = collect("secret-key", raw_path, manifest_path, fetcher)

    assert manifest["student_record_count"] == 48
    assert manifest["teacher_record_count"] == 48
    assert manifest["shared_school_code_count"] == 48
    assert "secret-key" not in manifest_path.read_text(encoding="utf-8")
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    assert set(payload) == {"student_movement", "teachers"}
