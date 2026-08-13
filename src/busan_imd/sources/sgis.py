"""Statistics Korea SGIS authentication and request helpers."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from busan_imd.core.http import fetch_json

AUTH_ENDPOINT = "https://sgisapi.mods.go.kr/OpenAPI3/auth/authentication.json"


def request_json(endpoint: str, parameters: dict[str, str]) -> dict[str, Any]:
    """Request one SGIS JSON document."""
    return fetch_json(f"{endpoint}?{urlencode(parameters)}")


def authenticate(consumer_key: str, consumer_secret: str) -> str:
    """Exchange SGIS credentials for a short-lived access token."""
    document = request_json(
        AUTH_ENDPOINT,
        {"consumer_key": consumer_key, "consumer_secret": consumer_secret},
    )
    if document.get("errCd") != 0:
        raise ValueError(f"SGIS authentication failed: {document.get('errMsg')}")
    token = document.get("result", {}).get("accessToken")
    if not token:
        raise ValueError("SGIS authentication returned no access token")
    return str(token)
