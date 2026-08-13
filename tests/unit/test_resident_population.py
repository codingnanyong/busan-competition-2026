"""Unit tests for MOIS resident-population combination."""

from pathlib import Path

from busan_imd.collectors.resident_population import (
    discover_source_files,
    normalized_mois_dong_name,
    parse_area,
    parse_source_row,
)


def test_discovery_selects_only_canonical_district_sources(tmp_path: Path) -> None:
    source = tmp_path / "busan_jung_gu_resident_population_2025_12.csv"
    combined = tmp_path / "busan_resident_population_admin_dong_2025_12.csv"
    source.touch()
    combined.touch()

    assert discover_source_files(tmp_path) == [source]


def test_parse_area_handles_repeated_city_label() -> None:
    assert parse_area("부산광역시 부산광역시 연제구 거제제1동(2647061000)") == (
        "부산광역시",
        "연제구",
        "거제제1동",
        "2647061000",
    )


def test_mois_ordinal_name_matches_sgis_name_without_damaging_base_name() -> None:
    assert normalized_mois_dong_name("서제1동") == "서1동"
    assert normalized_mois_dong_name("거제제1동") == "거제1동"


def test_source_row_reconciles_population_by_sex() -> None:
    row = {
        "행정구역": "부산광역시 부산광역시 연제구 거제제1동(2647061000)",
        "2025년_총인구수": "10,000",
        "2025년_세대수": "5,000",
        "2025년_세대당 인구": "2.00",
        "2025년_남자 인구수": "4,900",
        "2025년_여자 인구수": "5,100",
        "2025년_남여 비율": "0.96",
    }

    parsed = parse_source_row(row)

    assert parsed["mois_admin_dong_code"] == "2647061000"
    assert parsed["total_population"] == 10_000
    assert parsed["male_population"] + parsed["female_population"] == 10_000
