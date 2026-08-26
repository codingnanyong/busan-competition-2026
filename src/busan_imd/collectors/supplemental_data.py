"""Collect supplemental Busan population, transport, and safety datasets."""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from busan_imd.core.artifacts import sha256_file, write_csv, write_json
from busan_imd.core.config import read_env_file, require_values
from busan_imd.core.http import encoded_secret_url, retry_fetch
from busan_imd.core.provenance import ensure_secret_free

OUTPUT_ROOT = Path("data/raw/supplemental")
MANIFEST_PATH = Path("docs/data/manifests/BUSAN_SUPPLEMENTAL_DATA_MANIFEST.json")
REFERENCE_PATH = Path("docs/data/tables/BUSAN_ADMIN_DONG_CODES_2025.csv")
ANALYSIS_CUTOFF = "2026-07-31"
DISTRICTS = (
    "중구",
    "서구",
    "동구",
    "영도구",
    "부산진구",
    "동래구",
    "남구",
    "북구",
    "해운대구",
    "사하구",
    "금정구",
    "강서구",
    "연제구",
    "수영구",
    "사상구",
    "기장군",
)

FILE_SOURCES: dict[str, dict[str, Any]] = {
    "INC-BLF-HAEUNDAE-2025-001": {
        "name": "Haeundae-gu basic-livelihood benefit recipients",
        "provider": "Haeundae-gu, Busan Metropolitan City",
        "source_page": "https://www.data.go.kr/data/3075567/fileData.do",
        "download_url": (
            "https://www.data.go.kr/cmm/cmm/fileDownload.do?"
            "atchFileId=FILE_000000003248813&fileDetailSn=1&insertDataPrcus=N"
        ),
        "path": "basic_livelihood/busan_haeundae_basic_livelihood_2025_08_20.csv",
        "format": "csv",
        "reference_period": "2025-08-20",
        "period_type": "snapshot",
        "analysis_role": "partial_coverage_income_validation",
        "spatial_unit": "administrative dong",
        "license": "no restriction",
        "notes": (
            "Contains 18 administrative-dong rows and one facility-total row. It expands "
            "income validation coverage but cannot enter the composite until all 16 districts "
            "share one date and benefit definition."
        ),
    },
    "INC-WELFARE-SIGUNGU-2025-001": {
        "name": "2025 welfare-program beneficiaries by district",
        "provider": "Korea Social Security Information Service",
        "source_page": "https://www.data.go.kr/data/15062448/fileData.do",
        "download_url": (
            "https://www.data.go.kr/cmm/cmm/fileDownload.do?"
            "atchFileId=FILE_000000003664131&fileDetailSn=1&insertDataPrcus=N"
        ),
        "path": "welfare_beneficiaries/welfare_beneficiaries_by_sigungu_2025.csv",
        "format": "csv",
        "reference_period": "2025-12",
        "period_type": "annual_snapshot",
        "analysis_role": "district_level_validation",
        "spatial_unit": "si-gun-gu",
        "license": "no restriction",
        "notes": (
            "Includes basic-livelihood and other welfare-program beneficiary and household "
            "counts. District totals cannot replace administrative-dong source data."
        ),
    },
    "SAF-BUSAN-CCTV-001": {
        "name": "Busan crime-prevention CCTV locations",
        "provider": "Busan Metropolitan City",
        "source_page": "https://www.data.go.kr/data/15082060/fileData.do",
        "download_url": (
            "https://www.data.go.kr/cmm/cmm/fileDownload.do?"
            "atchFileId=FILE_000000003578112&fileDetailSn=1&insertDataPrcus=N"
        ),
        "path": "crime_prevention_cctv/busan_crime_prevention_cctv_2025.csv",
        "format": "csv",
        "reference_period": "2025-12-29",
        "period_type": "facility_snapshot",
        "analysis_role": "supplemental_safety_service",
        "spatial_unit": "point location",
        "license": "no restriction",
        "notes": (
            "Measures installed prevention infrastructure, not crime incidence. Coordinates "
            "may support a dong-level service-density proxy after spatial validation."
        ),
    },
    "TRN-BUSAN-BOARDING-2023-001": {
        "name": "Busan bus boardings and alightings by route and stop",
        "provider": "Busan Metropolitan City",
        "source_page": "https://www.data.go.kr/data/15123610/fileData.do",
        "download_url": (
            "https://www.data.go.kr/cmm/cmm/fileDownload.do?"
            "atchFileId=FILE_000000002818223&fileDetailSn=1&insertDataPrcus=N"
        ),
        "path": "bus_boarding/busan_bus_boarding_alighting_2023.csv",
        "format": "csv",
        "reference_period": "2023-07-31",
        "period_type": "one_time_snapshot",
        "analysis_role": "historical_transport_validation",
        "spatial_unit": "route-stop",
        "license": "no restriction",
        "notes": (
            "Contains stop- and time-band boarding/alighting counts but is too old to be a "
            "2025 primary indicator."
        ),
    },
    "TRN-BUSAN-ROUTE-USAGE-2025-001": {
        "name": "2025 Busan city-bus and village-bus route usage",
        "provider": "Busan Metropolitan City",
        "source_page": "https://www.data.go.kr/data/15095329/fileData.do",
        "download_url": (
            "https://www.data.go.kr/cmm/cmm/fileDownload.do?"
            "atchFileId=FILE_000000003617805&fileDetailSn=1&insertDataPrcus=N"
        ),
        "path": "bus_route_usage/busan_bus_route_usage_2025.csv",
        "format": "csv",
        "reference_period": "2025-12-31",
        "period_type": "annual_route_total",
        "analysis_role": "supplemental_transport_demand",
        "spatial_unit": "bus route",
        "license": "no restriction",
        "notes": (
            "Contains 333 unique routes and passenger-type counts by transfer count. It is "
            "a demand measure, not actual service frequency or an administrative-dong measure."
        ),
    },
    "DEM-BUSAN-LIVING-001": {
        "name": "Busan monthly average daily living population by age and administrative dong",
        "provider": "Busan Metropolitan City",
        "source_page": (
            "https://data.busan.go.kr/bdip/opendata/detail.do?publicdatapk=PD_LP00002"
        ),
        "download_url": (
            "https://data.busan.go.kr/bdip/opendata/DATA_202411250501368790"
        ),
        "path": "living_population/busan_living_population_2023_2025.xlsx.download",
        "format": "xlsx",
        "reference_period": "2023-01-01/2025-12-31",
        "period_type": "monthly_average_daily_estimate",
        "analysis_role": "supplemental_service_demand",
        "spatial_unit": "administrative dong by 10-year age group",
        "license": "no restriction",
        "notes": (
            "Telecom-derived residential, workplace, and visitor population. It must not "
            "replace the resident-registration denominator. The downloaded workbook has "
            "44,340 rows for 2023-01 through 2025-12, rather than the portal page's stated "
            "50,294 rows for 2019 through 2025."
        ),
    },
    "SAF-BUSAN-POLICE-TREND-001": {
        "name": "Busan citywide traffic-accident trend",
        "provider": "Busan Metropolitan Police Agency",
        "source_page": "https://www.data.go.kr/data/15059681/fileData.do",
        "download_url": (
            "https://www.data.go.kr/cmm/cmm/fileDownload.do?"
            "atchFileId=FILE_000000003619334&fileDetailSn=1&insertDataPrcus=N"
        ),
        "path": "traffic_accident_citywide/busan_traffic_accident_trend_2007_2025.csv",
        "format": "csv",
        "reference_period": "2007-01-01/2025-12-31",
        "period_type": "annual_series",
        "analysis_role": "citywide_validation",
        "spatial_unit": "Busan city total",
        "license": "no restriction",
        "notes": "Citywide trend only; never allocate the totals to administrative dongs.",
    },
    "SAF-BUSAN-RISK-AREA-001": {
        "name": "Busan accident-risk areas",
        "provider": "Busan Metropolitan City",
        "source_page": "https://www.data.go.kr/data/15114119/fileData.do",
        "download_url": (
            "https://www.data.go.kr/cmm/cmm/fileDownload.do?"
            "atchFileId=FILE_000000002735989&fileDetailSn=1&insertDataPrcus=N"
        ),
        "path": "accident_risk_areas/busan_accident_risk_areas_2023.csv",
        "format": "csv",
        "reference_period": "2023-05-31",
        "period_type": "selected_risk_locations",
        "analysis_role": "fallback_spatial_validation",
        "spatial_unit": "selected point location",
        "license": "no restriction",
        "notes": "Selected risk locations, not a complete census of accidents or fire dispatches.",
    },
}

