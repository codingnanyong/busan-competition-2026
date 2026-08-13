"""Collect Busan hospital, clinic, and pharmacy licences from the Public Data Portal."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from busan_imd.core.artifacts import (
    aggregate_sha256,
    sha256_file,
    write_csv,
    write_json,
)
from busan_imd.core.config import read_env_file, require_values
from busan_imd.core.http import retry_fetch
from busan_imd.core.provenance import (
    PRIMARY_REFERENCE_END,
    PRIMARY_REFERENCE_YEAR,
    ensure_secret_free,
)
from busan_imd.sources.local_licenses import (
    CLINIC_ENDPOINT,
    CLINIC_SOURCE,
    HOSPITAL_ENDPOINT,
    HOSPITAL_SOURCE,
    PHARMACY_ENDPOINT,
    PHARMACY_SOURCE,
    build_url,
    response_rows,
)

sha256 = sha256_file

DEFAULT_OUTPUT_ROOT = Path("data/raw/public_data_portal/healthcare_facilities")
DEFAULT_MANIFEST_PATH = Path("docs/data/manifests/HEALTHCARE_FACILITY_MANIFEST_2025.json")
REFERENCE_DATE = PRIMARY_REFERENCE_END.strftime("%Y%m%d")

fetch_with_retries = retry_fetch


def compact_date(value: object) -> str:
    """Return the first YYYYMMDD digits from a portal date value."""
    digits = "".join(character for character in str(value or "") if character.isdigit())
    return digits[:8] if len(digits) >= 8 else ""


def was_operating_on(row: dict[str, Any], reference_date: str = REFERENCE_DATE) -> bool:
    """Approximate whether a licence represented an operating facility on a date."""
    licensed = compact_date(row.get("LCPMT_YMD"))
    closed = compact_date(row.get("CLSBIZ_YMD"))
    revoked = compact_date(row.get("LCPMT_RTRCN_YMD"))
    temporary_start = compact_date(row.get("TCBIZ_BGNG_YMD"))
    temporary_end = compact_date(row.get("TCBIZ_END_YMD"))
    if not licensed or licensed > reference_date:
        return False
    if closed and closed <= reference_date:
        return False
    if revoked and revoked <= reference_date:
        return False
    temporarily_closed = temporary_start and temporary_start <= reference_date
    if temporarily_closed and (not temporary_end or temporary_end >= reference_date):
        return False
    return True


def collect_one(
    *,
    dataset_id: str,
    name: str,
    endpoint: str,
    source_page: str,
    service_key: str,
    output_root: Path,
    fetcher: Callable[[str], bytes] = fetch_with_retries,
    reuse_existing: bool = True,
) -> dict[str, object]:
    """Collect a Busan facility register and derive a 2025-12-31 candidate snapshot."""
    directory = output_root / dataset_id
    raw_directory = directory / "raw"
    parameters = {
        "pageNo": "1",
        "numOfRows": "100",
        "returnType": "json",
        "cond[ROAD_NM_ADDR::LIKE]": "부산광역시",
    }
    rows: list[dict[str, Any]] = []
    raw_paths: list[Path] = []
    total = 0
    page = 1
    while page == 1 or len(rows) < total:
        page_parameters = {**parameters, "pageNo": str(page)}
        raw_path = raw_directory / f"page_{page:04d}.json"
        if reuse_existing and raw_path.exists():
            payload = raw_path.read_bytes()
        else:
            payload = fetcher(build_url(endpoint, service_key, page_parameters))
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(payload)
        page_rows, page_total = response_rows(payload)
        if page == 1:
            total = page_total
        elif page_total != total:
            raise ValueError(f"{name} total count changed during pagination")
        if not page_rows and len(rows) < total:
            raise ValueError(f"{name} page {page} was empty before reaching {total} rows")
        rows.extend(page_rows)
        raw_paths.append(raw_path)
        page += 1
    if len(rows) != total:
        raise ValueError(f"Expected {total} {name} rows, received {len(rows)}")
    if any(
        "부산" not in str(row.get("ROAD_NM_ADDR") or row.get("LOTNO_ADDR") or "")
        for row in rows
    ):
        raise ValueError(f"{name} response contains a non-Busan address")

    eligible_rows = [row for row in rows if was_operating_on(row)]
    identifiers = [str(row.get("MNG_NO", "")).strip() for row in eligible_rows]
    has_duplicate_identifier = len(identifiers) != len(set(identifiers))
    if any(not identifier for identifier in identifiers) or has_duplicate_identifier:
        raise ValueError(f"{name} candidate identifiers are blank or duplicated")
    csv_path = directory / f"busan_{name}_operating_2025_12_31.csv"
    write_csv(csv_path, eligible_rows)
    coordinate_rows = [
        row for row in eligible_rows if row.get("CRD_INFO_X") and row.get("CRD_INFO_Y")
    ]
    return {
        "dataset_id": dataset_id,
        "provider": "Ministry of the Interior and Safety",
        "source_page": source_page,
        "endpoint": endpoint,
        "access_method": "Public Data Portal service key",
        "request_parameters": {
            "pageNo": "1",
            "numOfRows": "100",
            "returnType": "json",
            "address_filter": "Busan Metropolitan City",
        },
        "retrieved_snapshot_record_count": total,
        "raw_file_count": len(raw_paths),
        "raw_paths": [path.as_posix() for path in raw_paths],
        "raw_files_aggregate_sha256": aggregate_sha256(raw_paths, output_root),
        "reference_period": PRIMARY_REFERENCE_END.isoformat(),
        "primary_reference_year": PRIMARY_REFERENCE_YEAR,
        "analysis_role": "primary_candidate_reconstructed",
        "eligible_for_primary_analysis": False,
        "period_type": "reconstructed_snapshot",
        "record_count": len(eligible_rows),
        "coordinate_record_count": len(coordinate_rows),
        "coordinate_missing_count": len(eligible_rows) - len(coordinate_rows),
        "source_crs": "EPSG:5174",
        "csv_path": csv_path.as_posix(),
        "csv_sha256": sha256(csv_path),
        "licence": "No restriction",
        "notes": (
            "Candidate 2025-12-31 snapshot reconstructed from current licence, closure, "
            "revocation, and temporary-closure dates. It remains outside the primary score "
            "until historical completeness and coordinate conversion are validated."
        ),
    }


def validate_manifest(manifest: dict[str, object], root: Path = Path(".")) -> None:
    """Validate dataset coverage, checksums, reference year, and secret absence."""
    ensure_secret_free(manifest)
    if manifest.get("primary_reference_year") != PRIMARY_REFERENCE_YEAR:
        raise ValueError("Healthcare manifest has the wrong primary reference year")
    datasets = manifest.get("datasets")
    if not isinstance(datasets, list) or len(datasets) != 3:
        raise ValueError("Healthcare manifest must contain hospital, clinic, and pharmacy datasets")
    for dataset in datasets:
        if not dataset["retrieved_snapshot_record_count"] or not dataset["record_count"]:
            raise ValueError("Healthcare dataset is empty")
        csv_path = root / dataset["csv_path"]
        if csv_path.exists() and sha256(csv_path) != dataset["csv_sha256"]:
            raise ValueError(f"Healthcare checksum mismatch: {csv_path}")
        raw_paths = [root / path for path in dataset["raw_paths"]]
        existing_raw_paths = [path for path in raw_paths if path.exists()]
        if existing_raw_paths:
            raw_root = existing_raw_paths[0].parents[2]
            checksum = aggregate_sha256(existing_raw_paths, raw_root)
            if checksum != dataset["raw_files_aggregate_sha256"]:
                raise ValueError("Healthcare raw response checksum mismatch")


def collect(
    service_key: str,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    fetcher: Callable[[str], bytes] = fetch_with_retries,
    reuse_existing: bool = True,
) -> dict[str, object]:
    """Collect the three migrated MOIS facility services and write provenance."""
    datasets = [
        collect_one(
            dataset_id="HLT-HOSPITAL-001",
            name="hospitals",
            endpoint=HOSPITAL_ENDPOINT,
            source_page=HOSPITAL_SOURCE,
            service_key=service_key,
            output_root=output_root,
            fetcher=fetcher,
            reuse_existing=reuse_existing,
        ),
        collect_one(
            dataset_id="HLT-CLINIC-001",
            name="clinics",
            endpoint=CLINIC_ENDPOINT,
            source_page=CLINIC_SOURCE,
            service_key=service_key,
            output_root=output_root,
            fetcher=fetcher,
            reuse_existing=reuse_existing,
        ),
        collect_one(
            dataset_id="HLT-PHARMACY-001",
            name="pharmacies",
            endpoint=PHARMACY_ENDPOINT,
            source_page=PHARMACY_SOURCE,
            service_key=service_key,
            output_root=output_root,
            fetcher=fetcher,
            reuse_existing=reuse_existing,
        ),
    ]
    manifest: dict[str, object] = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "analysis_cutoff": "2026-07-31",
        "primary_reference_year": PRIMARY_REFERENCE_YEAR,
        "dataset_count": len(datasets),
        "datasets": datasets,
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
    parser.add_argument(
        "--refresh", action="store_true", help="Fetch again instead of reusing raw responses"
    )
    args = parser.parse_args()
    config = read_env_file(args.env_file)
    require_values(config, ("DATA_GO_KR_SERVICE_KEY",), args.env_file)
    manifest = collect(
        config["DATA_GO_KR_SERVICE_KEY"],
        args.output_root,
        args.manifest,
        reuse_existing=not args.refresh,
    )
    counts = [dataset["record_count"] for dataset in manifest["datasets"]]
    print(
        "collected reconstructed 2025 hospital/clinic/pharmacy rows: "
        f"{counts[0]}/{counts[1]}/{counts[2]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
