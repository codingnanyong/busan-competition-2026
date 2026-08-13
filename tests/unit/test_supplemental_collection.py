"""Unit tests for supplemental Busan data collection."""

import json
import zipfile

from busan_imd.collectors.supplemental_data import (
    api_error_code,
    json_response_rows,
    xlsx_metadata,
)


def test_json_response_rows_accepts_one_item_object() -> None:
    payload = json.dumps(
        {
            "response": {
                "header": {"resultCode": "00", "resultMsg": "NORMAL_CODE"},
                "body": {"items": {"item": {"route": "1"}}, "totalCount": 1},
            }
        }
    ).encode()

    rows, total = json_response_rows(payload)

    assert rows == [{"route": "1"}]
    assert total == 1


def test_api_error_code_reads_provider_no_data_response() -> None:
    payload = b"<result><resultMsg>NODATA_ERROR</resultMsg><resultCode>030</resultCode></result>"

    assert api_error_code(payload) == "030"


def test_xlsx_metadata_reads_inline_strings(tmp_path) -> None:
    workbook = tmp_path / "living.xlsx"
    cells = (
        ("기준년월", "행정동코드", "행정동명", "나이대"),
        ("202501", "2101053", "중앙동", "20대"),
        ("202502", "2101053", "중앙동", "30대"),
    )
    rows = "".join(
        "<row>"
        + "".join(f'<c t="inlineStr"><is><t>{value}</t></is></c>' for value in row)
        + "</row>"
        for row in cells
    )
    worksheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/'
        f'spreadsheetml/2006/main"><sheetData>{rows}</sheetData></worksheet>'
    )
    with zipfile.ZipFile(workbook, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)

    metadata = xlsx_metadata(workbook)

    assert metadata["record_count"] == 2
    assert metadata["reference_month_min"] == "202501"
    assert metadata["reference_month_max"] == "202502"
    assert metadata["admin_dong_count"] == 1
    assert metadata["age_groups"] == ["20대", "30대"]
