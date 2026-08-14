"""Collect Busan city parks and classify their suitability for a 2025 analysis."""

from __future__ import annotations

import argparse
import math
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path

from busan_imd.core.artifacts import aggregate_sha256, sha256_file, write_csv, write_json
from busan_imd.core.config import read_env_file, require_values
from busan_imd.core.http import retry_fetch
from busan_imd.core.provenance import ensure_secret_free
from busan_imd.sources.city_parks import SOURCE_PAGE, build_url, response_rows

DISTRICTS = (
    "중구", "서구", "동구", "영도구", "부산진구", "동래구", "남구", "북구",
    "해운대구", "사하구", "금정구", "강서구", "연제구", "수영구", "사상구", "기장군",
)
DEFAULT_OUTPUT_ROOT = Path("data/raw/public_data_portal/city_parks/current")
DEFAULT_MANIFEST = Path("docs/data/manifests/CITY_PARKS_MANIFEST.json")
CUTOFF = date(2025, 12, 31)


def cutoff_status(value: object) -> str:
    """Classify designation dates without pretending a current register is a snapshot."""
    text = str(value or "").strip().replace("-", "")
    if not text:
        return "unverified_designation_date"
    try:
        designation = datetime.strptime(text[:8], "%Y%m%d").date()
    except ValueError:
        return "unverified_designation_date"
    return "eligible_by_designation_date" if designation <= CUTOFF else "post_cutoff_designation"


def collect(
    api_key: str,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    manifest_path: Path = DEFAULT_MANIFEST,
    *,
    fetcher: Callable[[str], bytes] = retry_fetch,
    reuse_existing: bool = True,
) -> dict[str, object]:
    raw_dir = output_root / "raw"
    collected: list[dict[str, object]] = []
    raw_paths: list[Path] = []
    for number, district in enumerate(DISTRICTS, start=1):
        provider = f"부산광역시 {district}"
        page_no = 1
        while True:
            raw_path = raw_dir / f"{number:02d}_{page_no:03d}.json"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            if reuse_existing and raw_path.exists():
                payload = raw_path.read_bytes()
            else:
                payload = fetcher(build_url(api_key, provider, page_no=page_no))
                raw_path.write_bytes(payload)
            rows, total = response_rows(payload)
            raw_paths.append(raw_path)
            for row in rows:
                item = dict(row)
                item["requested_provider"] = provider
                item["cutoff_status"] = cutoff_status(item.get("appnNtfcDate"))
                collected.append(item)
            if page_no * 1000 >= total:
                break
            page_no += 1

    if not collected:
        raise ValueError("City-park API returned no Busan records")
    unique: dict[str, dict[str, object]] = {}
    for index, row in enumerate(collected):
        key = str(row.get("manageNo") or f"missing-{index}")
        unique.setdefault(key, row)
    rows = list(unique.values())
    if any("부산" not in str(row.get("insttNm", "")) for row in rows):
        raise ValueError("City-park API response contains a non-Busan provider")

    csv_path = output_root / "busan_city_parks_current.csv"
    write_csv(csv_path, rows)
    missing_coordinates = sum(
        1
        for row in rows
        if not _finite(row.get("latitude")) or not _finite(row.get("longitude"))
    )
    status_counts = {
        status: sum(row["cutoff_status"] == status for row in rows)
        for status in (
            "eligible_by_designation_date",
            "post_cutoff_designation",
            "unverified_designation_date",
        )
    }
    manifest: dict[str, object] = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "dataset_id": "ENV-CITY-PARK-001",
        "provider": "Local governments via Public Data Portal",
        "source_page": SOURCE_PAGE,
        "source_attribution": "Source: Public Data Portal, city-park standard data",
        "access_method": "authenticated Public Data Portal Open API",
        "reference_period": "current register at retrieval time",
        "analysis_cutoff": CUTOFF.isoformat(),
        "analysis_role": "validation",
        "eligible_for_primary_analysis": False,
        "limitations": (
            "The API exposes a current register rather than a preserved 2025-12-31 snapshot. "
            "Designation date can exclude explicit post-cutoff parks but cannot prove that an "
            "older park was still operating at the cutoff. Use only as accessibility context."
        ),
        "record_count": len(rows),
        "duplicate_records_removed": len(collected) - len(rows),
        "missing_coordinate_records": missing_coordinates,
        "cutoff_status_counts": status_counts,
        "csv_path": csv_path.as_posix(),
        "csv_sha256": sha256_file(csv_path),
        "raw_directory": raw_dir.as_posix(),
        "raw_aggregate_sha256": aggregate_sha256(raw_paths, raw_dir),
    }
    ensure_secret_free(manifest)
    write_json(manifest_path, manifest)
    write_json(output_root / "manifest.json", manifest)
    return manifest


def _finite(value: object) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    values = read_env_file(args.env_file)
    require_values(values, ("DATA_GO_KR_SERVICE_KEY",), args.env_file)
    collect(
        values["DATA_GO_KR_SERVICE_KEY"],
        args.output_root,
        args.manifest,
        reuse_existing=not args.refresh,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
