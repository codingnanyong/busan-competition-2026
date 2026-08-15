import os
import re
import subprocess
from pathlib import Path, PurePosixPath

from scripts.rewrite_wiki_links import rewrite_page

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RELATIVE_LINK_PATTERN = re.compile(
    r"\[[^]]+\]\((?!https?://|#|mailto:|tel:)[^)]+\)"
)


def test_rewrite_page_links_to_wiki_pages_and_repository_files() -> None:
    page_map = {
        "README.ko.md": "KO-Home",
        "README.en.md": "EN-Home",
        "docs/PROJECT_PLAN.md": "KO-Project-Plan",
    }
    text = (
        "[English](README.en.md)\n"
        "[계획](docs/PROJECT_PLAN.md#일정)\n"
        "[서식](docs/templates/report.hwpx)\n"
        "[섹션](#운영-원칙)\n"
        "[외부](https://example.com/docs)\n"
    )

    rewritten = rewrite_page(
        text,
        PurePosixPath("README.ko.md"),
        page_map,
        "codingnanyong/busan-competition-2026",
        "main",
    )

    assert "(https://github.com/codingnanyong/busan-competition-2026/wiki/EN-Home)" in rewritten
    assert (
        "(https://github.com/codingnanyong/busan-competition-2026/wiki/"
        "KO-Project-Plan#일정)" in rewritten
    )
    assert (
        "(https://github.com/codingnanyong/busan-competition-2026/blob/main/"
        "docs/templates/report.hwpx)" in rewritten
    )
    assert "[섹션](#운영-원칙)" in rewritten
    assert "[외부](https://example.com/docs)" in rewritten


def test_build_wiki_leaves_no_broken_repository_relative_links(tmp_path: Path) -> None:
    output_dir = tmp_path / "wiki"
    environment = os.environ.copy()
    environment["WIKI_SOURCE_REF"] = "develop"

    subprocess.run(
        ["bash", "scripts/build_wiki.sh", str(output_dir)],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=True,
    )

    pages = list(output_dir.glob("*.md"))
    assert len(pages) >= 20
    assert not (output_dir / ".wiki-pages.tsv").exists()
    assert all(not RELATIVE_LINK_PATTERN.search(page.read_text(encoding="utf-8")) for page in pages)
