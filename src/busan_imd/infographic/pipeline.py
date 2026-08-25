"""Orchestrate reproducible infographic and dashboard outputs."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

from busan_imd.core.artifacts import sha256_file, write_json
from busan_imd.infographic.config import (
    DEFAULT_BOUNDARIES,
    DEFAULT_CATEGORY_ASSESSMENT,
    DEFAULT_COMPOSITE,
    DEFAULT_HTML_OUTPUT,
    DEFAULT_INDICATOR_SCORES,
    DEFAULT_MAJOR_CATEGORY_ASSESSMENT,
    DEFAULT_OVERLAY,
    DEFAULT_PDF_OUTPUT,
    DEFAULT_PNG_OUTPUT,
    DEFAULT_POLICY_CATALOG,
    DEFAULT_POLICY_MATRIX,
    DEFAULT_PRIORITY_OUTPUT,
    DEFAULT_PROFILE_OUTPUT,
    DEFAULT_REPORT,
    DEFAULT_SVG_OUTPUT,
)
from busan_imd.infographic.profiles import build_action_profiles
from busan_imd.infographic.rendering import render, write_action_map


def run(
    composite_path: Path = DEFAULT_COMPOSITE,
    boundaries_path: Path = DEFAULT_BOUNDARIES,
    priority_path: Path = DEFAULT_PRIORITY_OUTPUT,
    overlay_path: Path = DEFAULT_OVERLAY,
    policy_matrix_path: Path = DEFAULT_POLICY_MATRIX,
    category_assessment_path: Path = DEFAULT_CATEGORY_ASSESSMENT,
    major_category_assessment_path: Path = DEFAULT_MAJOR_CATEGORY_ASSESSMENT,
    indicator_scores_path: Path = DEFAULT_INDICATOR_SCORES,
    policy_catalog_path: Path = DEFAULT_POLICY_CATALOG,
    svg_output: Path = DEFAULT_SVG_OUTPUT,
    pdf_output: Path = DEFAULT_PDF_OUTPUT,
    png_output: Path = DEFAULT_PNG_OUTPUT,
    profile_output: Path = DEFAULT_PROFILE_OUTPUT,
    html_output: Path = DEFAULT_HTML_OUTPUT,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    """Write the one-page draft, 206-dong action profiles, map, and manifest."""
    composite = pd.read_csv(composite_path, dtype={"admin_dong_code": str})
    boundaries = gpd.read_file(boundaries_path)
    priority = pd.read_csv(priority_path, dtype={"admin_dong_code": str})
    overlay = pd.read_csv(overlay_path, dtype={"admin_dong_code": str})
    policy_matrix = pd.read_csv(policy_matrix_path)
    category_assessments = pd.read_csv(
        category_assessment_path,
        dtype={"admin_dong_code": str},
    )
    major_category_assessments = pd.read_csv(
        major_category_assessment_path,
        dtype={"admin_dong_code": str},
    )
    indicator_scores = pd.read_csv(indicator_scores_path, dtype={"admin_dong_code": str})
    policy_catalog = pd.read_csv(policy_catalog_path)

    summary = render(
        composite,
        boundaries,
        priority,
        overlay,
        policy_matrix,
        svg_output,
        pdf_output,
        png_output,
    )
    profiles = build_action_profiles(composite)
    profile_output.parent.mkdir(parents=True, exist_ok=True)
    profiles.to_csv(profile_output, index=False, encoding="utf-8-sig", lineterminator="\n")
    write_action_map(
        profiles,
        boundaries,
        category_assessments,
        major_category_assessments,
        indicator_scores,
        policy_catalog,
        html_output,
    )

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "reference_year": 2025,
        "artifact_status": "submission_draft",
        "format": "A4 portrait one-page infographic",
        "dong_action_profile_count": len(profiles),
        **summary,
        "input_paths": {
            "composite_index": composite_path.as_posix(),
            "boundaries": boundaries_path.as_posix(),
            "priority_areas": priority_path.as_posix(),
            "environmental_overlay": overlay_path.as_posix(),
            "policy_matrix": policy_matrix_path.as_posix(),
            "category_assessment": category_assessment_path.as_posix(),
            "major_category_assessment": major_category_assessment_path.as_posix(),
            "indicator_scores": indicator_scores_path.as_posix(),
            "policy_catalog": policy_catalog_path.as_posix(),
        },
        "input_sha256": {
            "composite_index": sha256_file(composite_path),
            "boundaries": sha256_file(boundaries_path),
            "priority_areas": sha256_file(priority_path),
            "environmental_overlay": sha256_file(overlay_path),
            "policy_matrix": sha256_file(policy_matrix_path),
            "category_assessment": sha256_file(category_assessment_path),
            "major_category_assessment": sha256_file(major_category_assessment_path),
            "indicator_scores": sha256_file(indicator_scores_path),
            "policy_catalog": sha256_file(policy_catalog_path),
        },
        "output_paths": {
            "svg": svg_output.as_posix(),
            "pdf": pdf_output.as_posix(),
            "png": png_output.as_posix(),
            "action_profile_csv": profile_output.as_posix(),
            "interactive_action_map": html_output.as_posix(),
        },
        "output_sha256": {
            "svg": sha256_file(svg_output),
            "pdf": sha256_file(pdf_output),
            "png": sha256_file(png_output),
            "action_profile_csv": sha256_file(profile_output),
            "interactive_action_map": sha256_file(html_output),
        },
        "interpretation": (
            "Public-data experimental screening; not an official index, causal estimate, "
            "individual eligibility rule, or final funding decision"
        ),
    }
    write_json(report_path, report)
    return report


def main() -> int:
    """Run the infographic pipeline from command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--composite-index", type=Path, default=DEFAULT_COMPOSITE)
    parser.add_argument("--boundaries", type=Path, default=DEFAULT_BOUNDARIES)
    parser.add_argument("--priority-areas", type=Path, default=DEFAULT_PRIORITY_OUTPUT)
    parser.add_argument("--environmental-overlay", type=Path, default=DEFAULT_OVERLAY)
    parser.add_argument("--policy-matrix", type=Path, default=DEFAULT_POLICY_MATRIX)
    parser.add_argument("--category-assessment", type=Path, default=DEFAULT_CATEGORY_ASSESSMENT)
    parser.add_argument(
        "--major-category-assessment",
        type=Path,
        default=DEFAULT_MAJOR_CATEGORY_ASSESSMENT,
    )
    parser.add_argument("--indicator-scores", type=Path, default=DEFAULT_INDICATOR_SCORES)
    parser.add_argument("--policy-catalog", type=Path, default=DEFAULT_POLICY_CATALOG)
    parser.add_argument("--svg-output", type=Path, default=DEFAULT_SVG_OUTPUT)
    parser.add_argument("--pdf-output", type=Path, default=DEFAULT_PDF_OUTPUT)
    parser.add_argument("--png-output", type=Path, default=DEFAULT_PNG_OUTPUT)
    parser.add_argument("--profile-output", type=Path, default=DEFAULT_PROFILE_OUTPUT)
    parser.add_argument("--html-output", type=Path, default=DEFAULT_HTML_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    report = run(
        args.composite_index,
        args.boundaries,
        args.priority_areas,
        args.environmental_overlay,
        args.policy_matrix,
        args.category_assessment,
        args.major_category_assessment,
        args.indicator_scores,
        args.policy_catalog,
        args.svg_output,
        args.pdf_output,
        args.png_output,
        args.profile_output,
        args.html_output,
        args.report,
    )
    print(
        f"rendered {report['page_count']}-page infographic with "
        f"{report['priority_area_count']} priority areas"
    )
    return 0
