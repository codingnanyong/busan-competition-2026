"""Collect Busan traffic-accident statistics from the KOROAD Open API."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from busan_imd.core.artifacts import sha256_file as sha256
from busan_imd.core.artifacts import write_csv, write_json
from busan_imd.core.config import read_env_file, require_values
from busan_imd.core.http import retry_fetch
from busan_imd.core.provenance import PRIMARY_REFERENCE_YEAR, ensure_secret_free
from busan_imd.sources.koroad import (
    HOTSPOT_DISTRICTS,
    HOTSPOT_ENDPOINT,
    HOTSPOT_SOURCE,
    STATISTICS_DISTRICTS,
    STATISTICS_ENDPOINT,
    STATISTICS_SOURCE,
    build_url,
    response_rows,
)

DEFAULT_OUTPUT_ROOT = Path("data/raw/koroad/traffic_accidents")
DEFAULT_MANIFEST_PATH = Path("docs/data/manifests/KOROAD_TRAFFIC_ACCIDENT_MANIFEST.json")

fetch_with_retries = retry_fetch


def collect_dataset(
    *,
    api_key: str,
    endpoint: str,
    year: int,
    sido: str,
    districts: tuple[str, ...],
    output_dir: Path,
    fetcher: Callable[[str], bytes] = fetch_with_retries,
    reuse_existing: bool = True,
) -> tuple[list[dict[str, str]], list[Path]]:
    """Collect one response for every Busan district and retain raw JSON."""
    all_rows: list[dict[str, str]] = []
    raw_paths: list[Path] = []
    for district in districts:
        parameters = {
            "searchYearCd": str(year),
            "siDo": sido,
            "guGun": district,
            "type": "json",
            "numOfRows": "100",
            "pageNo": "1",
        }
        raw_path = output_dir / "raw" / f"{district}.json"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        if reuse_existing and raw_path.exists():
            payload = raw_path.read_bytes()
        else:
            payload = fetcher(build_url(endpoint, api_key, parameters))
            raw_path.write_bytes(payload)
        rows = response_rows(payload)
        raw_paths.append(raw_path)
        all_rows.extend(rows)
    return all_rows, raw_paths


def validate_manifest(manifest: dict[str, object], root: Path = Path(".")) -> None:
    """Validate coverage, checksums, cutoff, and absence of credentials."""
    ensure_secret_free(manifest)
    if manifest.get("analysis_cutoff") != "2026-07-31":
        raise ValueError("KOROAD manifest has the wrong analysis cutoff")
    if manifest.get("primary_reference_year") != PRIMARY_REFERENCE_YEAR:
        raise ValueError("KOROAD manifest has the wrong primary reference year")
    datasets = manifest.get("datasets")
    if not isinstance(datasets, list) or len(datasets) != 2:
        raise ValueError("KOROAD manifest must contain statistics and hotspot datasets")
    for dataset in datasets:
        if dataset["district_count"] != 16:
            raise ValueError("KOROAD dataset does not cover all 16 Busan districts")
        if not dataset["record_count"]:
            raise ValueError("KOROAD dataset has no records")
        if len(dataset["raw_files"]) != 16:
            raise ValueError("KOROAD dataset must retain 16 raw responses")
        csv_path = root / dataset["csv_path"]
        if csv_path.exists() and sha256(csv_path) != dataset["csv_sha256"]:
            raise ValueError(f"KOROAD CSV checksum mismatch: {csv_path}")


def collect(
    api_key: str,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    fetcher: Callable[[str], bytes] = fetch_with_retries,
    reuse_existing: bool = True,
) -> dict[str, object]:
    """Collect the latest cutoff-eligible statistics and hotspot context for Busan."""
    retrieved_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    statistics_dir = output_root / "statistics/2025"
    statistics, statistics_raw = collect_dataset(
        api_key=api_key,
        endpoint=STATISTICS_ENDPOINT,
        year=2025,
        sido="1200",
        districts=STATISTICS_DISTRICTS,
        output_dir=statistics_dir,
        fetcher=fetcher,
        reuse_existing=reuse_existing,
    )
    statistics_regions = {row["sido_sgg_nm"] for row in statistics}
    if len(statistics_regions) != 16:
        raise ValueError(f"Expected 16 statistics regions, received {len(statistics_regions)}")
    statistics_csv = statistics_dir / "busan_traffic_accident_statistics_2025.csv"
    write_csv(statistics_csv, statistics)

    hotspots_dir = output_root / "hotspots/2024"
    hotspots, hotspots_raw = collect_dataset(
        api_key=api_key,
        endpoint=HOTSPOT_ENDPOINT,
        year=2024,
        sido="26",
        districts=HOTSPOT_DISTRICTS,
        output_dir=hotspots_dir,
        fetcher=fetcher,
        reuse_existing=reuse_existing,
    )
    hotspot_regions = {row["sido_sgg_nm"].rstrip("123") for row in hotspots}
    if len(hotspot_regions) != 16:
        raise ValueError(f"Expected 16 hotspot regions, received {len(hotspot_regions)}")
    hotspots_csv = hotspots_dir / "busan_traffic_accident_hotspots_2024.csv"
    write_csv(hotspots_csv, hotspots)

    manifest: dict[str, object] = {
        "schema_version": 1,
        "generated_at": retrieved_at,
        "analysis_cutoff": "2026-07-31",
        "primary_reference_year": PRIMARY_REFERENCE_YEAR,
        "provider": "Korea Road Traffic Authority (KOROAD), TAAS",
        "source_attribution": (
            "Source: Korea Road Traffic Authority Traffic Accident Analysis System (TAAS)"
        ),
        "datasets": [
            {
                "dataset_id": "SAF-KOROAD-STT-001",
                "source_page": STATISTICS_SOURCE,
                "endpoint": STATISTICS_ENDPOINT,
                "access_method": "authenticated KOROAD Open API",
                "request_parameters": {
                    "searchYearCd": "2025",
                    "siDo": "1200",
                    "guGun": "1201..1216",
                    "type": "json",
                },
                "reference_period": "2025",
                "analysis_role": "primary",
                "lag_years": 0,
                "period_type": "annual",
                "cutoff_status": "eligible",
                "spatial_unit": "Busan district (gu/gun)",
                "district_count": len(statistics_regions),
                "record_count": len(statistics),
                "csv_path": statistics_csv.as_posix(),
                "csv_sha256": sha256(statistics_csv),
                "raw_files": [path.as_posix() for path in statistics_raw],
                "notes": (
                    "District-level validation/context data; it cannot directly produce a "
                    "206-administrative-dong indicator."
                ),
            },
            {
                "dataset_id": "SAF-KOROAD-HOTSPOT-001",
                "source_page": HOTSPOT_SOURCE,
                "endpoint": HOTSPOT_ENDPOINT,
                "access_method": "authenticated KOROAD Open API",
                "request_parameters": {
                    "searchYearCd": "2024",
                    "siDo": "26",
                    "guGun": list(HOTSPOT_DISTRICTS),
                    "type": "json",
                },
                "reference_period": "2024",
                "analysis_role": "fallback_validation",
                "lag_years": 1,
                "period_type": "annual",
                "cutoff_status": "eligible",
                "spatial_unit": "selected hotspot polygons and points",
                "district_count": len(hotspot_regions),
                "record_count": len(hotspots),
                "csv_path": hotspots_csv.as_posix(),
                "csv_sha256": sha256(hotspots_csv),
                "raw_files": [path.as_posix() for path in hotspots_raw],
                "crs": "EPSG:4326",
                "notes": (
                    "Only the top three locations per municipality with at least three crashes "
                    "within 150 m; validation and map context only, not a complete crash census."
                ),
            },
        ],
    }
    validate_manifest(manifest)
    write_json(manifest_path, manifest)
    local_manifest = output_root / "manifest.json"
    write_json(local_manifest, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument(
        "--refresh", action="store_true", help="Fetch again instead of reusing raw responses"
    )
    args = parser.parse_args()
    config = read_env_file(args.env_file)
    require_values(config, ("KOROAD_API_KEY",), args.env_file)
    api_key = config["KOROAD_API_KEY"]
    manifest = collect(api_key, args.output_root, args.manifest, reuse_existing=not args.refresh)
    counts = [dataset["record_count"] for dataset in manifest["datasets"]]
    print(f"collected KOROAD statistics/hotspots rows: {counts[0]}/{counts[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
