"""Collect approved raw API sources and build a provenance manifest."""

from __future__ import annotations

import argparse
import csv
import json
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from busan_imd.core.artifacts import sha256_file as sha256
from busan_imd.core.artifacts import write_json
from busan_imd.core.config import read_env_file, require_values
from busan_imd.core.http import encoded_secret_url, fetch_bytes
from busan_imd.core.provenance import (
    ANALYSIS_CUTOFF,
    PRIMARY_REFERENCE_YEAR,
    cutoff_status,
    ensure_secret_free,
)
from busan_imd.data_catalog import read_catalog
from busan_imd.sources.sgis import authenticate

CUTOFF = ANALYSIS_CUTOFF
COLLECTION_ROOT = Path("data/raw/collection")
AUDIT_ROOT = Path("data/raw/audit")
CATALOG_PATH = Path("docs/data/DATASET_AUDIT.csv")
MANIFEST_PATH = Path("docs/data/manifests/RAW_DATA_MANIFEST.json")
PORTAL_ID_PATTERN = re.compile(r"data\.go\.kr/data/(\d+)/fileData\.do")

API_SOURCES = {
    "EMP-SGIS-001": {
        "provider": "Statistics Korea SGIS",
        "source_url": "https://sgis.mods.go.kr/developer/html/newOpenApi/api/dataApi/census.html",
        "endpoint": "https://sgisapi.mods.go.kr/OpenAPI3/stats/company.json",
        "reference_period": "2024-12-31",
        "period_type": "annual",
        "license": "SGIS API terms; verify derivative redistribution before publishing raw data",
        "format": "json",
    },
    "HOU-BUSSTOP-API-001": {
        "provider": "Busan Metropolitan City",
        "source_url": "https://www.data.go.kr/data/15092750/openapi.do",
        "endpoint": "https://apis.data.go.kr/6260000/BusanBIMS/busStopList",
        "reference_period": "current inventory; record-level observation date unavailable",
        "period_type": "snapshot",
        "license": "no restriction",
        "format": "xml",
    },
    "HLT-AED-001": {
        "provider": "Busan Metropolitan City",
        "source_url": "https://www.data.go.kr/data/15095264/openapi.do",
        "endpoint": "https://apis.data.go.kr/6260000/BusanAedsService/getAedsList",
        "reference_period": "current inventory; record-level observation date unavailable",
        "period_type": "snapshot",
        "license": "no restriction",
        "format": "json",
    },
    "ENV-AIR-REALTIME-001": {
        "provider": "Busan Metropolitan City",
        "source_url": "https://www.data.go.kr/data/15057173/openapi.do",
        "endpoint": (
            "https://apis.data.go.kr/6260000/AirQualityInfoService/"
            "getAirQualityInfoClassifiedByStation"
        ),
        "reference_period": "derived from controlnumber in response",
        "period_type": "realtime_snapshot",
        "license": "no restriction",
        "format": "json",
    },
}

def public_portal_url(endpoint: str, service_key: str, result_type: str) -> str:
    """Build a portal URL without double-encoding its already encoded service key."""
    parameters = {"pageNo": "1", "numOfRows": "10000"}
    if result_type == "json":
        parameters["resultType"] = "json"
    return encoded_secret_url(endpoint, "serviceKey", service_key, parameters)


def json_summary(payload: bytes) -> tuple[int, dict[str, Any]]:
    """Validate a Public Data Portal JSON response and summarize its records."""
    document = json.loads(payload)
    response = document["response"]
    header = response.get("header", {})
    if str(header.get("resultCode", "00")) != "00":
        raise ValueError(f"Public Data Portal error: {header}")
    body = response["body"]
    items = body.get("items", {}).get("item", [])
    if isinstance(items, dict):
        items = [items]
    total_count = int(body["totalCount"])
    if len(items) != total_count:
        raise ValueError(f"Expected {total_count} JSON items, received {len(items)}")
    return total_count, {"items": items}


