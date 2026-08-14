"""Public Data Portal contract for the national city-park standard dataset."""

from __future__ import annotations

import json
from typing import Any

from busan_imd.core.http import encoded_secret_url

ENDPOINT = "https://api.data.go.kr/openapi/tn_pubr_public_cty_park_info_api"
SOURCE_PAGE = "https://www.data.go.kr/data/15012890/standard.do"


def build_url(api_key: str, provider: str, *, page_no: int = 1, page_size: int = 1000) -> str:
    return encoded_secret_url(
        ENDPOINT,
        "serviceKey",
        api_key,
        {
            "pageNo": str(page_no),
            "numOfRows": str(page_size),
            "type": "json",
            "instt_nm": provider,
        },
    )


def response_rows(payload: bytes) -> tuple[list[dict[str, Any]], int]:
    document = json.loads(payload)
    response = document.get("response", document)
    header = response.get("header", {})
    code = str(header.get("resultCode", ""))
    if code not in {"00", "03"}:
        raise ValueError(f"City-park API error: {header.get('resultMsg', 'unknown error')}")
    body = response.get("body", {})
    items = body.get("items", {}) or {}
    rows = items.get("item", []) if isinstance(items, dict) else items
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list):
        raise ValueError("City-park API returned an unexpected items structure")
    return rows, int(body.get("totalCount", len(rows)) or 0)
