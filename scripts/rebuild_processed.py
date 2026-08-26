"""Rebuild all local 2025 processed artifacts from a restored raw-data bundle."""

from __future__ import annotations

import argparse
from pathlib import Path

from busan_imd.analysis.category_assessment import run as write_category_assessment
from busan_imd.analysis.cluster_analysis import run as write_cluster_analysis
from busan_imd.analysis.composite_index import run as write_composite_index
from busan_imd.analysis.domain_scores import run as write_domain_scores
from busan_imd.analysis.eda import run as write_eda_report
from busan_imd.analysis.environmental_overlay import run as write_environmental_overlay
from busan_imd.analysis.policy_matrix import run as write_policy_matrix
from busan_imd.analysis.priority_areas import run as write_priority_areas
from busan_imd.analysis.sensitivity_analysis import run as write_sensitivity_analysis
from busan_imd.collectors.consumer_sales import run as process_consumer_sales
from busan_imd.infographic import run as write_infographic
from busan_imd.processing.candidate_processing import CandidatePaths, process_all
from busan_imd.processing.data_quality import run as write_quality_report
from busan_imd.processing.income_inference import infer
from busan_imd.processing.income_inference import write_outputs as write_income_outputs
from busan_imd.processing.standardization import build_standardized_profile, write_outputs
from busan_imd.submission import run as write_submission

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
    write_eda_report()
    write_domain_scores()
    write_composite_index()
    write_sensitivity_analysis()
    write_priority_areas()
    write_cluster_analysis()
    write_environmental_overlay()
    write_policy_matrix()
    write_category_assessment()
    write_infographic()
    write_submission()


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    rebuild()
    print(
        "rebuilt candidate, inference, standardized, consumer-sales, quality, EDA, "
        "domain-score, composite-index, sensitivity-analysis, priority-area, cluster-analysis, "
        "environmental-overlay, policy-matrix, category-assessment, infographic, "
        "and submission-draft artifacts"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