VILLAGE_BUS = {
    "dataset_id": "TRN-BUSAN-VILLAGE-BUS-001",
    "name": "Busan village-bus operating status",
    "provider": "Busan Metropolitan City",
    "source_page": "https://www.data.go.kr/data/15040508/openapi.do",
    "endpoint": "https://apis.data.go.kr/6260000/VillageBusService/VillageBusStusInfo",
    "path": "village_bus/busan_village_bus_status.json",
}

ELDERLY_ALONE = {
    "dataset_id": "SOC-BUSAN-ELDERLY-ALONE-001",
    "name": "Busan elderly people living alone by administrative dong",
    "provider": "Busan Metropolitan City",
    "source_page": "https://www.data.go.kr/data/15160011/openapi.do",
    "endpoint": "https://apis.data.go.kr/6260000/LaSeniorService/getLaSenior",
    "path": "elderly_alone/busan_elderly_alone_api_responses_2026.json",
    "csv_path": "elderly_alone/busan_elderly_alone_latest_by_admin_dong.csv",
}


def download(
    url: str,
    path: Path,
    fetcher: Callable[[str], bytes],
    *,
    reuse_existing: bool,
) -> bytes:
    """Download a source or reuse its preserved raw artifact."""
    if reuse_existing and path.exists():
        return path.read_bytes()
    payload = fetcher(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def csv_metadata(path: Path) -> tuple[int, list[str], str]:
    """Return row count, fields, and detected Korean CSV encoding."""
    for encoding in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            with path.open(encoding=encoding, newline="") as stream:
                reader = csv.reader(stream)
                rows = list(reader)
            if not rows:
                raise ValueError(f"CSV is empty: {path}")
            return len(rows) - 1, rows[0], encoding
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Unsupported CSV encoding: {path}")


def _xlsx_cell_value(cell: ET.Element, namespace: dict[str, str]) -> str:
    """Read either an inline-string or scalar XLSX cell."""
    inline_text = cell.findall(".//m:is/m:t", namespace)
    if inline_text:
        return "".join(node.text or "" for node in inline_text)
    value = cell.find("m:v", namespace)
    return "" if value is None else value.text or ""


def xlsx_metadata(path: Path) -> dict[str, Any]:
    """Inspect the living-population workbook without adding an Excel dependency."""
    if path.read_bytes()[:2] != b"PK":
        raise ValueError(f"XLSX does not have a ZIP signature: {path}")
    namespace = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    worksheet_rows: list[int] = []
    fields: list[str] = []
    months: set[str] = set()
    admin_codes: set[str] = set()
    age_groups: set[str] = set()
    with zipfile.ZipFile(path) as workbook:
        sheets = sorted(
            name
            for name in workbook.namelist()
            if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name)
        )
        if not sheets:
            raise ValueError(f"XLSX has no worksheets: {path}")
        for sheet in sheets:
            root = ET.fromstring(workbook.read(sheet))
            rows = root.findall(".//m:sheetData/m:row", namespace)
            worksheet_rows.append(max(len(rows) - 1, 0))
            if not fields and rows:
                fields = [
                    _xlsx_cell_value(cell, namespace)
                    for cell in rows[0].findall("m:c", namespace)
                ]
            for row in rows[1:]:
                values = [
                    _xlsx_cell_value(cell, namespace)
                    for cell in row.findall("m:c", namespace)
                ]
                if len(values) >= 4:
                    months.add(values[0])
                    admin_codes.add(values[1])
                    age_groups.add(values[3])
    if not months:
        raise ValueError(f"XLSX contains no living-population records: {path}")
    return {
        "record_count": sum(worksheet_rows),
        "worksheet_count": len(sheets),
        "fields": fields,
        "reference_month_min": min(months),
        "reference_month_max": max(months),
        "reference_month_count": len(months),
        "admin_dong_count": len(admin_codes),
        "age_groups": sorted(age_groups),
        "portal_advertised_record_count": 50294,
        "portal_advertised_reference_period": "2019-01/2025-12",
    }


