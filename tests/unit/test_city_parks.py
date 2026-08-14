import json

from busan_imd.collectors.city_parks import cutoff_status
from busan_imd.sources.city_parks import response_rows


def test_city_park_cutoff_status_is_explicit() -> None:
    assert cutoff_status("2025-12-31") == "eligible_by_designation_date"
    assert cutoff_status("20260101") == "post_cutoff_designation"
    assert cutoff_status("") == "unverified_designation_date"


def test_city_park_response_rows() -> None:
    payload = json.dumps(
        {
            "response": {
                "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
                "body": {"totalCount": 1, "items": {"item": [{"parkNm": "공원"}]}},
            }
        }
    ).encode()
    rows, total = response_rows(payload)
    assert total == 1
    assert rows == [{"parkNm": "공원"}]
