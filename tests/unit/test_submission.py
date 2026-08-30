from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import busan_imd.submission.report as submission_report
from busan_imd.submission.config import MAX_BODY_PAGES
from busan_imd.submission.package import (
    PACKAGE_README,
    copy_visualization,
    write_data_dictionary,
    write_package_readme,
    write_source_catalog,
)
from busan_imd.submission.report import (
    COVER,
    PAGES,
    REQUIRED_SECTION_TITLES,
    markdown_report,
    noto_family,
    wrap_korean,
)
from busan_imd.submission.verify import verify_committed_package


def test_report_covers_official_sections_within_page_limit() -> None:
    text = markdown_report()

    assert COVER["title"] in text
    assert len(PAGES) <= MAX_BODY_PAGES
    for title in REQUIRED_SECTION_TITLES:
        assert f"## {title}" in text
    assert "접수번호" in COVER["status"]
    assert "data/raw" in text or "원천" in text


def test_wrap_korean_splits_long_runs_without_spaces() -> None:
    lines = wrap_korean("가" * 90, width=40)

    assert all(len(line) <= 40 for line in lines)
    assert "".join(lines) == "가" * 90


def test_source_catalog_keeps_provenance_columns(tmp_path: Path) -> None:
    source = tmp_path / "audit.csv"
    output = tmp_path / "catalog.xlsx"
    pd.DataFrame(
        [
            {
                "dataset_id": "GEO-ADM-001",
                "domain": "geography",
                "indicator_candidate": "boundary",
                "provider": "Busan",
                "source_url": "https://example.invalid/geo",
                "access_method": "public web page",
                "reference_period": "2025",
                "spatial_unit": "administrative dong",
                "license": "public",
                "availability_grade": "A",
                "decision": "include",
                "notes": "reference geography",
                "extra": "dropped",
            }
        ]
    ).to_csv(source, index=False)

    assert write_source_catalog(source, output) == 1
    catalog = pd.read_excel(output, engine="openpyxl")
    catalog_csv = pd.read_csv(output.with_suffix(".csv"))
    assert list(catalog.columns) == [
        "dataset_id",
        "domain",
        "indicator_candidate",
        "provider",
        "source_url",
        "access_method",
        "reference_period",
        "spatial_unit",
        "license",
        "availability_grade",
        "decision",
        "notes",
    ]
    assert "extra" not in catalog.columns
    assert catalog_csv["dataset_id"].tolist() == ["GEO-ADM-001"]


def test_source_catalog_rejects_missing_columns(tmp_path: Path) -> None:
    source = tmp_path / "audit.csv"
    pd.DataFrame([{"dataset_id": "X"}]).to_csv(source, index=False)

    with pytest.raises(ValueError, match="missing columns"):
        write_source_catalog(source, tmp_path / "catalog.xlsx")


def test_data_dictionary_and_readme_writers(tmp_path: Path) -> None:
    dictionary_source = tmp_path / "dictionary.csv"
    pd.DataFrame([{"column_name": "admin_dong_code", "dtype": "str"}]).to_csv(
        dictionary_source, index=False
    )
    dictionary_output = tmp_path / "data-dictionary.xlsx"
    readme = tmp_path / "README.md"

    assert write_data_dictionary(dictionary_source, dictionary_output) == 1
    write_package_readme(readme)

    assert readme.read_text(encoding="utf-8") == PACKAGE_README
    assert "Hangul" in readme.read_text(encoding="utf-8")
    copied = pd.read_excel(dictionary_output, engine="openpyxl")
    assert copied.loc[0, "column_name"] == "admin_dong_code"


def test_committed_submission_package_passes_reproducibility_checks() -> None:
    report = verify_committed_package()

    assert report["visualization_pages"] == 1
    assert report["dataset_count"] == 42
    assert report["official_hwpx_in_git"] is False
    assert report["secret_hits"] == []


def test_copy_visualization_requires_a_one_page_pdf(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="missing one-page visualization"):
        copy_visualization(tmp_path / "missing.pdf", tmp_path / "out.pdf")


def test_report_pdf_requires_noto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(submission_report, "findSystemFonts", lambda: [])

    with pytest.raises(RuntimeError, match="Noto Sans CJK"):
        noto_family()
