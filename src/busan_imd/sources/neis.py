"""NEIS school-information API contract."""

from __future__ import annotations

import json
from urllib.parse import urlencode

from busan_imd.core.http import fetch_bytes

SOURCE_PAGE = "https://www.data.go.kr/data/15068997/fileData.do"
ENDPOINT = "https://open.neis.go.kr/hub/schoolInfo"
BUSAN_EDUCATION_OFFICE_CODE = "C10"


def fetch_school_page(page: int, api_key: str, page_size: int = 1000) -> dict[str, object]:
    """Fetch one authenticated Busan school-information page."""
    parameters = {
        "KEY": api_key,
        "Type": "json",
        "pIndex": str(page),
        "pSize": str(page_size),
        "ATPT_OFCDC_SC_CODE": BUSAN_EDUCATION_OFFICE_CODE,
    }
    document = json.loads(fetch_bytes(f"{ENDPOINT}?{urlencode(parameters)}"))
    if not isinstance(document, dict):
        raise ValueError("NEIS returned an invalid JSON document")
    return document