def json_response_rows(payload: bytes) -> tuple[list[dict[str, Any]], int]:
    """Validate a standard Public Data Portal JSON response."""
    document = json.loads(payload)
    response = document["response"]
    header = response.get("header", {})
    if str(header.get("resultCode")) != "00":
        raise ValueError(f"Public Data Portal API error: {header}")
    body = response["body"]
    items = body.get("items", {}).get("item", [])
    if isinstance(items, dict):
        items = [items]
    return list(items), int(body.get("totalCount", len(items)))


def collect_files(
    output_root: Path,
    fetcher: Callable[[str], bytes],
    *,
    reuse_existing: bool,
) -> list[dict[str, Any]]:
    """Collect the three selected public file datasets."""
    entries: list[dict[str, Any]] = []
    for dataset_id, source in FILE_SOURCES.items():
        path = output_root / source["path"]
        payload = download(
            source["download_url"], path, fetcher, reuse_existing=reuse_existing
        )
        if not payload:
            raise ValueError(f"Downloaded file is empty: {dataset_id}")
        metadata: dict[str, Any]
        if source["format"] == "csv":
            record_count, fields, encoding = csv_metadata(path)
            metadata = {"record_count": record_count, "fields": fields, "encoding": encoding}
        else:
            metadata = xlsx_metadata(path)
        entries.append(
            {
                "dataset_id": dataset_id,
                "dataset_name": source["name"],
                "provider": source["provider"],
                "source_page": source["source_page"],
                "download_url": source["download_url"],
                "access_method": "public direct download",
                "reference_period": source["reference_period"],
                "period_type": source["period_type"],
                "analysis_role": source["analysis_role"],
                "spatial_unit": source["spatial_unit"],
                "license": source["license"],
                "collection_status": "collected",
                "local_path": path.as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "notes": source["notes"],
                **metadata,
            }
        )
    return entries


