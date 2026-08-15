"""Shared provenance and reference-period validation."""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

ANALYSIS_CUTOFF = date(2026, 7, 31)
PRIMARY_REFERENCE_YEAR = 2025
PRIMARY_REFERENCE_START = date(PRIMARY_REFERENCE_YEAR, 1, 1)
PRIMARY_REFERENCE_END = date(PRIMARY_REFERENCE_YEAR, 12, 31)
DEFAULT_SECRET_MARKERS = (
    "serviceKey=",
    "authKey=",
    "accessToken=",
    "consumer_secret",
    "consumer_key",
    "KOROAD_API_KEY",
    "NEIS_API_KEY",
    "SCHOOLINFO_API_KEY",
)


def cutoff_status(reference_period: str, cutoff: date = ANALYSIS_CUTOFF) -> str:
    """Classify an ISO-like reference period against an analysis cutoff."""
    matches = re.findall(r"20\d{2}-\d{2}-\d{2}", reference_period)
    if matches:
        observed = date.fromisoformat(matches[-1])
        return "eligible" if observed <= cutoff else "outside_cutoff"
    match = re.search(r"(20\d{2})", reference_period)
    if match:
        return "eligible" if int(match.group(1)) <= cutoff.year else "outside_cutoff"
    return "unverified"


def analysis_role(reference_year: int) -> str:
    """Classify a dataset relative to the primary 2025 analysis year."""
    if reference_year == PRIMARY_REFERENCE_YEAR:
        return "primary"
    if reference_year < PRIMARY_REFERENCE_YEAR:
        return "fallback"
    return "supplemental_validation"


def ensure_secret_free(value: Any, markers: tuple[str, ...] = DEFAULT_SECRET_MARKERS) -> None:
    """Reject serialized provenance containing credential names or query values."""
    serialized = json.dumps(value, ensure_ascii=False)
    if any(marker in serialized for marker in markers):
        raise ValueError("Provenance contains a credential or secret-bearing query parameter")
