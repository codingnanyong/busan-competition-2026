"""MOIS local-government health-facility licence API contracts."""

from __future__ import annotations

import json
from typing import Any

from busan_imd.core.http import encoded_secret_url

HOSPITAL_ENDPOINT = "https://apis.data.go.kr/1741000/hospitals/info"
HOSPITAL_SOURCE = "https://www.data.go.kr/data/15154458/openapi.do"
CLINIC_ENDPOINT = "https://apis.data.go.kr/1741000/clinics/info"
CLINIC_SOURCE = "https://www.data.go.kr/data/15154874/openapi.do"
PHARMACY_ENDPOINT = "https://apis.data.go.kr/1741000/pharmacies/info"
PHARMACY_SOURCE = "https://www.data.go.kr/data/15154822/openapi.do"


def build_url(endpoint: str, service_key: str, parameters: dict[str, str]) -> str:
    """Build a Public Data Portal request without double-encoding its key."""
    return encoded_secret_url(endpoint, "serviceKey", service_key, parameters)


def response_rows(payload: bytes) -> tuple[list[dict[str, Any]], int]:
    """Validate a migrated local-licence response and return its rows and total."""
    document = json.loads(payload)
    response = document.get("response", {})
    header = response.get("header", {})
    if str(header.get("resultCode")) != "0":
        raise ValueError(
            f"Public Data Portal API error {header.get('resultCode')}: "
            f"{header.get('resultMsg')}"
        )
    body = response.get("body", {})
    items = body.get("items", {}).get("item", [])
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        raise ValueError("Public Data Portal response items must be a list")
    total = int(body.get("totalCount", 0))
    if len(items) > total:
        raise ValueError(f"Received {len(items)} rows for a total count of {total}")
    return items, total
