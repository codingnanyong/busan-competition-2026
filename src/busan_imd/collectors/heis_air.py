"""Collect historical daily air-quality observations from Busan HEIS."""

from __future__ import annotations

import argparse
import calendar
import re
import time
from collections.abc import Callable
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode

from busan_imd.core.artifacts import aggregate_sha256, write_json
from busan_imd.core.artifacts import sha256_file as sha256
from busan_imd.core.artifacts import write_csv as write_csv_artifact
from busan_imd.core.http import retry_fetch
from busan_imd.core.provenance import (
    ANALYSIS_CUTOFF,
    PRIMARY_REFERENCE_YEAR,
    analysis_role,
    ensure_secret_free,
)

SOURCE_PAGE = "https://heis.busan.go.kr/environmental/air002_3.aspx"
DEFAULT_OUTPUT_PARENT = Path("data/raw/heis/air_daily")
DEFAULT_MANIFEST_PARENT = Path("docs/data/manifests")
CUTOFF = ANALYSIS_CUTOFF
POLLUTANT_COLUMNS = ("pm25_ug_m3", "pm10_ug_m3", "so2_ppm", "o3_ppm", "no2_ppm", "co_ppm")
CSV_COLUMNS = (
    "station_code",
    "station_name",
    "observation_date",
    *POLLUTANT_COLUMNS,
    "measurement_status",
)


class DailyTableParser(HTMLParser):
    """Extract rows from the HEIS daily-average results table."""

    def __init__(self) -> None:
        super().__init__()
        self.in_target = False
        self.in_cell = False
        self.current_row: list[str] | None = None
        self.current_cell: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "table" and "일평균자료 조회 결과" in (attributes.get("summary") or ""):
            self.in_target = True
        elif self.in_target and tag == "tr":
            self.current_row = []
        elif self.in_target and tag == "td" and self.current_row is not None:
            self.in_cell = True
            self.current_cell = []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.in_target and tag == "td" and self.in_cell:
            assert self.current_row is not None
            self.current_row.append(" ".join("".join(self.current_cell).split()))
            self.in_cell = False
        elif self.in_target and tag == "tr" and self.current_row is not None:
            if len(self.current_row) == 7 and "일" in self.current_row[0]:
                self.rows.append(self.current_row)
            self.current_row = None
        elif self.in_target and tag == "table":
            self.in_target = False


def build_url(station_code: str, station_name: str, year: int, month: int) -> str:
    """Build the public HEIS daily-average query URL."""
    parameters = {
        "areaindex": station_code,
        "siteselect": "0",
        "sitename": station_name,
        "yearselect": str(year - 2010),
        "monthselect": str(month - 1),
        "year": str(year),
        "month": f"{month:02d}",
    }
    return f"{SOURCE_PAGE}?{urlencode(parameters)}"


def fetch_page(url: str) -> bytes:
    """Fetch one public HEIS page with bounded retries."""
    return retry_fetch(url)


def discover_stations(html: str) -> list[tuple[str, str]]:
    """Discover and deduplicate station codes from HEIS dropdown options."""
    matches = re.findall(
        r'<option\b[^>]*\bvalue=["\'](22\d{4})["\'][^>]*>([^<]+)</option>', html
    )
    stations = list(dict.fromkeys((code, name.strip()) for code, name in matches))
    if not stations:
        raise ValueError("No HEIS monitoring stations were found")
    return stations


def parse_daily_rows(
    html: str, station_code: str, station_name: str, year: int, month: int
) -> list[dict[str, str]]:
    """Normalize one station-month page into analysis-ready daily rows."""
    parser = DailyTableParser()
    parser.feed(html)
    expected_days = calendar.monthrange(year, month)[1]
    if len(parser.rows) != expected_days:
        raise ValueError(
            f"Expected {expected_days} daily rows for {station_code} {year}-{month:02d}, "
            f"received {len(parser.rows)}"
        )

    normalized: list[dict[str, str]] = []
    for raw_row in parser.rows:
        day_match = re.search(r"(\d{1,2})일", raw_row[0])
        if not day_match:
            raise ValueError(f"Unrecognized HEIS date cell: {raw_row[0]}")
        observation_date = date(year, month, int(day_match.group(1))).isoformat()
        values: list[str] = []
        statuses: list[str] = []
        for value in raw_row[1:]:
            try:
                float(value)
            except ValueError:
                values.append("")
                statuses.append(value or "missing")
            else:
                values.append(value)
        row = {
            "station_code": station_code,
            "station_name": station_name,
            "observation_date": observation_date,
            **dict(zip(POLLUTANT_COLUMNS, values, strict=True)),
            "measurement_status": "observed" if not statuses else ";".join(dict.fromkeys(statuses)),
        }
        normalized.append(row)
    return normalized


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    """Write normalized observations with a stable schema."""
    write_csv_artifact(path, rows, CSV_COLUMNS)


