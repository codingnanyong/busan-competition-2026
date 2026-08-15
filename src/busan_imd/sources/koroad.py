"""KOROAD traffic-accident API contracts."""

from __future__ import annotations

import json

from busan_imd.core.http import encoded_secret_url

STATISTICS_ENDPOINT = "https://opendata.koroad.or.kr/data/rest/stt"
STATISTICS_SOURCE = "https://opendata.koroad.or.kr/api/selectSttDataSet.do"
HOTSPOT_ENDPOINT = "https://opendata.koroad.or.kr/data/rest/frequentzone/lg"
HOTSPOT_SOURCE = "https://opendata.koroad.or.kr/api/selectLgDataSet.do"
STATISTICS_DISTRICTS = tuple(str(code) for code in range(1201, 1217))
HOTSPOT_DISTRICTS = (
    "110",
    "140",
    "170",
    "200",
    "230",
    "260",
    "290",
    "320",
    "350",
    "380",
    "410",
    "440",
    "470",
    "500",
    "530",
    "710",
)


def build_url(endpoint: str, api_key: str, parameters: dict[str, str]) -> str:
    """Build a KOROAD request without double-encoding its API key."""
    return encoded_secret_url(endpoint, "authKey", api_key, parameters)


def response_rows(payload: bytes) -> list[dict[str, str]]:
    """Validate a KOROAD response and return its rows."""
    document = json.loads(payload)
    if str(document.get("resultCode")) != "00":
        raise ValueError(
            f"KOROAD API error {document.get('resultCode')}: {document.get('resultMsg')}"
        )
    items = document.get("items", {}).get("item", [])
    if isinstance(items, dict):
        items = [items]
    expected = int(document.get("totalCount", 0))
    if len(items) != expected:
        raise ValueError(f"Expected {expected} KOROAD rows, received {len(items)}")
    return items