def xml_summary(payload: bytes) -> tuple[int, dict[str, Any]]:
    """Validate a Public Data Portal XML response and summarize its records."""
    root = ET.fromstring(payload)
    result_code = root.findtext("./header/resultCode")
    if result_code != "00":
        raise ValueError(f"Public Data Portal error code: {result_code}")
    total_count = int(root.findtext("./body/totalCount", "0"))
    items = root.findall("./body/items/item")
    if len(items) != total_count:
        raise ValueError(f"Expected {total_count} XML items, received {len(items)}")
    return total_count, {}

def direct_download_entries(catalog_path: Path, audit_root: Path) -> list[dict[str, Any]]:
    """Verify and describe the direct downloads already present locally."""
    entries: list[dict[str, Any]] = []
    for row in read_catalog(catalog_path):
        match = PORTAL_ID_PATTERN.search(row["source_url"])
        if not match or row["checksum"] == "not_collected":
            continue
        path = audit_root / f"{match.group(1)}.download"
        if not path.exists():
            raise FileNotFoundError(f"Missing audited raw file: {path}")
        digest = sha256(path)
        if digest != row["checksum"]:
            raise ValueError(f"Checksum mismatch: {path}")
        entries.append(
            {
                "dataset_id": row["dataset_id"],
                "provider": row["provider"],
                "source_url": row["source_url"],
                "endpoint": None,
                "access_method": "public direct download",
                "reference_period": row["reference_period"],
                "period_type": row["update_cycle"],
                "retrieved_at": row["collected_at"],
                "cutoff_status": cutoff_status(row["reference_period"]),
                "license": row["license"],
                "local_path": path.as_posix(),
                "bytes": path.stat().st_size,
                "sha256": digest,
                "record_count": csv_record_count(path),
                "notes": row["notes"],
            }
        )
    return entries


def csv_record_count(path: Path) -> int:
    """Count data records in a downloaded CSV using common Korean encodings."""
    for encoding in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            with path.open(encoding=encoding, newline="") as stream:
                return max(sum(1 for _ in csv.reader(stream)) - 1, 0)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Unsupported CSV encoding: {path}")


def collect_sgis_company(
    consumer_key: str, consumer_secret: str, output_root: Path, retrieved_at: str
) -> dict[str, Any]:
    """Collect the latest available Busan SGIS workplace statistics."""
    source = API_SOURCES["EMP-SGIS-001"]
    access_token = authenticate(consumer_key, consumer_secret)
    parameters = {"year": "2024", "adm_cd": "21", "low_search": "2"}
    url = f"{source['endpoint']}?{urlencode({**parameters, 'accessToken': access_token})}"
    payload = fetch_bytes(url)
    document = json.loads(payload)
    if document.get("errCd") != 0:
        raise ValueError(f"SGIS company API error: {document.get('errMsg')}")
    rows = document.get("result", [])
    codes = {str(row.get("adm_cd", "")) for row in rows}
    if len(rows) != 206 or len(codes) != 206:
        raise ValueError(f"Expected 206 unique SGIS dong rows, received {len(rows)}/{len(codes)}")
    path = output_root / "EMP-SGIS-001" / "sgis_company_2024.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return api_entry(
        "EMP-SGIS-001", path, retrieved_at, len(rows), "eligible", parameters, source
    )


