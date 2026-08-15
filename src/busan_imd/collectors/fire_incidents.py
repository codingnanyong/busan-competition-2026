"""Collect 2025 Busan fire-station daily summaries from the National Fire Agency."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from busan_imd.core.artifacts import aggregate_sha256, sha256_file, write_csv, write_json
from busan_imd.core.config import read_env_file, require_values
from busan_imd.core.http import retry_fetch
from busan_imd.core.provenance import PRIMARY_REFERENCE_YEAR, ensure_secret_free
from busan_imd.sources.fire_information import SOURCE_PAGE, build_url, busan_rows, response_rows

DEFAULT_OUTPUT_ROOT = Path("data/raw/public_data_portal/fire/2025")
DEFAULT_MANIFEST_PATH = Path("docs/data/manifests/FIRE_SUMMARY_MANIFEST_2025.json")
DEFAULT_START = date(2025, 1, 1)
DEFAULT_END = date(2025, 12, 31)


def date_range(start: date, end: date) -> Iterator[date]:
    """Yield an inclusive date range."""
    if end < start:
        raise ValueError("end date must be on or after start date")
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def collect(
    api_key: str,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    *,
    start: date = DEFAULT_START,
    end: date = DEFAULT_END,
    fetcher: Callable[[str], bytes] = retry_fetch,
    reuse_existing: bool = True,
) -> dict[str, object]:
    """Retain daily national responses and write a Busan-only normalized CSV."""
    raw_dir = output_root / "raw"
    all_rows: list[dict[str, object]] = []
    raw_paths: list[Path] = []
    national_record_count = 0
    for occurrence_date in date_range(start, end):
        compact_date = occurrence_date.strftime("%Y%m%d")
        raw_path = raw_dir / f"{compact_date}.json"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        if reuse_existing and raw_path.exists():
            payload = raw_path.read_bytes()
        else:
            payload = fetcher(build_url(api_key, compact_date))
            raw_path.write_bytes(payload)
        rows, total_count = response_rows(payload)
        raw_paths.append(raw_path)
        national_record_count += total_count
        all_rows.extend(busan_rows(rows))

    if not all_rows:
        raise ValueError("The fire API returned no Busan rows for the requested period")
    csv_path = output_root / f"busan_fire_station_daily_{start:%Y%m%d}_{end:%Y%m%d}.csv"
    write_csv(csv_path, all_rows)
    retrieved_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    manifest: dict[str, object] = {
        "schema_version": 1,
        "generated_at": retrieved_at,
        "analysis_cutoff": "2026-07-31",
        "primary_reference_year": PRIMARY_REFERENCE_YEAR,
        "dataset_id": "SAF-NFA-FIRE-SUMMARY-001",
        "provider": "National Fire Agency, Republic of Korea",
        "source_page": SOURCE_PAGE,
        "source_attribution": "Source: National Fire Agency National Fire Information Open API",
        "access_method": "authenticated Public Data Portal Open API",
        "reference_period": f"{start.isoformat()}/{end.isoformat()}",
        "period_type": "annual" if (start, end) == (DEFAULT_START, DEFAULT_END) else "partial_year",
        "analysis_role": "validation",
        "eligible_for_primary_analysis": False,
        "spatial_unit": "fire station",
        "limitations": (
            "Daily station summaries do not contain incident addresses or administrative-dong "
            "codes, so they validate the safety domain but cannot directly score 206 dongs."
        ),
        "request_count": len(raw_paths),
        "national_record_count": national_record_count,
        "record_count": len(all_rows),
        "station_count": len({str(row["fire_station"]) for row in all_rows}),
        "csv_path": csv_path.as_posix(),
        "csv_sha256": sha256_file(csv_path),
        "raw_directory": raw_dir.as_posix(),
        "raw_aggregate_sha256": aggregate_sha256(raw_paths, raw_dir),
    }
    validate_manifest(manifest, Path("."))
    write_json(manifest_path, manifest)
    write_json(output_root / "manifest.json", manifest)
    return manifest


def validate_manifest(manifest: dict[str, object], root: Path = Path(".")) -> None:
    """Validate period, source limitations, file integrity, and credential hygiene."""
    ensure_secret_free(manifest)
    if manifest.get("primary_reference_year") != PRIMARY_REFERENCE_YEAR:
        raise ValueError("Fire manifest has the wrong primary reference year")
    if manifest.get("analysis_role") != "validation":
        raise ValueError("Station-level fire summaries must remain validation-only")
    if manifest.get("eligible_for_primary_analysis") is not False:
        raise ValueError("Station-level fire summaries cannot directly score admin dongs")
    csv_path = root / str(manifest["csv_path"])
    if csv_path.exists() and sha256_file(csv_path) != manifest["csv_sha256"]:
        raise ValueError(f"Fire CSV checksum mismatch: {csv_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--start", type=date.fromisoformat, default=DEFAULT_START)
    parser.add_argument("--end", type=date.fromisoformat, default=DEFAULT_END)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    config = read_env_file(args.env_file)
    require_values(config, ("DATA_GO_KR_SERVICE_KEY",), args.env_file)
    manifest = collect(
        config["DATA_GO_KR_SERVICE_KEY"],
        args.output_root,
        args.manifest,
        start=args.start,
        end=args.end,
        reuse_existing=not args.refresh,
    )
    print(
        "collected fire station daily summaries: "
        f"{manifest['record_count']} rows from {manifest['request_count']} dates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
