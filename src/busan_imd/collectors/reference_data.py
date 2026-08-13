"""Collect public demographic and school reference data for Busan."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode

from busan_imd.core.artifacts import sha256_file as sha256
from busan_imd.core.artifacts import write_json
from busan_imd.core.config import read_env_file, require_values
from busan_imd.core.http import fetch_bytes
from busan_imd.core.provenance import (
    PRIMARY_REFERENCE_END,
    PRIMARY_REFERENCE_YEAR,
    ensure_secret_free,
)
from busan_imd.sources.neis import ENDPOINT as SCHOOL_ENDPOINT
from busan_imd.sources.neis import SOURCE_PAGE as SCHOOL_SOURCE
from busan_imd.sources.neis import fetch_school_page
from busan_imd.sources.sgis import authenticate

OUTPUT_ROOT = Path("data/raw/reference")
MANIFEST_PATH = Path("docs/data/manifests/REFERENCE_DATA_MANIFEST.json")
SGIS_SOURCE = "https://sgis.mods.go.kr/developer/html/newOpenApi/api/dataApi/census.html"
SGIS_ENDPOINT = "https://sgisapi.mods.go.kr/OpenAPI3/stats/population.json"
PRIMARY_REFERENCE_END_COMPACT = PRIMARY_REFERENCE_END.strftime("%Y%m%d")


def collect_sgis_demographics(config: dict[str, str], output_root: Path) -> dict[str, object]:
    """Collect the latest SGIS population and household denominators for Busan dongs."""
    token = authenticate(config["SGIS_CONSUMER_KEY"], config["SGIS_CONSUMER_SECRET"])
    parameters = {"year": "2024", "adm_cd": "21", "low_search": "2"}
    url = f"{SGIS_ENDPOINT}?{urlencode({**parameters, 'accessToken': token})}"
    payload = fetch_bytes(url)
    document = json.loads(payload)
    if document.get("errCd") != 0:
        raise ValueError(f"SGIS population API error: {document.get('errMsg')}")
    rows = document.get("result", [])
    codes = {str(row.get("adm_cd", "")) for row in rows}
    required = {"adm_cd", "adm_nm", "tot_ppltn", "tot_family"}
    if len(rows) != 206 or len(codes) != 206:
        raise ValueError(f"Expected 206 unique Busan dong rows, received {len(rows)}/{len(codes)}")
    if any(not required <= set(row) for row in rows):
        raise ValueError("SGIS population response is missing a required denominator field")

    path = output_root / "DEM-SGIS-001" / "sgis_population_households_2024.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {
        "dataset_id": "DEM-SGIS-001",
        "provider": "Statistics Korea SGIS",
        "source_page": SGIS_SOURCE,
        "endpoint": SGIS_ENDPOINT,
        "access_method": "SGIS consumer key and secret",
        "request_parameters": parameters,
        "reference_period": "2024-12-31",
        "primary_reference_year": PRIMARY_REFERENCE_YEAR,
        "analysis_role": "fallback",
        "lag_years": 1,
        "period_type": "annual",
        "cutoff_status": "eligible",
        "local_path": path.as_posix(),
        "record_count": len(rows),
        "fields": sorted(required),
        "sha256": sha256(path),
        "notes": (
            "Latest year exposed by the SGIS API; 206 rows align with the 2025 boundary count."
        ),
    }


school_page = fetch_school_page


def collect_neis_schools(api_key: str, output_root: Path) -> dict[str, object]:
    """Collect every Busan school row through the authenticated NEIS API."""
    first = school_page(1, api_key)
    total = int(first["schoolInfo"][0]["head"][0]["list_total_count"])
    rows = list(first["schoolInfo"][1]["row"])
    page = 2
    while len(rows) < total:
        document = school_page(page, api_key)
        rows.extend(document["schoolInfo"][1]["row"])
        page += 1
    if len(rows) != total:
        raise ValueError(f"Expected {total} NEIS school rows, received {len(rows)}")
    eligible_rows = [
        row
        for row in rows
        if not row.get("FOND_YMD") or str(row["FOND_YMD"]) <= PRIMARY_REFERENCE_END_COMPACT
    ]
    excluded_rows = [row for row in rows if row not in eligible_rows]
    school_codes = [str(row.get("SD_SCHUL_CODE", "")).strip() for row in eligible_rows]
    if any(not code for code in school_codes) or len(school_codes) != len(set(school_codes)):
        raise ValueError("Cutoff-eligible NEIS school identifiers are blank or duplicated")

    payload = json.dumps({"schoolInfo": rows}, ensure_ascii=False, indent=2).encode()
    path = output_root / "EDU-SCHOOL-NEIS-001" / "busan_school_info.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    load_dates = sorted({str(row.get("LOAD_DTM", "")) for row in rows if row.get("LOAD_DTM")})
    return {
        "dataset_id": "EDU-SCHOOL-NEIS-001",
        "provider": "KERIS NEIS Education Information Open Portal",
        "source_page": SCHOOL_SOURCE,
        "endpoint": SCHOOL_ENDPOINT,
        "access_method": "NEIS OpenAPI key required",
        "request_parameters": {"ATPT_OFCDC_SC_CODE": "C10", "Type": "json"},
        "reference_period": "current register; record load dates vary",
        "primary_reference_year": PRIMARY_REFERENCE_YEAR,
        "analysis_role": "primary_facility_filter",
        "facility_opening_cutoff": PRIMARY_REFERENCE_END.isoformat(),
        "period_type": "snapshot",
        "cutoff_status": "unverified",
        "load_date_min": load_dates[0],
        "load_date_max": load_dates[-1],
        "local_path": path.as_posix(),
        "record_count": len(rows),
        "analysis_eligible_record_count": len(eligible_rows),
        "excluded_after_cutoff_record_count": len(excluded_rows),
        "analysis_cutoff": "2026-07-31",
        "sha256": sha256(path),
        "notes": (
            "The raw register includes future-planned schools. Records with FOND_YMD after "
            "2025-12-31 are retained for provenance but excluded from the primary 2025 analysis."
        ),
    }


def write_manifest(entries: list[dict[str, object]], path: Path) -> None:
    """Write a secret-free provenance manifest."""
    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "analysis_cutoff": "2026-07-31",
        "primary_reference_year": PRIMARY_REFERENCE_YEAR,
        "dataset_count": len(entries),
        "datasets": entries,
    }
    ensure_secret_free(manifest)
    write_json(path, manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    args = parser.parse_args()
    config = read_env_file(args.env_file)
    require_values(config, ("SGIS_CONSUMER_KEY", "SGIS_CONSUMER_SECRET"), args.env_file)
    entries = [collect_sgis_demographics(config, args.output_root)]
    if config.get("NEIS_API_KEY"):
        entries.append(collect_neis_schools(config["NEIS_API_KEY"], args.output_root))
    write_manifest(entries, args.manifest)
    print(f"collected {len(entries)} reference datasets; manifest: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
