"""Rebuild all local 2025 processed artifacts from a restored raw-data bundle."""

from __future__ import annotations

import argparse
from pathlib import Path

from busan_imd.candidate_processing import CandidatePaths, process_all
from busan_imd.collectors.consumer_sales import run as process_consumer_sales
from busan_imd.data_quality import run as write_quality_report
from busan_imd.income_inference import infer
from busan_imd.income_inference import write_outputs as write_income_outputs
from busan_imd.standardization import build_standardized_profile, write_outputs

BOOTSTRAP_DIR = Path("data/processed/bootstrap/2025")
BOOTSTRAP_REPORT = BOOTSTRAP_DIR / "standardization_report_without_income.json"


def rebuild() -> None:
    """Run the dependency-ordered, network-free processing pipeline."""
    process_all(
        CandidatePaths(),
        Path("data/processed/candidates/2025"),
        Path("docs/data/manifests/CANDIDATE_PROCESSING_REPORT_2025.json"),
    )
    bootstrap, bootstrap_report = build_standardized_profile(include_basic_livelihood=False)
    write_outputs(bootstrap, bootstrap_report, BOOTSTRAP_DIR, BOOTSTRAP_REPORT)
    income, income_manifest = infer(BOOTSTRAP_DIR / "busan_admin_dong_candidate_profile_2025.csv")
    write_income_outputs(income, income_manifest)
    final_profile, final_report = build_standardized_profile()
    write_outputs(final_profile, final_report)
    process_consumer_sales()
    write_quality_report()


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    rebuild()
    print("rebuilt candidate, inference, standardized, consumer-sales, and quality artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