def portal_url(
    endpoint: str, service_key: str, *, num_rows: int, extra: dict[str, str] | None = None
) -> str:
    """Build an authenticated portal URL without double encoding the stored key."""
    parameters = {"pageNo": "1", "numOfRows": str(num_rows), "resultType": "json"}
    parameters.update(extra or {})
    return encoded_secret_url(endpoint, "serviceKey", service_key, parameters)


def collect_village_bus(
    service_key: str,
    output_root: Path,
    fetcher: Callable[[str], bytes],
    *,
    reuse_existing: bool,
) -> dict[str, Any]:
    """Collect every Busan village-bus operating-status record."""
    path = output_root / VILLAGE_BUS["path"]
    url = portal_url(VILLAGE_BUS["endpoint"], service_key, num_rows=10000)
    payload = download(url, path, fetcher, reuse_existing=reuse_existing)
    rows, total = json_response_rows(payload)
    if len(rows) != total or not rows:
        raise ValueError(f"Village-bus response count mismatch: {len(rows)}/{total}")
    basic_dates = sorted(
        {str(row.get("reference_date", "")).strip() for row in rows if row.get("reference_date")}
    )
    invalid_time_sentinel_count = sum(
        1
        for row in rows
        if str(row.get("first_bus_time", "")).startswith("1899-12-31")
        or str(row.get("last_bus_time", "")).startswith("1899-12-31")
    )
    return {
        "dataset_id": VILLAGE_BUS["dataset_id"],
        "dataset_name": VILLAGE_BUS["name"],
        "provider": VILLAGE_BUS["provider"],
        "source_page": VILLAGE_BUS["source_page"],
        "endpoint": VILLAGE_BUS["endpoint"],
        "access_method": "authenticated Public Data Portal OpenAPI",
        "request_parameters": {
            "pageNo": "1",
            "numOfRows": "10000",
            "resultType": "json",
        },
        "reference_period": basic_dates or "record-level basic date field",
        "period_type": "operating-status snapshot",
        "analysis_role": "supplemental_transport_service",
        "spatial_unit": "village-bus route",
        "license": "no restriction",
        "collection_status": "collected",
        "record_count": len(rows),
        "invalid_time_sentinel_record_count": invalid_time_sentinel_count,
        "local_path": path.as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "notes": (
            "Covers village buses only, not the complete Busan city-bus network. Source rows "
            "that encode times as the 1899-12-31 spreadsheet sentinel require cleaning."
        ),
    }


def api_error_code(payload: bytes) -> str | None:
    """Extract the compact error code returned outside the standard API envelope."""
    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        return None
    return root.findtext("resultCode")