def validate_manifest(manifest: dict[str, object], repository_root: Path = Path(".")) -> None:
    """Validate HEIS coverage, provenance fields, and an available local CSV."""
    stations = manifest.get("stations", [])
    if not isinstance(stations, list) or len(stations) != manifest.get("station_count"):
        raise ValueError("HEIS station count does not match its station registry")
    station_codes = [station["code"] for station in stations]
    if len(station_codes) != len(set(station_codes)):
        raise ValueError("HEIS station codes are not unique")
    expected_files = int(manifest["station_count"]) * int(manifest["month_count"])
    if manifest.get("raw_file_count") != expected_files:
        raise ValueError("HEIS raw file count does not cover every station-month")
    if manifest.get("analysis_cutoff") != CUTOFF.isoformat():
        raise ValueError("HEIS manifest has the wrong analysis cutoff")
    if manifest.get("primary_reference_year") != PRIMARY_REFERENCE_YEAR:
        raise ValueError("HEIS manifest has the wrong primary reference year")
    expected_role = analysis_role(int(str(manifest["reference_period"])[:4]))
    if manifest.get("analysis_role") != expected_role:
        raise ValueError("HEIS manifest has the wrong analysis role")
    ensure_secret_free(manifest)
    for key in ("raw_files_aggregate_sha256", "csv_sha256"):
        if not re.fullmatch(r"[0-9A-F]{64}", str(manifest.get(key, ""))):
            raise ValueError(f"Invalid HEIS checksum: {key}")
    csv_path = repository_root / str(manifest["csv_path"])
    if csv_path.exists() and sha256(csv_path) != manifest["csv_sha256"]:
        raise ValueError("HEIS CSV checksum does not match its manifest")


def collect(
    year: int,
    months: list[int],
    output_root: Path,
    manifest_path: Path,
    delay_seconds: float = 0.15,
    fetcher: Callable[[str], bytes] = fetch_page,
    reuse_existing: bool = True,
) -> dict[str, object]:
    """Collect all HEIS stations for selected months and write provenance outputs."""
    allowed_months = set(range(1, 13)) if year == 2025 else set(range(1, 8))
    if year not in (2025, 2026) or not months or not set(months) <= allowed_months:
        raise ValueError("Collection is restricted to 2025-01..12 or 2026-01..07")

    retrieved_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    discovery_url = build_url("221112", "광복동", year, months[0])
    discovery_payload = fetcher(discovery_url)
    stations = discover_stations(discovery_payload.decode("utf-8"))
    raw_paths: list[Path] = []
    rows: list[dict[str, str]] = []

    for station_index, (station_code, station_name) in enumerate(stations):
        for month in months:
            url = build_url(station_code, station_name, year, month)
            raw_path = output_root / "html" / station_code / f"{year}-{month:02d}.html"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            if reuse_existing and raw_path.exists():
                payload = raw_path.read_bytes()
            else:
                payload = discovery_payload if url == discovery_url else fetcher(url)
            raw_path.write_bytes(payload)
            raw_paths.append(raw_path)
            rows.extend(
                parse_daily_rows(payload.decode("utf-8"), station_code, station_name, year, month)
            )
            if delay_seconds and not (station_index == len(stations) - 1 and month == months[-1]):
                time.sleep(delay_seconds)

    csv_path = output_root / f"busan_heis_air_daily_{year}_{months[0]:02d}_{months[-1]:02d}.csv"
    write_csv(rows, csv_path)
    observed_rows = sum(row["measurement_status"] == "observed" for row in rows)
    manifest: dict[str, object] = {
        "schema_version": 1,
        "dataset_id": (
            "ENV-AIR-HEIS-DAILY-001"
            if year == 2026
            else "ENV-AIR-HEIS-DAILY-2025-001"
        ),
        "provider": "Busan Metropolitan City Health & Environment Information System (HEIS)",
        "source_page": SOURCE_PAGE,
        "access_method": "public HEIS HTML daily-average query",
        "query_parameters": [
            "areaindex",
            "sitename",
            "yearselect",
            "monthselect",
            "year",
            "month",
        ],
        "reference_period": (
            f"{year}-{months[0]:02d}-01/{year}-{months[-1]:02d}-"
            f"{calendar.monthrange(year, months[-1])[1]}"
        ),
        "primary_reference_year": PRIMARY_REFERENCE_YEAR,
        "analysis_role": analysis_role(year),
        "eligible_for_primary_analysis": year == PRIMARY_REFERENCE_YEAR,
        "analysis_cutoff": CUTOFF.isoformat(),
        "cutoff_status": "eligible",
        "period_type": "annual" if months == list(range(1, 13)) else "partial_year",
        "retrieved_at": retrieved_at,
        "license": "Public HEIS page; raw-data redistribution terms require separate verification",
        "station_count": len(stations),
        "stations": [{"code": code, "name": name} for code, name in stations],
        "month_count": len(months),
        "raw_file_count": len(raw_paths),
        "raw_files_aggregate_sha256": aggregate_sha256(raw_paths, output_root),
        "csv_path": csv_path.as_posix(),
        "csv_sha256": sha256(csv_path),
        "record_count": len(rows),
        "fully_observed_record_count": observed_rows,
        "non_observed_record_count": len(rows) - observed_rows,
        "notes": (
            "Each HTML response is retained locally. Non-numeric source values such as 점검중 "
            "are preserved in measurement_status and represented as blank pollutant values."
        ),
    }
    validate_manifest(manifest)
    write_json(manifest_path, manifest)
    local_manifest = output_root / "manifest.json"
    write_json(local_manifest, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--year", type=int, default=PRIMARY_REFERENCE_YEAR, help="Reference year (default: 2025)"
    )
    parser.add_argument("--months", type=int, nargs="+")
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--delay-seconds", type=float, default=0.15)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Fetch every page again instead of reusing existing raw HTML",
    )
    args = parser.parse_args()
    months = args.months or (list(range(1, 13)) if args.year == 2025 else list(range(1, 8)))
    output_root = args.output_root or DEFAULT_OUTPUT_PARENT / str(args.year)
    manifest_path = args.manifest or DEFAULT_MANIFEST_PARENT / f"HEIS_AIR_MANIFEST_{args.year}.json"
    manifest = collect(
        args.year,
        sorted(set(months)),
        output_root,
        manifest_path,
        args.delay_seconds,
        reuse_existing=not args.refresh,
    )
    print(
        f"collected {manifest['record_count']} daily rows from "
        f"{manifest['station_count']} HEIS stations; manifest: {manifest_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
