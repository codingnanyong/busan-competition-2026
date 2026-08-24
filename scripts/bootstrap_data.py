"""Restore the frozen 2025 snapshot, recollect stable sources, and rebuild outputs."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from busan_imd.core.config import read_env_file
from scripts.data_bundle import DEFAULT_ARCHIVE_NAME, import_bundle
from scripts.rebuild_processed import rebuild

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CollectionStep:
    dataset_id: str
    access_method: str
    required_keys: tuple[str, ...]
    command: tuple[str, ...]
    supports_refresh: bool = False
    supports_env_file: bool = True


COLLECTION_STEPS = (
    CollectionStep(
        "GEO-SGIS-ADM-001",
        "historical_api",
        ("SGIS_CONSUMER_KEY", "SGIS_CONSUMER_SECRET"),
        ("-m", "busan_imd.collectors.admin_boundaries", "--year", "2025"),
    ),
    CollectionStep(
        "EMP-SGIS-001",
        "historical_api",
        ("SGIS_CONSUMER_KEY", "SGIS_CONSUMER_SECRET"),
        (
            "-m",
            "busan_imd.collectors.approved_apis",
            "--skip-direct-downloads",
            "--dataset",
            "EMP-SGIS-001",
            "--manifest",
            "data/raw/collection/api-recollect-manifest.json",
        ),
    ),
    CollectionStep(
        "DEM-SGIS-001|EDU-SCHOOL-NEIS-001",
        "historical_api",
        ("SGIS_CONSUMER_KEY", "SGIS_CONSUMER_SECRET", "NEIS_API_KEY"),
        (
            "-m",
            "busan_imd.collectors.reference_data",
            "--manifest",
            "data/raw/reference/api-recollect-manifest.json",
        ),
    ),
    CollectionStep(
        "EDU-SCHOOLINFO-2025-001",
        "historical_api",
        ("SCHOOLINFO_API_KEY",),
        ("-m", "busan_imd.collectors.school_disclosures"),
    ),
    CollectionStep(
        "HLT-HOSPITAL-001|HLT-CLINIC-001|HLT-PHARMACY-001",
        "historical_reconstruction_api",
        ("DATA_GO_KR_SERVICE_KEY",),
        (
            "-m",
            "busan_imd.collectors.healthcare_facilities",
            "--manifest",
            "data/raw/public_data_portal/healthcare_facilities/api-recollect-manifest.json",
        ),
        True,
    ),
    CollectionStep(
        "SAF-KOROAD-001",
        "historical_api",
        ("KOROAD_API_KEY",),
        (
            "-m",
            "busan_imd.collectors.traffic_accidents",
            "--manifest",
            "data/raw/koroad/traffic_accidents/api-recollect-manifest.json",
        ),
        supports_refresh=True,
    ),
    CollectionStep(
        "SAF-POLICE-CRIME-2025-001",
        "versioned_file_api",
        ("DATA_GO_KR_SERVICE_KEY",),
        (
            "-m",
            "busan_imd.collectors.police_crime",
            "--manifest",
            "data/raw/public_data_portal/police_crime/2025/api-recollect-manifest.json",
        ),
        True,
    ),
    CollectionStep(
        "HOU-SGIS-OLD-001",
        "historical_api",
        ("SGIS_CONSUMER_KEY", "SGIS_CONSUMER_SECRET"),
        (
            "-m",
            "busan_imd.collectors.housing",
            "--manifest",
            "data/raw/sgis/housing/2024/api-recollect-manifest.json",
        ),
        True,
    ),
    CollectionStep(
        "SAF-FIRE-2025-001",
        "historical_api",
        ("DATA_GO_KR_SERVICE_KEY",),
        (
            "-m",
            "busan_imd.collectors.fire_incidents",
            "--manifest",
            "data/raw/public_data_portal/fire/2025/api-recollect-manifest.json",
        ),
        True,
    ),
    CollectionStep(
        "ENV-HEIS-AIR-2025-001",
        "historical_public_page",
        (),
        (
            "-m",
            "busan_imd.collectors.heis_air",
            "--year",
            "2025",
            "--manifest",
            "data/raw/heis/air_daily/2025/network-recollect-manifest.json",
        ),
        supports_refresh=True,
        supports_env_file=False,
    ),
)


def locate_bundle(explicit: Path | None, env_file: Path) -> Path:
    """Resolve an explicit, configured, or locally synced Google Drive bundle."""
    if explicit:
        return explicit.expanduser().resolve()
    configured = read_env_file(env_file).get("BUSAN_IMD_RAW_BUNDLE") or os.getenv(
        "BUSAN_IMD_RAW_BUNDLE"
    )
    if configured:
        return Path(configured).expanduser().resolve()
    relative = Path(
        "Developer/Project/busan-competition-2026/raw-data/2025"
    ) / DEFAULT_ARCHIVE_NAME
    patterns = (
        Path("Library/CloudStorage/GoogleDrive-*/My Drive") / relative,
        Path("Library/CloudStorage/GoogleDrive-*/내 드라이브") / relative,
        Path("Google Drive/My Drive") / relative,
    )
    for pattern in patterns:
        matches = sorted(Path.home().glob(pattern.as_posix()))
        if matches:
            return matches[0].resolve()
    raise FileNotFoundError(
        "Raw bundle not found. Pass --bundle or set BUSAN_IMD_RAW_BUNDLE to the synced "
        "Google Drive archive path."
    )


def collect_network(
    env_file: Path, selected: set[str], *, refresh: bool, dry_run: bool
) -> None:
    """Run only sources whose historical reference period is reproducible over the network."""
    config = read_env_file(env_file)
    for step in COLLECTION_STEPS:
        if selected and step.dataset_id not in selected:
            continue
        missing = [key for key in step.required_keys if not config.get(key) and not os.getenv(key)]
        if missing:
            raise ValueError(f"{step.dataset_id} requires: {', '.join(missing)}")
        command = [sys.executable, *step.command]
        if step.supports_env_file:
            command.extend(("--env-file", str(env_file)))
        if refresh and step.supports_refresh:
            command.append("--refresh")
        print(f"[{step.access_method}] {step.dataset_id}: {' '.join(command)}")
        if not dry_run:
            subprocess.run(command, cwd=REPOSITORY_ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    subparsers = parser.add_subparsers(dest="command", required=True)

    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("--bundle", type=Path)
    restore_parser.add_argument("--replace", action="store_true")

    collect_parser = subparsers.add_parser("collect-network")
    collect_parser.add_argument(
        "--only", action="append", choices=[step.dataset_id for step in COLLECTION_STEPS]
    )
    collect_parser.add_argument("--refresh", action="store_true")
    collect_parser.add_argument("--dry-run", action="store_true")

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--bundle", type=Path)
    prepare_parser.add_argument("--replace", action="store_true")
    prepare_parser.add_argument("--refresh-network", action="store_true")

    subparsers.add_parser("rebuild")
    args = parser.parse_args()
    if args.command == "restore":
        import_bundle(
            locate_bundle(args.bundle, args.env_file),
            replace=args.replace,
            require_checksum=True,
        )
    elif args.command == "collect-network":
        collect_network(
            args.env_file,
            set(args.only or ()),
            refresh=args.refresh,
            dry_run=args.dry_run,
        )
    elif args.command == "prepare":
        import_bundle(
            locate_bundle(args.bundle, args.env_file),
            replace=args.replace,
            require_checksum=True,
        )
        if args.refresh_network:
            collect_network(args.env_file, set(), refresh=True, dry_run=False)
        rebuild()
    else:
        rebuild()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
