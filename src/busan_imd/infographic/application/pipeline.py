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
    DEFAULT_AED_POINTS,
    DEFAULT_BOUNDARIES,
    DEFAULT_CANDIDATE_PROFILE,
    DEFAULT_CATEGORY_ASSESSMENT,
    DEFAULT_CITY_PARKS,
    DEFAULT_COMPOSITE,
    DEFAULT_CONSUMER_SALES,
    DEFAULT_CONSUMER_SALES_BY_CATEGORY,
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
    DEFAULT_SAFETY_RISK_AREAS,
    DEFAULT_SVG_OUTPUT,
    DEFAULT_TRAFFIC_CITYWIDE_TREND,
    DEFAULT_TRAFFIC_DISTRICT_STATISTICS,
    DEFAULT_TRAFFIC_HOTSPOTS,
)
from busan_imd.infographic.domain.profiles import build_action_profiles
from busan_imd.infographic.presentation.rendering import render, write_action_map
from busan_imd.processing.standardization import load_aed_points


def add_park_context(
    context: pd.DataFrame,
    boundaries: gpd.GeoDataFrame,
    parks: pd.DataFrame,
) -> pd.DataFrame:
    """Add current park proximity context without changing the 2025 score."""
    points = gpd.GeoDataFrame(
        parks.copy(),
        geometry=gpd.points_from_xy(
            pd.to_numeric(parks["longitude"], errors="raise"),
            pd.to_numeric(parks["latitude"], errors="raise"),
        ),
        crs="EPSG:4326",
    ).to_crs(boundaries.crs)
    lookup = boundaries[["adm_cd", "geometry"]].copy()
    lookup["adm_cd"] = lookup["adm_cd"].astype(str)
    mapped = gpd.sjoin(points, lookup, how="left", predicate="within")
    counts = mapped.groupby("adm_cd", observed=True).size()
    centroids = lookup.copy()
    centroids["geometry"] = centroids.geometry.centroid
    nearest = gpd.sjoin_nearest(
        centroids,
        points[["geometry"]],
        how="left",
        distance_col="nearest_park_distance_m_current",
    ).drop_duplicates("adm_cd")
    output = context.copy()
    output["park_count_current"] = output["admin_dong_code"].map(counts).fillna(0).astype(int)
    output = output.merge(
        nearest[["adm_cd", "nearest_park_distance_m_current"]],
        left_on="admin_dong_code",
        right_on="adm_cd",
        how="left",
        validate="one_to_one",
    ).drop(columns="adm_cd")
    return output


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
    traffic_hotspots_path: Path = DEFAULT_TRAFFIC_HOTSPOTS,
    candidate_profile_path: Path = DEFAULT_CANDIDATE_PROFILE,
    consumer_sales_path: Path = DEFAULT_CONSUMER_SALES,
    city_parks_path: Path = DEFAULT_CITY_PARKS,
    safety_risk_areas_path: Path = DEFAULT_SAFETY_RISK_AREAS,
    consumer_sales_by_category_path: Path = DEFAULT_CONSUMER_SALES_BY_CATEGORY,
    aed_points_path: Path = DEFAULT_AED_POINTS,
    traffic_district_statistics_path: Path = DEFAULT_TRAFFIC_DISTRICT_STATISTICS,
    traffic_citywide_trend_path: Path = DEFAULT_TRAFFIC_CITYWIDE_TREND,
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
    traffic_hotspots = pd.read_csv(traffic_hotspots_path)
    reference_context = pd.read_csv(
        candidate_profile_path,
        dtype={"admin_dong_code": str},
    ).merge(
        pd.read_csv(consumer_sales_path, dtype={"admin_dong_code": str}),
        on="admin_dong_code",
        how="left",
        validate="one_to_one",
    )
    reference_context["senior_consumer_minus_living_share_pp_2025_context"] = (
        reference_context["consumer_sales_senior_transaction_share_pct_2025"]
        - reference_context["senior_living_population_share_pct_2025"]
    )
    reference_context["under_30_consumer_minus_living_share_pp_2025_context"] = (
        reference_context["consumer_sales_under_30_transaction_share_pct_2025"]
        - reference_context["under_30_living_population_share_pct_2025"]
    )
    reference_context["living_consumer_age_composition_divergence_pp_2025_context"] = (
        reference_context[
            [
                "senior_consumer_minus_living_share_pp_2025_context",
                "under_30_consumer_minus_living_share_pp_2025_context",
            ]
        ]
        .abs()
        .mean(axis=1)
    )
    reference_context = add_park_context(
        reference_context,
        boundaries,
        pd.read_csv(city_parks_path),
    )
    reference_context["students_per_teacher_within_2000m_2025"] = (
        reference_context["core_school_students_within_2000m_2025"]
        / reference_context["core_school_teachers_within_2000m_2025"].replace(0, pd.NA)
    ).fillna(0)
    district_statistics = pd.read_csv(traffic_district_statistics_path)
    district_statistics = district_statistics[district_statistics["acc_cl_nm"] == "전체사고"].copy()
    district_statistics["sigungu_name"] = district_statistics["sido_sgg_nm"].str.replace(
        "부산광역시 ", "", regex=False
    )
    reference_context = reference_context.merge(
        district_statistics[
            ["sigungu_name", "acc_cnt", "dth_dnv_cnt", "injpsn_cnt", "pop_100k"]
        ].rename(
            columns={
                "acc_cnt": "district_accident_count_2025",
                "dth_dnv_cnt": "district_accident_deaths_2025",
                "injpsn_cnt": "district_accident_injuries_2025",
                "pop_100k": "district_accidents_per_100k_2025",
            }
        ),
        on="sigungu_name",
        how="left",
        validate="many_to_one",
    )
    consumer_sales_by_category = pd.read_csv(
        consumer_sales_by_category_path, dtype={"admin_dong_code": str}
    )
    aed_points, _, _ = load_aed_points(aed_points_path)
    city_parks = pd.read_csv(city_parks_path)
    traffic_citywide_trend = pd.read_csv(traffic_citywide_trend_path, encoding="cp949")
    safety_risk_areas = pd.read_csv(safety_risk_areas_path, encoding="cp949")

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
    map_summary = write_action_map(
        profiles,
        boundaries,
        category_assessments,
        major_category_assessments,
        indicator_scores,
        policy_catalog,
        html_output,
        traffic_hotspots,
        reference_context,
        safety_risk_areas,
        consumer_sales_by_category,
        aed_points,
        city_parks,
        traffic_citywide_trend,
    )
    dashboard_outputs = {
        key: path.as_posix() for key, path in map_summary.pop("dashboard_outputs").items()
    }

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "reference_year": 2025,
        "artifact_status": "submission_draft",
        "format": "A4 portrait one-page infographic",
        "dong_action_profile_count": len(profiles),
        **map_summary,
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
            "traffic_accident_hotspots": traffic_hotspots_path.as_posix(),
            "candidate_profile": candidate_profile_path.as_posix(),
            "consumer_sales": consumer_sales_path.as_posix(),
            "city_parks": city_parks_path.as_posix(),
            "safety_risk_areas": safety_risk_areas_path.as_posix(),
            "consumer_sales_by_category": consumer_sales_by_category_path.as_posix(),
            "aed_points": aed_points_path.as_posix(),
            "traffic_district_statistics": traffic_district_statistics_path.as_posix(),
            "traffic_citywide_trend": traffic_citywide_trend_path.as_posix(),
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
            "traffic_accident_hotspots": sha256_file(traffic_hotspots_path),
            "candidate_profile": sha256_file(candidate_profile_path),
            "consumer_sales": sha256_file(consumer_sales_path),
            "city_parks": sha256_file(city_parks_path),
            "safety_risk_areas": sha256_file(safety_risk_areas_path),
            "consumer_sales_by_category": sha256_file(consumer_sales_by_category_path),
            "aed_points": sha256_file(aed_points_path),
            "traffic_district_statistics": sha256_file(traffic_district_statistics_path),
            "traffic_citywide_trend": sha256_file(traffic_citywide_trend_path),
        },
        "output_paths": {
            "svg": svg_output.as_posix(),
            "pdf": pdf_output.as_posix(),
            "png": png_output.as_posix(),
            "action_profile_csv": profile_output.as_posix(),
            **dashboard_outputs,
        },
        "output_sha256": {
            "svg": sha256_file(svg_output),
            "pdf": sha256_file(pdf_output),
            "png": sha256_file(png_output),
            "action_profile_csv": sha256_file(profile_output),
            **{key: sha256_file(Path(path)) for key, path in dashboard_outputs.items()},
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
    parser.add_argument("--traffic-hotspots", type=Path, default=DEFAULT_TRAFFIC_HOTSPOTS)
    parser.add_argument("--candidate-profile", type=Path, default=DEFAULT_CANDIDATE_PROFILE)
    parser.add_argument("--consumer-sales", type=Path, default=DEFAULT_CONSUMER_SALES)
    parser.add_argument("--city-parks", type=Path, default=DEFAULT_CITY_PARKS)
    parser.add_argument("--safety-risk-areas", type=Path, default=DEFAULT_SAFETY_RISK_AREAS)
    parser.add_argument(
        "--consumer-sales-by-category", type=Path, default=DEFAULT_CONSUMER_SALES_BY_CATEGORY
    )
    parser.add_argument("--aed-points", type=Path, default=DEFAULT_AED_POINTS)
    parser.add_argument(
        "--traffic-district-statistics", type=Path, default=DEFAULT_TRAFFIC_DISTRICT_STATISTICS
    )
    parser.add_argument(
        "--traffic-citywide-trend", type=Path, default=DEFAULT_TRAFFIC_CITYWIDE_TREND
    )
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
        args.traffic_hotspots,
        args.candidate_profile,
        args.consumer_sales,
        args.city_parks,
        args.safety_risk_areas,
        args.consumer_sales_by_category,
        args.aed_points,
        args.traffic_district_statistics,
        args.traffic_citywide_trend,
    )
    print(
        f"rendered {report['page_count']}-page infographic with "
        f"{report['priority_area_count']} priority areas"
    )
    return 0
