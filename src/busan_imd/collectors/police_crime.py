"""Collect 2025 Busan police-station five-major-crime statistics."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from busan_imd.core.artifacts import sha256_file, write_csv, write_json
from busan_imd.core.config import read_env_file, require_values
from busan_imd.core.http import encoded_secret_url, retry_fetch
from busan_imd.core.provenance import PRIMARY_REFERENCE_YEAR, ensure_secret_free

SOURCE_PAGE = "https://www.data.go.kr/data/15036510/fileData.do"
ENDPOINT = (
    "https://api.odcloud.kr/api/15036510/v1/"
    "uddi:f21fd44d-104d-437d-a965-87fd92475727"
)
DEFAULT_OUTPUT_ROOT = Path("data/raw/public_data_portal/police_crime/2025")
DEFAULT_MANIFEST_PATH = Path("docs/data/manifests/POLICE_CRIME_MANIFEST_2025.json")

COLUMN_MAP = {
    "연번": "sequence",
    "경찰서": "police_station",
    "구분": "jurisdiction_type",
    "살인": "murder",
    "강도": "robbery",
    "성범죄": "sexual_crime",
    "절도": "theft",
    "폭력": "violence",
}
CRIME_COLUMNS = ("murder", "robbery", "sexual_crime", "theft", "violence")


def build_url(service_key: str) -> str:
    """Build the ODCloud URL without double-encoding the portal service key."""
    return encoded_secret_url(
        ENDPOINT,
        "serviceKey",
        service_key,
        {"page": "1", "perPage": "100", "returnType": "JSON"},
    )


def response_rows(payload: bytes) -> list[dict[str, object]]:
    """Validate and normalize the automatic file-data API response."""
    document = json.loads(payload)
    data = document.get("data")
    if not isinstance(data, list):
        raise ValueError("Police crime API response has no data list")
    total_count = int(document.get("totalCount", -1))
    if total_count != len(data):
        raise ValueError(f"Expected {total_count} police rows, received {len(data)}")

    rows: list[dict[str, object]] = []
    for source_row in data:
        missing = set(COLUMN_MAP) - set(source_row)
        if missing:
            raise ValueError(f"Police crime row is missing columns: {sorted(missing)}")
        row: dict[str, object] = {
            target: source_row[source] for source, target in COLUMN_MAP.items()
        }
        for column in ("sequence", *CRIME_COLUMNS):
            row[column] = int(row[column])
        row["total_five_major_crimes"] = sum(int(row[column]) for column in CRIME_COLUMNS)
        rows.append(row)
    return rows


def validate_manifest(manifest: dict[str, object], root: Path = Path(".")) -> None:
    """Keep police-station statistics validation-only and verify file integrity."""
    ensure_secret_free(manifest)
    if manifest.get("primary_reference_year") != PRIMARY_REFERENCE_YEAR:
        raise ValueError("Police crime manifest has the wrong primary reference year")
    if manifest.get("analysis_role") != "validation":
        raise ValueError("Police-station crime statistics must remain validation-only")
    if manifest.get("eligible_for_primary_analysis") is not False:
        raise ValueError("Police-station crime rows cannot directly score administrative dongs")
    if manifest.get("record_count") != 16 or manifest.get("police_station_count") != 16:
        raise ValueError("Police crime data must contain all 16 Busan police stations")
    for key in ("raw_path", "csv_path"):
        path = root / str(manifest[key])
        checksum_key = f"{key.removesuffix('_path')}_sha256"
        if path.exists() and sha256_file(path) != manifest[checksum_key]:
            raise ValueError(f"Police crime checksum mismatch: {path}")


def collect(
    service_key: str,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    *,
    fetcher: Callable[[str], bytes] = retry_fetch,
    reuse_existing: bool = True,
) -> dict[str, object]:
    """Retain the raw response and write a normalized, secret-free CSV and manifest."""
    raw_path = output_root / "raw" / "busan_police_five_major_crimes_2025.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    if reuse_existing and raw_path.exists():
        payload = raw_path.read_bytes()
    else:
        payload = fetcher(build_url(service_key))
        raw_path.write_bytes(payload)

    rows = response_rows(payload)
    police_stations = {str(row["police_station"]) for row in rows}
    if len(rows) != 16 or len(police_stations) != 16:
        raise ValueError(
            f"Expected 16 unique Busan police stations, received {len(rows)}/{len(police_stations)}"
        )

    csv_path = output_root / "busan_police_five_major_crimes_2025.csv"
    write_csv(csv_path, rows)
    retrieved_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    manifest: dict[str, object] = {
        "schema_version": 1,
        "generated_at": retrieved_at,
        "analysis_cutoff": "2026-07-31",
        "primary_reference_year": PRIMARY_REFERENCE_YEAR,
        "dataset_id": "SAF-BUSAN-POLICE-CRIME-001",
        "provider": "Busan Metropolitan Police Agency",
        "source_page": SOURCE_PAGE,
        "source_attribution": (
            "Source: Busan Metropolitan Police Agency, 2025 five-major-crime statistics"
        ),
        "endpoint": ENDPOINT,
        "access_method": "authenticated Public Data Portal automatic Open API",
        "reference_period": "2025-01-01/2025-12-31",
        "period_type": "annual",
        "analysis_role": "validation",
        "eligible_for_primary_analysis": False,
        "spatial_unit": "police station jurisdiction",
        "limitations": (
            "Police jurisdictions do not align one-to-one with the 206 administrative dongs; "
            "do not allocate station totals to dongs or use them as direct IMD scores."
        ),
        "record_count": len(rows),
        "police_station_count": len(police_stations),
        "crime_count_total": sum(int(row["total_five_major_crimes"]) for row in rows),
        "raw_path": raw_path.as_posix(),
        "raw_sha256": sha256_file(raw_path),
        "csv_path": csv_path.as_posix(),
        "csv_sha256": sha256_file(csv_path),
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
    require_values(config, ("DATA_GO_KR_SERVICE_KEY",), args.env_file)
    manifest = collect(
        config["DATA_GO_KR_SERVICE_KEY"],
        args.output_root,
        args.manifest,
        reuse_existing=not args.refresh,
    )
    print(
        "collected police five-major-crime statistics: "
        f"{manifest['record_count']} stations / {manifest['crime_count_total']} incidents"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