def reference_rows(path: Path) -> list[dict[str, str]]:
    """Read the canonical 2025 administrative-dong reference."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def normalize_elderly_rows(
    rows: list[dict[str, Any]], reference_path: Path
) -> list[dict[str, Any]]:
    """Select each dong's latest record and map it to the canonical 2025 SGIS code."""
    reference = reference_rows(reference_path)
    reference_by_exact = {
        (row["sigungu_name"], row["admin_dong_name"].replace(" ", "")): row
        for row in reference
    }
    selected: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        district = str(row.get("gugun", "")).strip()
        parts = str(row.get("dongNm", "")).strip().split()
        source_name = parts[-1] if len(parts) >= 3 else "".join(parts)
        if source_name in {"총합", "합계"}:
            continue
        exact_key = (district, source_name)
        if exact_key in reference_by_exact:
            key = exact_key
        else:
            key = (district, re.sub(r"제(?=\d)", "", source_name))
        if key not in reference_by_exact:
            raise ValueError(f"Unmatched elderly-alone administrative dong: {key}")
        current = selected.get(key)
        current_date = str(current.get("referenceDate") or "") if current else ""
        candidate_date = str(row.get("referenceDate") or "")
        if current is None or candidate_date >= current_date:
            selected[key] = row
    if len(selected) != len(reference):
        missing = sorted(set(reference_by_exact) - set(selected))
        raise ValueError(
            f"Expected {len(reference)} elderly-alone dongs, received {len(selected)}; "
            f"missing={missing}"
        )

    output: list[dict[str, Any]] = []
    for reference_row in reference:
        key = (
            reference_row["sigungu_name"],
            reference_row["admin_dong_name"].replace(" ", ""),
        )
        row = selected[key]
        output.append(
            {
                "sgis_admin_dong_code": reference_row["admin_dong_code"],
                "sigungu_name": reference_row["sigungu_name"],
                "admin_dong_name": reference_row["admin_dong_name"],
                "source_admin_dong_name": row.get("dongNm"),
                "elderly_alone_total": row.get("laSeniorCnt"),
                "age_65_79_male": row.get("age6579MalOdsnCnt"),
                "age_65_79_female": row.get("age6579FmlOdsnCnt"),
                "age_80_plus_male": row.get("age80AbnmlMalOdsnCnt"),
                "age_80_plus_female": row.get("age80AbnmlFmlOdsnCnt"),
                "reference_date": row.get("referenceDate"),
                "source_institution_code": row.get("insttCode"),
            }
        )
    return output


def collect_elderly_alone(
    service_key: str,
    output_root: Path,
    fetcher: Callable[[str], bytes],
    *,
    reuse_existing: bool,
) -> dict[str, Any]:
    """Try every district and record the provider's current data-availability status."""
    path = output_root / ELDERLY_ALONE["path"]
    legacy_path = output_root / "elderly_alone/busan_elderly_alone_2026.json"
    existing_path = path if path.exists() else legacy_path
    rows: list[dict[str, Any]] = []
    no_data_districts: list[str] = []
    if reuse_existing and existing_path.exists():
        rows = json.loads(existing_path.read_text(encoding="utf-8"))["items"]
    else:
        for index, district in enumerate(DISTRICTS):
            if index:
                time.sleep(0.25)
            url = portal_url(
                ELDERLY_ALONE["endpoint"],
                service_key,
                num_rows=1000,
                extra={"gugun": district},
            )
            payload = fetcher(url)
            if api_error_code(payload) == "030":
                no_data_districts.append(district)
                continue
            district_rows, total = json_response_rows(payload)
            if len(district_rows) != total:
                raise ValueError(f"Elderly-alone response count mismatch for {district}")
            rows.extend(district_rows)

    digest: str | None = None
    csv_path: Path | None = None
    csv_digest: str | None = None
    normalized_rows: list[dict[str, Any]] = []
    if rows:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"items": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
        digest = sha256_file(path)
        normalized_rows = normalize_elderly_rows(rows, REFERENCE_PATH)
        csv_path = output_root / ELDERLY_ALONE["csv_path"]
        write_csv(csv_path, normalized_rows)
        csv_digest = sha256_file(csv_path)
    reference_dates = sorted(
        {
            str(row["reference_date"])
            for row in normalized_rows
            if row.get("reference_date") not in {None, "", "None"}
        }
    )
    missing_date_count = sum(not row.get("reference_date") for row in normalized_rows)
    missing_age_count = sum(not row.get("age_65_79_male") for row in normalized_rows)
    return {
        "dataset_id": ELDERLY_ALONE["dataset_id"],
        "dataset_name": ELDERLY_ALONE["name"],
        "provider": ELDERLY_ALONE["provider"],
        "source_page": ELDERLY_ALONE["source_page"],
        "endpoint": ELDERLY_ALONE["endpoint"],
        "access_method": "authenticated Public Data Portal OpenAPI",
        "request_parameters": {
            "pageNo": "1",
            "numOfRows": "1000",
            "resultType": "json",
            "gugun": "each of 16 Busan districts",
        },
        "reference_period": (
            f"{reference_dates[0]}/{reference_dates[-1]}" if reference_dates else "unverified"
        ),
        "period_type": "snapshot",
        "analysis_role": "supplemental_validation",
        "spatial_unit": "administrative dong",
        "license": "third-party rights and reuse permission not included; review required",
        "collection_status": "collected" if rows else "provider_no_data",
        "raw_record_count": len(rows),
        "record_count": len(normalized_rows),
        "duplicate_or_total_record_count": len(rows) - len(normalized_rows),
        "missing_reference_date_count": missing_date_count,
        "missing_age_breakdown_count": missing_age_count,
        "no_data_district_count": len(no_data_districts),
        "no_data_districts": no_data_districts,
        "local_path": path.as_posix() if rows else None,
        "sha256": digest,
        "csv_path": csv_path.as_posix() if csv_path else None,
        "csv_sha256": csv_digest,
        "notes": (
            "The collector requests all 16 districts, removes total/older duplicate rows, "
            "selects each dong's latest record, and maps it to the 2025 SGIS reference. "
            "Reference dates vary, so this remains supplemental validation rather than a "
            "uniform 2025 primary indicator."
        ),
    }


