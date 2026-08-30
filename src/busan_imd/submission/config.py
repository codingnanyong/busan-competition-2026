"""Paths for the 2025 contest submission draft package."""

from pathlib import Path

from busan_imd.infographic.config import DEFAULT_PDF_OUTPUT, DEFAULT_TABLE_OUTPUT_DIR

DEFAULT_OUTPUT_DIR = Path("outputs/submission/2025")
DEFAULT_DATA_DIR = DEFAULT_OUTPUT_DIR / "03_data"
DEFAULT_VISUALIZATION_PDF = DEFAULT_OUTPUT_DIR / "01_data-visualization.pdf"
DEFAULT_REPORT_PDF = DEFAULT_OUTPUT_DIR / "02_analysis-report.pdf"
DEFAULT_REPORT_MARKDOWN = DEFAULT_OUTPUT_DIR / "02_analysis-report.md"
DEFAULT_SOURCE_CATALOG = DEFAULT_DATA_DIR / "source-catalog.xlsx"
DEFAULT_DATA_DICTIONARY = DEFAULT_DATA_DIR / "data-dictionary.xlsx"
DEFAULT_PACKAGE_README = DEFAULT_OUTPUT_DIR / "README.md"
DEFAULT_REPORT_MANIFEST = Path("docs/data/manifests/SUBMISSION_DRAFT_REPORT_2025.json")
DEFAULT_AUDIT = Path("docs/data/tables/DATASET_AUDIT.csv")
DEFAULT_DICTIONARY = Path("docs/data/tables/DATA_DICTIONARY_2025.csv")
DEFAULT_ONE_PAGE_PDF = DEFAULT_PDF_OUTPUT
DEFAULT_OFFICIAL_TEMPLATE = Path(
    "docs/templates/2026-big-data-competition-submission-template.hwpx"
)
TRACKED_ANALYSIS_TABLES = (
    DEFAULT_TABLE_OUTPUT_DIR / "busan_admin_dong_action_profile_2025.csv",
    DEFAULT_TABLE_OUTPUT_DIR / "busan_admin_dong_category_assessment_2025.csv",
    DEFAULT_TABLE_OUTPUT_DIR / "busan_admin_dong_major_category_assessment_2025.csv",
    DEFAULT_TABLE_OUTPUT_DIR / "busan_admin_dong_category_indicator_scores_2025.csv",
)
MAX_BODY_PAGES = 10
