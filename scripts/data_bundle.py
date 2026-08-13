"""Export or import gitignored raw data for transfer between workstations."""

from __future__ import annotations

import argparse
import hashlib
import tarfile
from pathlib import Path, PurePosixPath

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = REPOSITORY_ROOT / "data/raw"
DEFAULT_ARCHIVE = REPOSITORY_ROOT / "outputs/busan-imd-raw-data.tar.gz"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def export_bundle(archive_path: Path) -> None:
    """Create a portable archive containing data/raw but never .env."""
    if not RAW_ROOT.is_dir():
        raise FileNotFoundError(f"Raw-data directory does not exist: {RAW_ROOT}")
    archive_path = archive_path.resolve()
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(RAW_ROOT, arcname="data/raw", recursive=True)
    digest = sha256(archive_path)
    archive_path.with_suffix(archive_path.suffix + ".sha256").write_text(
        f"{digest}  {archive_path.name}\n", encoding="ascii"
    )
    print(f"exported {archive_path} ({archive_path.stat().st_size} bytes, SHA-256 {digest})")


def _validate_member(member: tarfile.TarInfo) -> None:
    path = PurePosixPath(member.name)
    if path.is_absolute() or ".." in path.parts or path.parts[:2] != ("data", "raw"):
        raise ValueError(f"Unsafe or out-of-scope archive member: {member.name}")
    if member.issym() or member.islnk():
        raise ValueError(f"Links are not allowed in a raw-data bundle: {member.name}")


def import_bundle(archive_path: Path, *, replace: bool = False) -> None:
    """Safely restore a bundle; require --replace when raw data already exists."""
    archive_path = archive_path.resolve()
    existing = [path for path in RAW_ROOT.rglob("*") if path.is_file() and path.name != ".gitkeep"]
    if existing and not replace:
        raise FileExistsError(
            "data/raw already contains files; rerun with --replace only after preserving them"
        )
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            _validate_member(member)
        archive.extractall(REPOSITORY_ROOT, members=members, filter="data")
    print(f"imported {len(members)} entries from {archive_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("archive", type=Path, nargs="?", default=DEFAULT_ARCHIVE)
    import_parser = subparsers.add_parser("import")
    import_parser.add_argument("archive", type=Path)
    import_parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    if args.command == "export":
        export_bundle(args.archive)
    else:
        import_bundle(args.archive, replace=args.replace)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
