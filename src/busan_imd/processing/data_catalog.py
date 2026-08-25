"""Validation helpers for the COD-10 dataset availability audit."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
from pathlib import Path

REQUIRED_COLUMNS = (
    "dataset_id",
    "domain",
    "indicator_candidate",
    "measure_type",
    "provider",
    "source_url",
    "reference_period",
    "update_cycle",
    "spatial_unit",
    "format",
    "access_method",
    "license",
    "coverage",
    "missing_rate",
    "availability_grade",
    "decision",
    "fallback",
    "collected_at",
    "checksum",
    "notes",
)
MEASURE_TYPES = {"direct", "proxy", "context", "validation"}
GRADES = {"A", "B", "C", "D"}
DECISIONS = {"include", "hold", "exclude", "validation-only"}
DATASET_ID_PATTERN = re.compile(r"^[A-Z]+(?:-[A-Z0-9]+)+-\d{3}$")
SHA256_PATTERN = re.compile(r"^[A-F0-9]{64}$")
PORTAL_ID_PATTERN = re.compile(r"data\.go\.kr/data/(\d+)/fileData\.do")


def read_catalog(path: Path) -> list[dict[str, str]]:
    """Read the audit CSV and reject a missing or altered schema."""
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != REQUIRED_COLUMNS:
            raise ValueError("Dataset audit columns do not match the required schema")
        return list(reader)


def validate_catalog(path: Path) -> list[dict[str, str]]:
    """Validate identifiers and controlled fields in the audit catalog."""
    rows = read_catalog(path)
    if not rows:
        raise ValueError("Dataset audit must contain at least one row")

    identifiers: set[str] = set()
    errors: list[str] = []
    for line_number, row in enumerate(rows, start=2):
        missing = [column for column in REQUIRED_COLUMNS if not row[column].strip()]
        if missing:
            errors.append(f"line {line_number}: blank fields: {', '.join(missing)}")

        dataset_id = row["dataset_id"]
        if not DATASET_ID_PATTERN.fullmatch(dataset_id):
            errors.append(f"line {line_number}: invalid dataset_id {dataset_id!r}")
        if dataset_id in identifiers:
            errors.append(f"line {line_number}: duplicate dataset_id {dataset_id!r}")
        identifiers.add(dataset_id)

        if row["measure_type"] not in MEASURE_TYPES:
            errors.append(f"line {line_number}: invalid measure_type")
        if row["availability_grade"] not in GRADES:
            errors.append(f"line {line_number}: invalid availability_grade")
        if row["decision"] not in DECISIONS:
            errors.append(f"line {line_number}: invalid decision")
        if not row["source_url"].startswith("https://"):
            errors.append(f"line {line_number}: source_url must use HTTPS")

        checksum = row["checksum"]
        if checksum != "not_collected" and not SHA256_PATTERN.fullmatch(checksum):
            errors.append(f"line {line_number}: checksum must be SHA-256 or not_collected")

    if errors:
        raise ValueError("\n".join(errors))
    return rows


def verify_downloads(rows: list[dict[str, str]], raw_dir: Path) -> list[str]:
    """Verify checksums for public-portal files that are present locally."""
    verified: list[str] = []
    for row in rows:
        if row["checksum"] == "not_collected":
            continue
        match = PORTAL_ID_PATTERN.search(row["source_url"])
        if not match:
            continue
        raw_path = raw_dir / f"{match.group(1)}.download"
        if not raw_path.exists():
            continue
        digest = hashlib.sha256(raw_path.read_bytes()).hexdigest().upper()
        if digest != row["checksum"]:
            raise ValueError(f"Checksum mismatch: {raw_path}")
        verified.append(row["dataset_id"])
    return verified


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("--raw-dir", type=Path)
    args = parser.parse_args()

    rows = validate_catalog(args.catalog)
    verified = verify_downloads(rows, args.raw_dir) if args.raw_dir else []
    print(f"validated {len(rows)} catalog rows; verified {len(verified)} local downloads")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