def api_entry(
    dataset_id: str,
    path: Path,
    retrieved_at: str,
    record_count: int,
    status: str,
    parameters: dict[str, str],
    source: dict[str, Any],
    *,
    reference_period: str | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Build one secret-free API provenance entry."""
    return {
        "dataset_id": dataset_id,
        "provider": source["provider"],
        "source_url": source["source_url"],
        "endpoint": source["endpoint"],
        "access_method": "authenticated OpenAPI",
        "request_parameters": parameters,
        "reference_period": reference_period or source["reference_period"],
        "period_type": source["period_type"],
        "retrieved_at": retrieved_at,
        "cutoff_status": status,
        "license": source["license"],
        "local_path": path.as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "record_count": record_count,
        "notes": notes,
    }


def collect_portal_api(
    dataset_id: str, service_key: str, output_root: Path, retrieved_at: str
) -> dict[str, Any]:
    """Collect and validate one Public Data Portal API in a single full page."""
    source = API_SOURCES[dataset_id]
    result_type = str(source["format"])
    url = public_portal_url(str(source["endpoint"]), service_key, result_type)
    payload = fetch_bytes(url)
    if result_type == "json":
        count, summary = json_summary(payload)
    else:
        count, summary = xml_summary(payload)
    path = output_root / dataset_id / f"response.{result_type}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)

    reference_period = str(source["reference_period"])
    status = "unverified"
    notes = "Record-level observation date is unavailable; do not score until cutoff is verified."
    if dataset_id == "ENV-AIR-REALTIME-001":
        controls = sorted(
            str(item["controlnumber"])
            for item in summary["items"]
            if item.get("controlnumber")
        )
        if not controls:
            raise ValueError("Air-quality response has no controlnumber")
        busan_timezone = ZoneInfo("Asia/Seoul")
        first = datetime.strptime(controls[0], "%Y%m%d%H").replace(tzinfo=busan_timezone)
        last = datetime.strptime(controls[-1], "%Y%m%d%H").replace(tzinfo=busan_timezone)
        reference_period = f"{first.isoformat()}/{last.isoformat()}"
        status = "eligible" if last.date() <= CUTOFF else "outside_cutoff"
        notes = "Real-time snapshot retained for provenance; excluded when outside the cutoff."

    return api_entry(
        dataset_id,
        path,
        retrieved_at,
        count,
        status,
        {"pageNo": "1", "numOfRows": "10000", "resultType": result_type},
        source,
        reference_period=reference_period,
        notes=notes,
    )


def validate_manifest(manifest: dict[str, Any], repository_root: Path = Path(".")) -> None:
    """Reject secrets, duplicate IDs, missing files, and checksum drift."""
    ensure_secret_free(manifest)
    if manifest.get("primary_reference_year") != PRIMARY_REFERENCE_YEAR:
        raise ValueError(f"Manifest primary reference year must be {PRIMARY_REFERENCE_YEAR}")
    entries = manifest.get("datasets", [])
    identifiers = [entry["dataset_id"] for entry in entries]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Manifest dataset IDs are not unique")
    for entry in entries:
        path = repository_root / entry["local_path"]
        if path.exists() and sha256(path) != entry["sha256"]:
            raise ValueError(f"Manifest checksum mismatch: {path}")


def write_manifest(entries: list[dict[str, Any]], path: Path, generated_at: str) -> None:
    """Write the versioned provenance manifest."""
    status_counts: dict[str, int] = {}
    for entry in entries:
        status = str(entry["cutoff_status"])
        status_counts[status] = status_counts.get(status, 0) + 1
    manifest = {
        "schema_version": 1,
        "generated_at": generated_at,
        "analysis_cutoff": CUTOFF.isoformat(),
        "primary_reference_year": PRIMARY_REFERENCE_YEAR,
        "dataset_count": len(entries),
        "cutoff_status_counts": status_counts,
        "datasets": sorted(entries, key=lambda entry: entry["dataset_id"]),
    }
    validate_manifest(manifest)
    write_json(path, manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    parser.add_argument("--audit-root", type=Path, default=AUDIT_ROOT)
    parser.add_argument("--output-root", type=Path, default=COLLECTION_ROOT)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    args = parser.parse_args()

    config = read_env_file(args.env_file)
    required = ("SGIS_CONSUMER_KEY", "SGIS_CONSUMER_SECRET", "DATA_GO_KR_SERVICE_KEY")
    require_values(config, required, args.env_file)

    retrieved_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    entries = direct_download_entries(args.catalog, args.audit_root)
    entries.append(
        collect_sgis_company(
            config["SGIS_CONSUMER_KEY"],
            config["SGIS_CONSUMER_SECRET"],
            args.output_root,
            retrieved_at,
        )
    )
    for dataset_id in ("HOU-BUSSTOP-API-001", "HLT-AED-001", "ENV-AIR-REALTIME-001"):
        entries.append(
            collect_portal_api(
                dataset_id, config["DATA_GO_KR_SERVICE_KEY"], args.output_root, retrieved_at
            )
        )
    write_manifest(entries, args.manifest, retrieved_at)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    write_json(args.output_root / "manifest.json", manifest)
    print(f"collected and verified {len(entries)} datasets; manifest: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
