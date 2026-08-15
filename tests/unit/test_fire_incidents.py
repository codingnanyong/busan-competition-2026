import json
from datetime import date

from busan_imd.collectors.fire_incidents import date_range
from busan_imd.sources.fire_information import busan_rows, response_rows


def test_date_range_is_inclusive() -> None:
    assert list(date_range(date(2025, 1, 30), date(2025, 2, 1))) == [
        date(2025, 1, 30),
        date(2025, 1, 31),
        date(2025, 2, 1),
    ]


def test_response_parser_and_busan_filter() -> None:
    payload = json.dumps(
        {
            "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
            "totalCount": 2,
            "body": {
                "items": [
                    {
                        "OCRN_YMD": "20250101",
                        "SIDO_HQ_FRST_CETR_NM": "부산소방재난본부",
                        "FRST_CETR_NM": "중부소방서",
                        "FIRE_RCPT_MNB": 3,
                        "FIRE_PROG_MNB": 1,
                    },
                    {"SIDO_HQ_FRST_CETR_NM": "서울소방재난본부"},
                ]
            },
        },
        ensure_ascii=False,
    ).encode()
    rows, total_count = response_rows(payload)
    selected = busan_rows(rows)

    assert total_count == 2
    assert selected == [
        {
            "date": "20250101",
            "fire_headquarters": "부산소방재난본부",
            "fire_station": "중부소방서",
            "reports": 3,
            "fires_in_progress": 1,
            "false_reports": 0,
            "alarm_processing": 0,
            "self_extinguished": 0,
            "station_closed": 0,
        }
    ]
