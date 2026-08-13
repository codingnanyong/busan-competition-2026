"""Public Data Portal contract for National Fire Agency daily fire summaries."""

from __future__ import annotations

import json
from typing import Any

from busan_imd.core.http import encoded_secret_url

ENDPOINT = (
    "https://apis.data.go.kr/1661000/FireInformationService/"
    "getOcByfrstFireSmrzPcnd"
)
SOURCE_PAGE = "https://www.data.go.kr/data/15077644/openapi.do"
BUSAN_HEADQUARTERS = "부산소방재난본부"


def build_url(api_key: str, occurrence_date: str, *, page_size: int = 1000) -> str:
    """Build a daily request without double-encoding a portal service key."""
    return encoded_secret_url(
        ENDPOINT,
        "ServiceKey",
        api_key,
        {
            "pageNo": "1",
            "numOfRows": str(page_size),
            "resultType": "json",
            "ocrn_ymd": occurrence_date,
        },
    )


def response_rows(payload: bytes) -> tuple[list[dict[str, Any]], int]:
    """Parse the service's flat JSON envelope and return rows plus total count."""
    document = json.loads(payload)
    header = document.get("header", {})
    if str(header.get("resultCode")) != "00":
        raise ValueError(f"Fire API error: {header.get('resultMsg', 'unknown error')}")
    rows = document.get("body", {}).get("items", [])
    if rows is None:
        rows = []
    if isinstance(rows, dict):
        rows = rows.get("item", [])
    if not isinstance(rows, list):
        raise ValueError("Fire API returned an unexpected items structure")
    total_count = int(document.get("totalCount", len(rows)))
    if total_count > len(rows):
        raise ValueError(f"Fire API response was truncated: {len(rows)}/{total_count}")
    return rows, total_count


def busan_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select Busan headquarters rows and expose analysis-friendly field names."""
    selected: list[dict[str, Any]] = []
    for row in rows:
        if row.get("SIDO_HQ_FRST_CETR_NM") != BUSAN_HEADQUARTERS:
            continue
        selected.append(
            {
                "date": str(row.get("OCRN_YMD", "")),
                "fire_headquarters": str(row.get("SIDO_HQ_FRST_CETR_NM", "")),
                "fire_station": str(row.get("FRST_CETR_NM", "")),
                "reports": int(row.get("FIRE_RCPT_MNB", 0) or 0),
                "fires_in_progress": int(row.get("FIRE_PROG_MNB", 0) or 0),
                "false_reports": int(row.get("FALS_DCLR_MNB", 0) or 0),
                "alarm_processing": int(row.get("FLSRP_PRCS_MNB", 0) or 0),
                "self_extinguished": int(row.get("SLF_EXTSH_MNB", 0) or 0),
                "station_closed": int(row.get("STN_END_MNB", 0) or 0),
            }
        )
    return selected
