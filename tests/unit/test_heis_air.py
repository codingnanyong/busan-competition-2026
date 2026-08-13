"""Unit tests for HEIS parsing and collection orchestration."""

import calendar
from pathlib import Path

from busan_imd.collectors.heis_air import (
    build_url,
    collect,
    discover_stations,
    parse_daily_rows,
)


def sample_html(year: int = 2026, month: int = 1) -> str:
    rows = []
    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        day_label = f"{month:02d}월 {day:02d}일" if day == 1 else f"{day:02d}일"
        values = ["10", "20", "0.003", "0.021", "0.014", "0.3"]
        if day == 2:
            values = ["점검중"] * 6
        cells = "".join(f"<td>{value}</td>" for value in [day_label, *values])
        rows.append(f"<tr>{cells}</tr>")
    return f"""
    <select><option selected="selected" value="221112">광복동</option>
    <option value="221112">광복동</option></select>
    <table summary="측정소별 대기질정보 일평균자료 조회 결과"><tbody>
    {''.join(rows)}
    </tbody></table>
    """


def test_build_url_matches_heis_query_contract() -> None:
    url = build_url("221112", "광복동", 2026, 7)
    assert "areaindex=221112" in url
    assert "yearselect=16" in url
    assert "monthselect=6" in url
    assert "year=2026" in url
    assert "month=07" in url
    assert "yearselect=15" in build_url("221112", "광복동", 2025, 12)


def test_discover_and_parse_daily_rows() -> None:
    html = sample_html()
    assert discover_stations(html) == [("221112", "광복동")]

    rows = parse_daily_rows(html, "221112", "광복동", 2026, 1)
    assert len(rows) == 31
    assert rows[0]["observation_date"] == "2026-01-01"
    assert rows[0]["pm25_ug_m3"] == "10"
    assert rows[0]["measurement_status"] == "observed"
    assert rows[1]["pm25_ug_m3"] == ""
    assert rows[1]["measurement_status"] == "점검중"


def test_collect_writes_raw_csv_and_provenance(tmp_path: Path) -> None:
    payload = sample_html().encode()
    output_root = tmp_path / "raw"
    manifest_path = tmp_path / "manifest.json"

    manifest = collect(
        2026,
        [1],
        output_root,
        manifest_path,
        delay_seconds=0,
        fetcher=lambda _url: payload,
    )

    assert manifest["station_count"] == 1
    assert manifest["raw_file_count"] == 1
    assert manifest["record_count"] == 31
    assert manifest["non_observed_record_count"] == 1
    assert (output_root / "html/221112/2026-01.html").exists()
    assert (output_root / "busan_heis_air_daily_2026_01_01.csv").exists()
    assert manifest_path.exists()


def test_collect_accepts_complete_2025_year(tmp_path: Path) -> None:
    payloads = {
        month: sample_html(year=2025, month=month).encode() for month in range(1, 13)
    }

    def fetcher(url: str) -> bytes:
        month = int(url.rsplit("month=", maxsplit=1)[1])
        return payloads[month]

    manifest = collect(
        2025,
        list(range(1, 13)),
        tmp_path / "raw",
        tmp_path / "manifest.json",
        delay_seconds=0,
        fetcher=fetcher,
    )

    assert manifest["dataset_id"] == "ENV-AIR-HEIS-DAILY-2025-001"
    assert manifest["reference_period"] == "2025-01-01/2025-12-31"
    assert manifest["period_type"] == "annual"
    assert manifest["record_count"] == 365
