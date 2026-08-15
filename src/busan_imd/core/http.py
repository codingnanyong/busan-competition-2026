"""Bounded HTTP helpers for approved HTTPS data sources."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USER_AGENT = "busan-competition-2026/1.0"


def fetch_bytes(url: str, *, timeout: int = 120) -> bytes:
    """Fetch bytes from an explicitly configured HTTPS URL."""
    if not url.startswith("https://"):
        raise ValueError("Only HTTPS data sources are supported")
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - HTTPS checked above
        return response.read()


def fetch_json(url: str, *, timeout: int = 120) -> dict[str, Any]:
    """Fetch and decode a JSON object."""
    document = json.loads(fetch_bytes(url, timeout=timeout))
    if not isinstance(document, dict):
        raise ValueError("Expected a JSON object")
    return document


def retry_fetch(
    url: str,
    *,
    attempts: int = 3,
    fetcher: Callable[[str], bytes] = fetch_bytes,
) -> bytes:
    """Retry transient transport failures with bounded exponential backoff."""
    if attempts < 1:
        raise ValueError("attempts must be positive")
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return fetcher(url)
        except Exception as error:  # noqa: BLE001 - retry transport, then preserve cause
            last_error = error
            if attempt < attempts - 1:
                time.sleep(2**attempt)
    assert last_error is not None
    raise last_error


def encoded_secret_url(
    endpoint: str,
    secret_name: str,
    encoded_secret: str,
    parameters: dict[str, str],
) -> str:
    """Append an already URL-encoded secret without double encoding it."""
    return f"{endpoint}?{secret_name}={encoded_secret}&{urlencode(parameters)}"
