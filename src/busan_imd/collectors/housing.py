"""Collect SGIS housing statistics for a 2025 one-year-lag proxy."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode

from busan_imd.core.artifacts import aggregate_sha256, sha256_file, write_csv, write_json
from busan_imd.core.config import read_env_file, require_values
from busan_imd.core.http import retry_fetch
from busan_imd.core.provenance import PRIMARY_REFERENCE_YEAR, ensure_secret_free
from busan_imd.sources.sgis import authenticate

SOURCE_PAGE = "https://sgis.mods.go.kr/developer/html/newOpenApi/api/dataApi/census.html"
ENDPOINT = "https://sgisapi.mods.go.kr/OpenAPI3/stats/house.json"
REFERENCE_YEAR = 2024
OLD_HOUSING_CODES = {
    "10": "30_to_under_40_years",
    "11": "40_to_under_50_years",
    "12": "50_years_or_more",
}
DEFAULT_OUTPUT_ROOT = Path("data/raw/sgis/housing/2024")
DEFAULT_MANIFEST_PATH = Path("docs/data/manifests/SGIS_HOUSING_PROXY_MANIFEST_2025.json")


def build_url(access_token: str, extra: dict[str, str] | None = None) -> str:
    """Build an SGIS housing request for every Busan administrative dong."""
    parameters = {
        "accessToken": access_token,
        "year": str(REFERENCE_YEAR),
        "adm_cd": "21",
        "low_search": "2",
        **(extra or {}),
    }
    return f"{ENDPOINT}?{urlencode(parameters)}"


def response_rows(payload: bytes) -> list[dict[str, object]]:
    """Validate an SGIS response and return its result rows."""
    document = json.loads(payload)
    if document.get("errCd") != 0:
        raise ValueError(f"SGIS housing API error: {document.get('errMsg')}")
    rows = document.get("result")
    if not isinstance(rows, list):
        raise ValueError("SGIS housing response has no result list")
    return rows


def _count(value: object) -> int | None:
    text = str(value).strip()
    return None if text in {"", "N/A", "None"} else int(text)


def normalize(
    total_rows: list[dict[str, object]],
    age_rows: dict[str, list[dict[str, object]]],
) -> tuple[list[dict[str, object]], dict[str, int]]:
    """Create a 206-dong old-housing lower-bound profile with suppression flags."""
    totals = {str(row["adm_cd"]): row for row in total_rows}
    if len(total_rows) != 206 or len(totals) != 206:
        raise ValueError(f"Expected 206 unique total-housing rows, received {len(total_rows)}")

    by_code = {
        code: {str(row["adm_cd"]): row for row in rows} for code, rows in age_rows.items()
    }
    normalized: list[dict[str, object]] = []
    suppressed_cells = 0
    absent_cells = 0
    for adm_cd, total_row in sorted(totals.items()):
        total_houses = _count(total_row.get("house_cnt"))
        if total_houses is None or total_houses <= 0:
            raise ValueError(f"Invalid total house count for {adm_cd}")
        output: dict[str, object] = {
            "adm_cd": adm_cd,
            "adm_nm": str(total_row["adm_nm"]),
            "total_house_count_2024": total_houses,
        }
        old_house_lower_bound = 0
        suppressed_for_dong = 0
        absent_for_dong = 0
        for code, label in OLD_HOUSING_CODES.items():
            source_row = by_code[code].get(adm_cd)
            if source_row is None:
                count = 0
                absent_cells += 1
                absent_for_dong += 1
            else:
                count = _count(source_row.get("house_cnt"))
                if count is None:
                    count = 0
                    suppressed_cells += 1
                    suppressed_for_dong += 1
            output[f"house_count_{label}_2024_lower_bound"] = count
            old_house_lower_bound += count
        output["old_house_count_30plus_2024_lower_bound"] = old_house_lower_bound
        output["old_house_share_30plus_2024_lower_bound_pct"] = round(
            old_house_lower_bound / total_houses * 100, 6
        )
        output["suppressed_age_cells"] = suppressed_for_dong
        output["absent_age_cells_imputed_zero"] = absent_for_dong
        output["inference_target_year"] = 2025
        output["lag_years"] = 1
        normalized.append(output)
    return normalized, {
        "suppressed_age_cells": suppressed_cells,
        "absent_age_cells_imputed_zero": absent_cells,
    }


def validate_manifest(manifest: dict[str, object], root: Path = Path(".")) -> None:
    """Validate coverage, inference disclosure, checksums, and credential hygiene."""
    ensure_secret_free(manifest)
    if manifest.get("primary_reference_year") != PRIMARY_REFERENCE_YEAR:
        raise ValueError("Housing manifest has the wrong primary reference year")
    if manifest.get("reference_period") != "2024-12-31":
        raise ValueError("Housing proxy must retain its observed 2024 reference period")
    if manifest.get("inference_target_year") != 2025 or manifest.get("lag_years") != 1:
        raise ValueError("Housing proxy must disclose its one-year inference lag")
    if manifest.get("record_count") != 206:
        raise ValueError("Housing proxy must cover all 206 Busan administrative dongs")
    csv_path = root / str(manifest["csv_path"])
    if csv_path.exists() and sha256_file(csv_path) != manifest["csv_sha256"]:
        raise ValueError(f"Housing CSV checksum mismatch: {csv_path}")


def collect(
    access_token: str,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    *,
    fetcher: Callable[[str], bytes] = retry_fetch,
    reuse_existing: bool = True,
) -> dict[str, object]:
    """Collect total and 30-plus-year housing counts and write a lagged proxy."""
    raw_dir = output_root / "raw"
    requests = [("total", {})] + [
        (f"age_{code}", {"house_use_prid_cd": code}) for code in OLD_HOUSING_CODES
    ]
    payloads: dict[str, bytes] = {}
    raw_paths: list[Path] = []
    for name, parameters in requests:
        path = raw_dir / f"sgis_housing_2024_{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        if reuse_existing and path.exists():
            payload = path.read_bytes()
        else:
            payload = fetcher(build_url(access_token, parameters))
            path.write_bytes(payload)
        response_rows(payload)
        payloads[name] = payload
        raw_paths.append(path)

    total_rows = response_rows(payloads["total"])
    age_rows = {
        code: response_rows(payloads[f"age_{code}"]) for code in OLD_HOUSING_CODES
    }
    rows, quality = normalize(total_rows, age_rows)
    csv_path = output_root / "busan_admin_dong_old_housing_proxy_2025.csv"
    write_csv(csv_path, rows)

    retrieved_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    manifest: dict[str, object] = {
        "schema_version": 1,
        "generated_at": retrieved_at,
        "analysis_cutoff": "2026-07-31",
        "primary_reference_year": PRIMARY_REFERENCE_YEAR,
        "dataset_id": "HOU-SGIS-OLD-001",
        "provider": "Statistics Korea SGIS",
        "source_page": SOURCE_PAGE,
        "endpoint": ENDPOINT,
        "source_attribution": "Source: Statistics Korea SGIS housing statistics API",
        "access_method": "SGIS consumer key and secret",
        "request_parameters": {
            "year": str(REFERENCE_YEAR),
            "adm_cd": "21",
            "low_search": "2",
            "house_use_prid_cd": list(OLD_HOUSING_CODES),
        },
        "reference_period": "2024-12-31",
        "inference_target_year": 2025,
        "lag_years": 1,
        "period_type": "annual_lagged_proxy",
        "analysis_role": "provisional_scoring_proxy",
        "spatial_unit": "administrative dong",
        "record_count": len(rows),
        "old_housing_definition": "houses used for 30 years or more",
        "value_semantics": "lower bound where SGIS suppresses an age-band value",
        **quality,
        "csv_path": csv_path.as_posix(),
        "csv_sha256": sha256_file(csv_path),
        "raw_directory": raw_dir.as_posix(),
        "raw_aggregate_sha256": aggregate_sha256(raw_paths, raw_dir),
        "limitations": (
            "SGIS does not expose year=2025 housing statistics. The observed 2024 "
            "administrative-dong distribution is used as a one-year-lag 2025 proxy. Missing "
            "age-band rows are treated as zero; N/A cells are treated as zero only to produce "
            "a disclosed lower bound and require sensitivity analysis."
        ),
    }
    validate_manifest(manifest)
    write_json(manifest_path, manifest)
    write_json(output_root / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    config = read_env_file(args.env_file)
    required = ("SGIS_CONSUMER_KEY", "SGIS_CONSUMER_SECRET")
    require_values(config, required, args.env_file)
    token = authenticate(config["SGIS_CONSUMER_KEY"], config["SGIS_CONSUMER_SECRET"])
    manifest = collect(
        token,
        args.output_root,
        args.manifest,
        reuse_existing=not args.refresh,
    )
    print(
        "collected SGIS housing proxy: "
        f"{manifest['record_count']} dongs / {manifest['lag_years']}-year lag"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
