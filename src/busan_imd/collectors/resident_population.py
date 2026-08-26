"""Combine manually downloaded MOIS resident-population CSV files for Busan."""

from __future__ import annotations

import argparse
import csv
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from busan_imd.core.artifacts import sha256_file, write_csv, write_json
from busan_imd.core.provenance import ensure_secret_free

INPUT_DIR = Path("data/raw/mois/resident_population/2025")
REFERENCE_PATH = Path("docs/data/tables/BUSAN_ADMIN_DONG_CODES_2025.csv")
OUTPUT_PATH = INPUT_DIR / "busan_resident_population_admin_dong_2025_12.csv"
MANIFEST_PATH = Path("docs/data/manifests/MOIS_RESIDENT_POPULATION_MANIFEST_2025.json")
SOURCE_PAGE = "https://jumin.mois.go.kr/"
DATASET_ID = "DEM-MOIS-RESIDENT-2025-001"
REFERENCE_PERIOD = "2025-12-31"
SOURCE_FILE_PATTERN = re.compile(
    r"^busan_(?:jung|seo|dong|yeongdo|busanjin|dongnae|nam|buk|haeundae|saha|"
    r"geumjeong|gangseo|yeonje|suyeong|sasang)_gu_resident_population_2025_12\.csv$"
    r"|^busan_gijang_gun_resident_population_2025_12\.csv$"
)
AREA_PATTERN = re.compile(r"^(.*?)\s*\((\d{10})\)$")
SOURCE_FIELDS = (
    "행정구역",
    "2025년_총인구수",
    "2025년_세대수",
    "2025년_세대당 인구",
    "2025년_남자 인구수",
    "2025년_여자 인구수",
    "2025년_남여 비율",
)
OUTPUT_FIELDS = (
    "reference_period",
    "mois_admin_dong_code",
    "sgis_admin_dong_code",
    "sido_name",
    "sigungu_name",
    "admin_dong_name",
    "source_admin_dong_name",
    "total_population",
    "households",
    "population_per_household",
    "male_population",
    "female_population",
    "sex_ratio",
)


def discover_source_files(input_dir: Path) -> list[Path]:
    """Return only the 16 district-level files, excluding derived and summary CSVs."""
    return sorted(
        path
        for path in input_dir.glob("*.csv")
        if SOURCE_FILE_PATTERN.fullmatch(path.name)
    )


