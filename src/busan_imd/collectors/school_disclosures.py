"""Collect 2025 Busan school staffing and student records from SchoolInfo."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from busan_imd.core.artifacts import sha256_file, write_json
from busan_imd.core.config import read_env_file, require_values
from busan_imd.core.http import fetch_bytes
from busan_imd.core.provenance import ensure_secret_free

ENDPOINT = "https://www.schoolinfo.go.kr/openApi.do"
SOURCE_PAGE = "https://www.schoolinfo.go.kr/ng/go/pnnggo_a01_l0.do"
OUTPUT_ROOT = Path("data/raw/reference/EDU-SCHOOLINFO-2025-001")
RAW_PATH = OUTPUT_ROOT / "busan_school_disclosures_2025.json"
MANIFEST_PATH = Path("docs/data/manifests/SCHOOLINFO_DISCLOSURE_MANIFEST_2025.json")
REFERENCE_YEAR = "2025"
BUSAN_SIDO_CODE = "26"
DISTRICT_CODES = (
    "26110",
    "26140",
    "26170",
    "26200",
    "26230",
    "26260",
    "26290",
    "26320",
    "26350",
    "26380",
    "26410",
    "26440",
    "26470",
    "26500",
    "26530",
    "26710",
)
SCHOOL_KIND_CODES = ("02", "03", "04")
API_TYPES = {"student_movement": "10", "teachers": "22"}


def fetch_disclosure(
    api_key: str,
    api_type: str,
    district_code: str,
    school_kind_code: str,
    fetcher: Callable[[str], bytes] = fetch_bytes,
) -> list[dict[str, Any]]:
    """Fetch one SchoolInfo disclosure slice without persisting the credential."""
    parameters = {
        "apiKey": api_key,
        "apiType": api_type,
        "pbanYr": REFERENCE_YEAR,
        "sidoCode": BUSAN_SIDO_CODE,
        "sggCode": district_code,
        "schulKndCode": school_kind_code,
    }
    document = json.loads(fetcher(f"{ENDPOINT}?{urlencode(parameters)}"))
    if document.get("resultCode") != "success":
        raise ValueError(f"SchoolInfo API error: {document.get('resultMsg')}")
    rows = document.get("list", [])
    if not isinstance(rows, list):
        raise ValueError("SchoolInfo list must be an array")
    return [
        {**row, "_sgg_code": district_code, "_school_kind_code": school_kind_code}
        for row in rows
    ]


def collect(
    api_key: str,
    raw_path: Path = RAW_PATH,
    manifest_path: Path = MANIFEST_PATH,
    fetcher: Callable[[str], bytes] = fetch_bytes,
) -> dict[str, Any]:
    """Collect the complete 2025 Busan primary and secondary school disclosure set."""
    datasets: dict[str, list[dict[str, Any]]] = {}
    for name, api_type in API_TYPES.items():
        rows: list[dict[str, Any]] = []
        for district_code in DISTRICT_CODES:
            for school_kind_code in SCHOOL_KIND_CODES:
                rows.extend(
                    fetch_disclosure(
                        api_key,
                        api_type,
                        district_code,
                        school_kind_code,
                        fetcher,
                    )
                )
        school_codes = [str(row.get("SCHUL_CODE", "")).strip() for row in rows]
        if any(not code for code in school_codes):
            raise ValueError(f"SchoolInfo {name} includes a blank school code")
        if len(school_codes) != len(set(school_codes)):
            raise ValueError(f"SchoolInfo {name} includes duplicate school codes")
        datasets[name] = sorted(rows, key=lambda row: str(row["SCHUL_CODE"]))

    required_students = {"SCHUL_CODE", "SCHUL_NM", "STDNT_SUM"}
    required_teachers = {"SCHUL_CODE", "SCHUL_NM", "COL_S"}
    if any(not required_students <= set(row) for row in datasets["student_movement"]):
        raise ValueError("SchoolInfo student records are missing required fields")
    if any(not required_teachers <= set(row) for row in datasets["teachers"]):
        raise ValueError("SchoolInfo teacher records are missing required fields")

    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(datasets, ensure_ascii=False, indent=2), encoding="utf-8")
    student_codes = {str(row["SCHUL_CODE"]) for row in datasets["student_movement"]}
    teacher_codes = {str(row["SCHUL_CODE"]) for row in datasets["teachers"]}
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    manifest = {
        "schema_version": 1,
        "dataset_id": "EDU-SCHOOLINFO-2025-001",
        "provider": "Korea Education and Research Information Service SchoolInfo",
        "source_page": SOURCE_PAGE,
        "endpoint": ENDPOINT,
        "access_method": "SchoolInfo OpenAPI key",
        "reference_period": "2025 school disclosure year",
        "period_type": "annual_school_disclosure",
        "retrieved_at": generated_at,
        "analysis_role": "provisional_scoring_proxy",
        "spatial_unit": "school location",
        "license": "Korea Open Government License Type 1 (attribution)",
        "student_record_count": len(datasets["student_movement"]),
        "teacher_record_count": len(datasets["teachers"]),
        "shared_school_code_count": len(student_codes & teacher_codes),
        "district_count": len(DISTRICT_CODES),
        "school_kind_codes": list(SCHOOL_KIND_CODES),
        "api_types": API_TYPES,
        "local_path": raw_path.as_posix(),
        "sha256": sha256_file(raw_path),
        "notes": (
            "School-level staffing and enrollment are direct disclosures. Their assignment to "
            "administrative-dong access areas remains a spatial proxy and does not measure "
            "resident educational outcomes. API type 10 currently exposes transfers and total "
            "students but no dropout-count field."
        ),
    }
    ensure_secret_free(manifest)
    write_json(manifest_path, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--raw", type=Path, default=RAW_PATH)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    args = parser.parse_args()
    config = read_env_file(args.env_file)
    require_values(config, ("SCHOOLINFO_API_KEY",), args.env_file)
    report = collect(config["SCHOOLINFO_API_KEY"], args.raw, args.manifest)
    print(
        f"collected {report['shared_school_code_count']} shared 2025 school disclosures; "
        f"manifest: {args.manifest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
