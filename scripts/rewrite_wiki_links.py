from __future__ import annotations

import os
import posixpath
import re
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import quote

LINK_PATTERN = re.compile(r"(?P<prefix>!?\[[^]]*\]\()(?P<target>[^)]+)(?P<suffix>\))")
EXTERNAL_PREFIXES = ("#", "//", "http://", "https://", "mailto:", "tel:")


def load_page_map(manifest_path: Path) -> dict[str, str]:
    page_map: dict[str, str] = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        source_path, page_name = line.split("\t", maxsplit=1)
        page_map[PurePosixPath(source_path).as_posix()] = page_name
    return page_map


def rewrite_target(
    target: str,
    source_path: PurePosixPath,
    page_map: dict[str, str],
    repository: str,
    source_ref: str,
) -> str:
    if target.startswith(EXTERNAL_PREFIXES):
        return target

    path_part, separator, fragment = target.partition("#")
    resolved_path = posixpath.normpath((source_path.parent / path_part).as_posix())
    fragment_suffix = f"#{fragment}" if separator else ""

    if resolved_path in page_map:
        return f"https://github.com/{repository}/wiki/{page_map[resolved_path]}{fragment_suffix}"

    encoded_path = quote(resolved_path, safe="/")
    return (
        f"https://github.com/{repository}/blob/{source_ref}/{encoded_path}{fragment_suffix}"
    )


def rewrite_page(
    text: str,
    source_path: PurePosixPath,
    page_map: dict[str, str],
    repository: str,
    source_ref: str,
) -> str:
    def replace(match: re.Match[str]) -> str:
        target = rewrite_target(
            match.group("target"), source_path, page_map, repository, source_ref
        )
        return f"{match.group('prefix')}{target}{match.group('suffix')}"

    return LINK_PATTERN.sub(replace, text)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: rewrite_wiki_links.py OUTPUT_DIR PAGE_MANIFEST")

    output_dir = Path(sys.argv[1])
    manifest_path = Path(sys.argv[2])
    repository = os.environ.get(
        "GITHUB_REPOSITORY", "codingnanyong/busan-competition-2026"
    )
    source_ref = os.environ.get("WIKI_SOURCE_REF", "main")
    page_map = load_page_map(manifest_path)

    for source, page_name in page_map.items():
        output_path = output_dir / f"{page_name}.md"
        rewritten = rewrite_page(
            output_path.read_text(encoding="utf-8"),
            PurePosixPath(source),
            page_map,
            repository,
            source_ref,
        )
        output_path.write_text(rewritten, encoding="utf-8")


if __name__ == "__main__":
    main()