def read_csv(path: Path, encoding: str) -> list[dict[str, str]]:
    """Read a CSV and strip the whitespace introduced by the source export."""
    with path.open(encoding=encoding, newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        return [
            {str(key).strip(): str(value or "").strip() for key, value in row.items()}
            for row in reader
        ]


def parse_area(value: str) -> tuple[str, str, str | None, str]:
    """Parse the MOIS label into city, district, optional dong, and its 10-digit code."""
    match = AREA_PATTERN.fullmatch(value.strip())
    if not match:
        raise ValueError(f"Invalid MOIS administrative-area label: {value!r}")
    tokens = match.group(1).split()
    if len(tokens) >= 2 and tokens[0] == tokens[1] == "부산광역시":
        tokens.pop(0)
    if len(tokens) not in {1, 2, 3} or tokens[0] != "부산광역시":
        raise ValueError(f"Unexpected Busan administrative-area label: {value!r}")
    district = tokens[1] if len(tokens) >= 2 else ""
    dong = tokens[2] if len(tokens) == 3 else None
    return tokens[0], district, dong, match.group(2)


def integer(value: str) -> int:
    """Parse a comma-formatted integer from the MOIS export."""
    return int(value.replace(",", "").strip())


def normalized_mois_dong_name(name: str) -> str:
    """Convert MOIS ordinal names such as 거제제1동 to the SGIS form 거제1동."""
    return re.sub(r"제(?=\d)", "", re.sub(r"\s+", "", name))


def load_reference(path: Path) -> tuple[dict[tuple[str, str], dict[str, str]], dict[str, int]]:
    """Load the 2025 SGIS reference and preserve its canonical ordering."""
    rows = read_csv(path, "utf-8-sig")
    mapping: dict[tuple[str, str], dict[str, str]] = {}
    order: dict[str, int] = {}
    for index, row in enumerate(rows):
        key = (row["sigungu_name"], row["admin_dong_name"].replace(" ", ""))
        if key in mapping:
            raise ValueError(f"Duplicate reference administrative dong: {key}")
        mapping[key] = row
        order[row["admin_dong_code"]] = index
    return mapping, order


def parse_source_row(row: dict[str, str]) -> dict[str, Any]:
    """Parse and internally validate one administrative-dong row."""
    missing = set(SOURCE_FIELDS) - set(row)
    if missing:
        raise ValueError(f"MOIS CSV is missing fields: {sorted(missing)}")
    sido, district, dong, code = parse_area(row["행정구역"])
    if dong is None or code.endswith("00000"):
        raise ValueError(f"Expected an administrative-dong row, received: {row['행정구역']}")
    total = integer(row["2025년_총인구수"])
    male = integer(row["2025년_남자 인구수"])
    female = integer(row["2025년_여자 인구수"])
    households = integer(row["2025년_세대수"])
    population_per_household = float(row["2025년_세대당 인구"])
    sex_ratio = float(row["2025년_남여 비율"])
    if total != male + female:
        raise ValueError(f"Population sex totals do not reconcile for {row['행정구역']}")
    display_tolerance = 0.011
    if (
        households <= 0
        or abs(total / households - population_per_household) > display_tolerance
    ):
        raise ValueError(f"Population per household does not reconcile for {row['행정구역']}")
    if female <= 0 or abs(male / female - sex_ratio) > display_tolerance:
        raise ValueError(f"Sex ratio does not reconcile for {row['행정구역']}")
    return {
        "reference_period": REFERENCE_PERIOD,
        "mois_admin_dong_code": code,
        "sido_name": sido,
        "sigungu_name": district,
        "source_admin_dong_name": dong,
        "total_population": total,
        "households": households,
        "population_per_household": population_per_household,
        "male_population": male,
        "female_population": female,
        "sex_ratio": sex_ratio,
    }


def reconcile_total(total_row: dict[str, str], dong_rows: list[dict[str, Any]]) -> None:
    """Require each district total to equal the sum of its administrative dongs."""
    _, district, dong, _ = parse_area(total_row["행정구역"])
    if dong is not None:
        raise ValueError(f"Expected a district total row: {total_row['행정구역']}")
    checks = {
        "2025년_총인구수": "total_population",
        "2025년_세대수": "households",
        "2025년_남자 인구수": "male_population",
        "2025년_여자 인구수": "female_population",
    }
    for source_field, output_field in checks.items():
        expected = integer(total_row[source_field])
        observed = sum(int(row[output_field]) for row in dong_rows)
        if expected != observed:
            message = (
                f"{district} {source_field} total mismatch: "
                f"expected {expected}, observed {observed}"
            )
            raise ValueError(
                message
            )


def combine_files(
    source_files: list[Path], reference_path: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Combine district files, validate totals, and attach canonical SGIS dong codes."""
    reference, order = load_reference(reference_path)
    combined: list[dict[str, Any]] = []
    source_metadata: list[dict[str, Any]] = []
    for path in source_files:
        rows = read_csv(path, "cp949")
        if not rows:
            raise ValueError(f"MOIS CSV is empty: {path}")
        parsed = [parse_source_row(row) for row in rows[1:]]
        reconcile_total(rows[0], parsed)
        combined.extend(parsed)
        source_metadata.append(
            {
                "local_path": path.as_posix(),
                "sha256": sha256_file(path),
                "raw_record_count": len(rows),
                "admin_dong_record_count": len(parsed),
            }
        )

    codes = [str(row["mois_admin_dong_code"]) for row in combined]
    if len(codes) != len(set(codes)):
        raise ValueError("MOIS administrative-dong codes are duplicated")

    unmatched: list[str] = []
    for row in combined:
        key = (
            str(row["sigungu_name"]),
            normalized_mois_dong_name(str(row["source_admin_dong_name"])),
        )
        reference_row = reference.get(key)
        if reference_row is None:
            unmatched.append("|".join(key))
            continue
        row["sgis_admin_dong_code"] = reference_row["admin_dong_code"]
        row["admin_dong_name"] = reference_row["admin_dong_name"]
    if unmatched:
        raise ValueError(f"Unmatched MOIS administrative dongs: {sorted(unmatched)}")
    if len(combined) != len(reference):
        raise ValueError(
            f"Expected {len(reference)} reference dongs, received {len(combined)} MOIS dongs"
        )
    combined.sort(key=lambda row: order[str(row["sgis_admin_dong_code"])])
    return combined, source_metadata


def validate_summary(path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate the separately downloaded city/district summary against detail rows."""
    summary = read_csv(path, "cp949")
    if len(summary) != 17:
        raise ValueError(f"Expected 17 city/district summary rows, received {len(summary)}")
    city_row = summary[0]
    _, district, dong, code = parse_area(city_row["행정구역"])
    if district or dong is not None or code != "2600000000":
        raise ValueError("The first summary row is not the Busan city total")
    expected = {
        "total_population": integer(city_row["2025년_총인구수"]),
        "households": integer(city_row["2025년_세대수"]),
        "male_population": integer(city_row["2025년_남자 인구수"]),
        "female_population": integer(city_row["2025년_여자 인구수"]),
    }
    observed = {field: sum(int(row[field]) for row in rows) for field in expected}
    if expected != observed:
        raise ValueError(f"Busan summary totals do not reconcile: {expected=} {observed=}")

    detail_by_district: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        detail_by_district.setdefault(str(row["sigungu_name"]), []).append(row)
    summary_districts: set[str] = set()
    for summary_row in summary[1:]:
        _, summary_district, summary_dong, _ = parse_area(summary_row["행정구역"])
        if not summary_district or summary_dong is not None:
            raise ValueError(f"Invalid district summary row: {summary_row['행정구역']}")
        summary_districts.add(summary_district)
        detail = detail_by_district.get(summary_district, [])
        if not detail:
            raise ValueError(f"No administrative-dong detail for {summary_district}")
        for source_field, output_field in (
            ("2025년_총인구수", "total_population"),
            ("2025년_세대수", "households"),
            ("2025년_남자 인구수", "male_population"),
            ("2025년_여자 인구수", "female_population"),
        ):
            district_expected = integer(summary_row[source_field])
            district_observed = sum(int(row[output_field]) for row in detail)
            if district_expected != district_observed:
                raise ValueError(
                    f"{summary_district} summary mismatch for {source_field}: "
                    f"expected {district_expected}, observed {district_observed}"
                )
    if summary_districts != set(detail_by_district):
        raise ValueError("District coverage differs between the summary and detail files")
    return {
        "local_path": path.as_posix(),
        "sha256": sha256_file(path),
        "record_count": len(summary),
        "validation_role": "city_and_district_total_cross_check",
    }


def collect(
    input_dir: Path = INPUT_DIR,
    reference_path: Path = REFERENCE_PATH,
    output_path: Path = OUTPUT_PATH,
    manifest_path: Path = MANIFEST_PATH,
) -> dict[str, Any]:
    """Create the canonical combined CSV and its source-provenance manifest."""
    source_files = discover_source_files(input_dir)
    if len(source_files) != 16:
        raise ValueError(f"Expected 16 district source files, received {len(source_files)}")
    rows, source_metadata = combine_files(source_files, reference_path)
    write_csv(output_path, rows, OUTPUT_FIELDS)

    summary_path = input_dir / "busan_resident_population_by_dong_2025_12.csv"
    summary = validate_summary(summary_path, rows) if summary_path.exists() else None
    totals = {
        field: sum(int(row[field]) for row in rows)
        for field in ("total_population", "households", "male_population", "female_population")
    }
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "dataset_id": DATASET_ID,
        "dataset_name": "2025 Busan resident population and households by administrative dong",
        "provider": "Ministry of the Interior and Safety (MOIS)",
        "source_page": SOURCE_PAGE,
        "access_method": "manual CSV download from the resident registration statistics portal",
        "reference_period": REFERENCE_PERIOD,
        "primary_reference_year": 2025,
        "analysis_role": "primary",
        "eligible_for_primary_analysis": True,
        "period_type": "snapshot",
        "spatial_unit": "administrative dong",
        "source_code_system": "MOIS 10-digit administrative institution code",
        "reference_code_system": "SGIS 2025 administrative dong code",
        "mapping_method": "district and normalized administrative-dong name",
        "source_file_count": len(source_files),
        "source_files": source_metadata,
        "summary_file": summary,
        "output_path": output_path.as_posix(),
        "output_sha256": sha256_file(output_path),
        "record_count": len(rows),
        "unique_mois_code_count": len({row["mois_admin_dong_code"] for row in rows}),
        "matched_reference_count": len(rows),
        "unmatched_reference_count": 0,
        "totals": totals,
        "license_note": (
            "Confirm and follow the source portal's current reuse terms when publishing."
        ),
        "notes": (
            "The 16 district files contain 206 administrative-dong rows. The separate 17-row "
            "file contains only Busan and district totals and is used solely for reconciliation."
        ),
    }
    ensure_secret_free(manifest)
    write_json(manifest_path, manifest)
    return manifest


def validate_manifest(manifest: dict[str, Any], repository_root: Path) -> None:
    """Validate the committed manifest and local files when raw artifacts are present."""
    if manifest["dataset_id"] != DATASET_ID or manifest["record_count"] != 206:
        raise ValueError("Unexpected MOIS resident-population manifest identity or record count")
    if manifest["matched_reference_count"] != 206 or manifest["unmatched_reference_count"] != 0:
        raise ValueError("MOIS-to-SGIS administrative-dong mapping is incomplete")
    output = repository_root / manifest["output_path"]
    if output.exists() and sha256_file(output) != manifest["output_sha256"]:
        raise ValueError("Combined MOIS resident-population CSV checksum mismatch")
    for entry in manifest["source_files"]:
        path = repository_root / entry["local_path"]
        if path.exists() and sha256_file(path) != entry["sha256"]:
            raise ValueError(f"MOIS source checksum mismatch: {path}")
    ensure_secret_free(manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=INPUT_DIR)
    parser.add_argument("--reference", type=Path, default=REFERENCE_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    args = parser.parse_args()
    manifest = collect(args.input_dir, args.reference, args.output, args.manifest)
    print(
        f"combined {manifest['record_count']} administrative dongs from "
        f"{manifest['source_file_count']} files: {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