def validate_manifest(manifest: dict[str, Any], repository_root: Path = Path(".")) -> None:
    """Validate identities, checksums, and absence of credentials."""
    ensure_secret_free(manifest)
    datasets = manifest.get("datasets")
    expected_count = len(FILE_SOURCES) + 2
    if not isinstance(datasets, list) or len(datasets) != expected_count:
        raise ValueError(
            f"Supplemental manifest must contain {expected_count} selected datasets"
        )
    ids = [dataset["dataset_id"] for dataset in datasets]
    if len(ids) != len(set(ids)):
        raise ValueError("Supplemental manifest dataset identifiers are duplicated")
    for dataset in datasets:
        local_path = dataset.get("local_path")
        digest = dataset.get("sha256")
        if local_path and digest:
            path = repository_root / local_path
            if path.exists() and sha256_file(path) != digest:
                raise ValueError(f"Supplemental dataset checksum mismatch: {path}")
        csv_path_value = dataset.get("csv_path")
        csv_digest = dataset.get("csv_sha256")
        if csv_path_value and csv_digest:
            path = repository_root / csv_path_value
            if path.exists() and sha256_file(path) != csv_digest:
                raise ValueError(f"Supplemental normalized CSV checksum mismatch: {path}")


def collect(
    service_key: str,
    output_root: Path = OUTPUT_ROOT,
    manifest_path: Path = MANIFEST_PATH,
    fetcher: Callable[[str], bytes] = retry_fetch,
    *,
    reuse_existing: bool = True,
) -> dict[str, Any]:
    """Collect all selected supplemental sources and write one provenance manifest."""
    retrieved_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    datasets = collect_files(output_root, fetcher, reuse_existing=reuse_existing)
    datasets.append(
        collect_village_bus(
            service_key, output_root, fetcher, reuse_existing=reuse_existing
        )
    )
    datasets.append(
        collect_elderly_alone(
            service_key, output_root, fetcher, reuse_existing=reuse_existing
        )
    )
    manifest = {
        "schema_version": 1,
        "generated_at": retrieved_at,
        "analysis_cutoff": ANALYSIS_CUTOFF,
        "primary_reference_year": 2025,
        "dataset_count": len(datasets),
        "status_counts": {
            status: sum(1 for dataset in datasets if dataset["collection_status"] == status)
            for status in sorted({dataset["collection_status"] for dataset in datasets})
        },
        "datasets": datasets,
    }
    validate_manifest(manifest)
    write_json(manifest_path, manifest)
    write_json(output_root / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
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
        f"processed {manifest['dataset_count']} supplemental datasets: "
        f"{manifest['status_counts']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
