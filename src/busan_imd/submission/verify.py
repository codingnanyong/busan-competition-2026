"""Checks for the committed contest draft package. Does not read raw extracts."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from busan_imd.submission.config import DEFAULT_OUTPUT_DIR
from busan_imd.submission.package import pdf_page_count

SECRET_MARKERS = (
    "SGIS_CONSUMER_KEY",
    "SGIS_CONSUMER_SECRET",
    "DATA_GO_KR_SERVICE_KEY",
    "KOROAD_API_KEY",
    "SCHOOLINFO_API_KEY",
    "NEIS_API_KEY",
    "LINEAR_API_KEY",
    "consumer_secret",
)

REQUIRED_CATALOG_COLUMNS = (
    "dataset_id",
    "provider",
    "source_url",
    "access_method",
    "reference_period",
    "license",
    "decision",
)

TEXT_SUFFIXES = {".csv", ".md", ".txt", ".json"}


def _scan_secrets(root: Path) -> list[str]:
    hits: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        for marker in SECRET_MARKERS:
            if marker in text:
                hits.append(f"{path.as_posix()}:{marker}")
    return hits


def verify_committed_package(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict:
    """Inspect the Git-tracked draft. Official Hangul files stay outside Git."""
    visualization = output_dir / "01_data-visualization.pdf"
    report_pdf = output_dir / "02_analysis-report.pdf"
    catalog = output_dir / "03_data" / "source-catalog.csv"
    data_readme = output_dir / "03_data" / "README.txt"
    if not visualization.is_file():
        raise FileNotFoundError(f"missing visualization: {visualization}")
    if pdf_page_count(visualization) != 1:
        raise ValueError("visualization PDF must be exactly one page")
    if not report_pdf.is_file():
        raise FileNotFoundError(f"missing draft report PDF: {report_pdf}")
    if pdf_page_count(report_pdf) < 2:
        raise ValueError("draft report PDF must include a cover and body")

    frame = pd.read_csv(catalog)
    missing = [name for name in REQUIRED_CATALOG_COLUMNS if name not in frame.columns]
    if missing:
        raise ValueError(f"source-catalog missing columns: {missing}")
    if frame[list(REQUIRED_CATALOG_COLUMNS)].isna().any().any():
        raise ValueError("source-catalog has empty provenance cells")
    if "원천" not in data_readme.read_text(encoding="utf-8"):
        raise ValueError("03_data/README.txt must say raw extracts are omitted")

    secret_hits = _scan_secrets(output_dir)
    if secret_hits:
        raise ValueError("secret marker in submission draft: " + "; ".join(secret_hits))

    raw_like = [
        path.as_posix()
        for path in output_dir.rglob("*")
        if path.is_file() and re.search(r"\.(zip|tar|gz|geojson)$", path.name, re.I)
    ]
    if raw_like:
        raise ValueError("raw-like files in submission draft: " + ", ".join(raw_like))

    return {
        "visualization_pages": 1,
        "draft_report_pages": pdf_page_count(report_pdf),
        "dataset_count": int(len(frame)),
        "official_hwpx_in_git": False,
        "secret_hits": [],
    }
