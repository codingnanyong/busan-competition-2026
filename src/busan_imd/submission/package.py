"""Assemble the contest submission draft folder without redistributing raw extracts."""

from __future__ import annotations

import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from busan_imd.core.artifacts import sha256_file
from busan_imd.submission.config import (
    DEFAULT_AUDIT,
    DEFAULT_DATA_DICTIONARY,
    DEFAULT_DICTIONARY,
    DEFAULT_OFFICIAL_TEMPLATE,
    DEFAULT_ONE_PAGE_PDF,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PACKAGE_README,
    DEFAULT_REPORT_MANIFEST,
    DEFAULT_REPORT_MARKDOWN,
    DEFAULT_REPORT_PDF,
    DEFAULT_SOURCE_CATALOG,
    DEFAULT_VISUALIZATION_PDF,
    MAX_BODY_PAGES,
    TRACKED_ANALYSIS_TABLES,
)
from busan_imd.submission.report import write_markdown, write_pdf

PACKAGE_README = """# 2025 제출물 초안

공식 압축 구성에 맞춘 초안이다. 접수번호와 최종 파일명은 제출 직전에 참가 신청 폼을
다시 확인한다.

- `01_data-visualization.pdf`: 1페이지 인포그래픽. 파이프라인이 복사한다.
- `02_analysis-report.pdf`: 표지와 본문. 본문은 10페이지 이하.
- `02_analysis-report.md`: 공식 HWPX 서식에 붙여 넣을 본문.
- `03_data/`: 재배포 가능한 파생 표와 출처 목록(XLSX·CSV). `data/raw` 원천은 넣지 않는다.

HWPX는 `docs/templates/2026-big-data-competition-submission-template.hwpx`를 복사한 뒤
`02_analysis-report.md`를 서식 목차에 옮긴다. 이 초안은 Hangul 파일을 자동 작성하지
않으며, 빈 서식을 제출 보고서로 두지 않는다.

```bash
docker compose run --rm jupyter python -m busan_imd.submission
```
"""


def pdf_page_count(path: Path) -> int:
    return len(re.findall(rb"/Type\s*/Page\b", path.read_bytes()))


def copy_visualization(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"missing one-page visualization: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    pages = pdf_page_count(destination)
    if pages != 1:
        raise ValueError(f"visualization PDF must be exactly one page; found {pages}")


def _write_excel_and_csv(frame: pd.DataFrame, excel_path: Path) -> Path:
    excel_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path = excel_path.with_suffix(".csv")
    frame.to_csv(csv_path, index=False, encoding="utf-8", lineterminator="\n")
    frame.to_excel(excel_path, index=False, engine="openpyxl")
    return csv_path


def write_source_catalog(audit_path: Path, output_path: Path) -> int:
    frame = pd.read_csv(audit_path)
    columns = [
        "dataset_id",
        "domain",
        "indicator_candidate",
        "provider",
        "source_url",
        "reference_period",
        "spatial_unit",
        "license",
        "availability_grade",
        "decision",
        "notes",
    ]
    missing = [name for name in columns if name not in frame.columns]
    if missing:
        raise ValueError(f"DATASET_AUDIT.csv missing columns: {missing}")
    _write_excel_and_csv(frame.loc[:, columns], output_path)
    return len(frame)


def write_data_dictionary(dictionary_path: Path, output_path: Path) -> int:
    frame = pd.read_csv(dictionary_path)
    _write_excel_and_csv(frame, output_path)
    return len(frame)


def copy_analysis_tables(
    data_dir: Path,
    sources: tuple[Path, ...] = TRACKED_ANALYSIS_TABLES,
) -> list[str]:
    data_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for source in sources:
        if not source.is_file():
            raise FileNotFoundError(f"missing analysis table: {source}")
        destination = data_dir / source.name
        shutil.copyfile(source, destination)
        copied.append(destination.as_posix())
    return copied


def write_package_readme(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PACKAGE_README, encoding="utf-8", newline="\n")


def run(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    visualization_pdf: Path = DEFAULT_ONE_PAGE_PDF,
    audit_path: Path = DEFAULT_AUDIT,
    dictionary_path: Path = DEFAULT_DICTIONARY,
    analysis_tables: tuple[Path, ...] = TRACKED_ANALYSIS_TABLES,
    manifest_path: Path = DEFAULT_REPORT_MANIFEST,
    official_template: Path = DEFAULT_OFFICIAL_TEMPLATE,
) -> dict:
    if not official_template.is_file():
        raise FileNotFoundError(f"missing official Hangul template: {official_template}")

    data_dir = output_dir / "03_data"
    visualization_dest = output_dir / DEFAULT_VISUALIZATION_PDF.name
    report_pdf = output_dir / DEFAULT_REPORT_PDF.name
    report_md = output_dir / DEFAULT_REPORT_MARKDOWN.name
    catalog = data_dir / DEFAULT_SOURCE_CATALOG.name
    dictionary = data_dir / DEFAULT_DATA_DICTIONARY.name
    catalog_csv = catalog.with_suffix(".csv")
    dictionary_csv = dictionary.with_suffix(".csv")
    readme_path = output_dir / DEFAULT_PACKAGE_README.name

    copy_visualization(visualization_pdf, visualization_dest)
    write_markdown(report_md)
    pdf_info = write_pdf(report_pdf)
    body_pages = int(pdf_info["body_pages"])
    if body_pages > MAX_BODY_PAGES:
        raise ValueError("report body exceeds the contest page limit")
    if pdf_page_count(report_pdf) != int(pdf_info["total_pages"]):
        raise ValueError("report PDF page count does not match the generated page plan")
    dataset_count = write_source_catalog(audit_path, catalog)
    dictionary_rows = write_data_dictionary(dictionary_path, dictionary)
    copied_tables = copy_analysis_tables(data_dir, analysis_tables)
    write_package_readme(readme_path)

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "reference_year": 2025,
        "artifact_status": "submission_draft",
        "cover_pages": pdf_info["cover_pages"],
        "body_pages": body_pages,
        "total_pages": pdf_info["total_pages"],
        "max_body_pages": MAX_BODY_PAGES,
        "visualization_page_count": 1,
        "dataset_count": dataset_count,
        "data_dictionary_row_count": dictionary_rows,
        "analysis_tables": copied_tables,
        "font_family": pdf_info["font_family"],
        "hwpx_status": "hangul_paste_required",
        "official_template": official_template.as_posix(),
        "output_paths": {
            "visualization_pdf": visualization_dest.as_posix(),
            "report_pdf": report_pdf.as_posix(),
            "report_markdown": report_md.as_posix(),
            "source_catalog": catalog.as_posix(),
            "source_catalog_csv": catalog_csv.as_posix(),
            "data_dictionary": dictionary.as_posix(),
            "data_dictionary_csv": dictionary_csv.as_posix(),
            "package_readme": readme_path.as_posix(),
        },
        "output_sha256": {
            "visualization_pdf": sha256_file(visualization_dest),
            "report_pdf": sha256_file(report_pdf),
            "report_markdown": sha256_file(report_md),
            "source_catalog_csv": sha256_file(catalog_csv),
            "data_dictionary_csv": sha256_file(dictionary_csv),
            "package_readme": sha256_file(readme_path),
            **{Path(path).name: sha256_file(Path(path)) for path in copied_tables},
        },
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


def main() -> int:
    summary = run()
    print(
        "wrote submission draft: "
        f"body {summary['body_pages']} pages, "
        f"{summary['dataset_count']} audited datasets"
    )
    return 0
