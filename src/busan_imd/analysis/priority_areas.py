"""Explain the domain and indicator drivers of the 2025 B-IMD priority areas."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from busan_imd.analysis.composite_index import DEFAULT_OUTPUT as DEFAULT_COMPOSITE
from busan_imd.analysis.composite_index import DEFAULT_SPEC as DEFAULT_COMPOSITE_SPEC
from busan_imd.analysis.composite_index import DomainWeight, load_weights
from busan_imd.analysis.domain_scores import DEFAULT_OUTPUT_DIR, IDENTITY_COLUMNS
from busan_imd.core.artifacts import sha256_file, write_json

DEFAULT_INDICATOR_SCORES = DEFAULT_OUTPUT_DIR / "busan_admin_dong_indicator_scores_2025.csv"
DEFAULT_PRIORITY_OUTPUT = DEFAULT_OUTPUT_DIR / "busan_admin_dong_priority_areas_2025.csv"
DEFAULT_CONTRIBUTION_OUTPUT = (
    DEFAULT_OUTPUT_DIR / "busan_admin_dong_priority_indicator_contributions_2025.csv"
)
DEFAULT_REPORT = Path("docs/data/manifests/PRIORITY_AREA_REPORT_2025.json")


def _validate_inputs(
    composite: pd.DataFrame,
    indicator_scores: pd.DataFrame,
    weights: list[DomainWeight],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Validate and normalize the two upstream scoring artifacts."""
    weight_by_domain = pd.Series(
        {item.domain: item.scored_model_weight for item in weights}, dtype=float
    )
    if (
        not weights
        or len(weight_by_domain) != len(weights)
        or not np.isclose(weight_by_domain.sum(), 1.0)
        or (weight_by_domain <= 0).any()
    ):
        raise ValueError("Domain weights must be unique, positive, and sum to one")

    codes = composite["admin_dong_code"].astype(str)
    if len(composite) != 206 or codes.duplicated().any():
        raise ValueError("Priority-area analysis requires 206 unique composite rows")
    required_composite = {
        *IDENTITY_COLUMNS,
        "b_imd_score_0_100",
        "b_imd_rank",
        "b_imd_decile",
        *(f"{domain}_score_0_100" for domain in weight_by_domain.index),
    }
    missing_composite = sorted(required_composite - set(composite.columns))
    if missing_composite:
        raise ValueError(f"Composite input is missing columns: {missing_composite}")

    required_indicator = {
        "admin_dong_code",
        "sigungu_name",
        "admin_dong_name",
        "domain",
        "indicator",
        "source_dataset_id",
        "raw_value",
        "deprivation_percentile_0_100",
        "within_domain_weight",
        "evidence_status",
    }
    missing_indicator = sorted(required_indicator - set(indicator_scores.columns))
    if missing_indicator:
        raise ValueError(f"Indicator input is missing columns: {missing_indicator}")
    indicator_codes = indicator_scores["admin_dong_code"].astype(str)
    if set(indicator_codes) != set(codes):
        raise ValueError("Indicator and composite inputs must cover the same dong codes")
    if indicator_scores.duplicated(["admin_dong_code", "indicator"]).any():
        raise ValueError("Indicator rows must be unique by dong and indicator")
    if set(indicator_scores["domain"]) != set(weight_by_domain.index):
        raise ValueError("Indicator rows must cover every weighted domain")

    composite = composite.copy()
    composite["admin_dong_code"] = codes
    indicator_scores = indicator_scores.copy()
    indicator_scores["admin_dong_code"] = indicator_codes
    numeric = indicator_scores[["deprivation_percentile_0_100", "within_domain_weight"]].apply(
        pd.to_numeric, errors="raise"
    )
    if not np.isfinite(numeric).all().all():
        raise ValueError("Indicator scores and weights must be finite")
    indicator_values = numeric["deprivation_percentile_0_100"]
    if ((indicator_values < 0) | (indicator_values > 100)).any():
        raise ValueError("Indicator scores must be between 0 and 100")
    return composite, indicator_scores


def build(
    composite: pd.DataFrame,
    indicator_scores: pd.DataFrame,
    weights: list[DomainWeight],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Build priority-area profiles and their indicator-level explanations."""
    composite, indicator_scores = _validate_inputs(composite, indicator_scores, weights)
    weight_by_domain = pd.Series(
        {item.domain: item.scored_model_weight for item in weights}, dtype=float
    )
    priority = composite.loc[composite["b_imd_decile"] == 1].copy()
    if len(priority) != 21:
        raise ValueError("The 206-dong rank contract requires 21 first-decile priority areas")

    domain_records: list[pd.DataFrame] = []
    for domain, domain_weight in weight_by_domain.items():
        score_column = f"{domain}_score_0_100"
        domain_median = float(composite[score_column].median())
        frame = composite[
            IDENTITY_COLUMNS + ["b_imd_score_0_100", "b_imd_rank", "b_imd_decile", score_column]
        ].copy()
        frame["domain"] = domain
        frame["domain_score_0_100"] = frame.pop(score_column)
        frame["domain_weight"] = domain_weight
        frame["composite_contribution_points"] = frame["domain_score_0_100"] * domain_weight
        frame["city_domain_median_0_100"] = domain_median
        frame["weighted_excess_over_city_median"] = (
            frame["domain_score_0_100"] - domain_median
        ) * domain_weight
        domain_records.append(frame)
    domain_contributions = pd.concat(domain_records, ignore_index=True)

    calculated = domain_contributions.groupby("admin_dong_code")[
        "composite_contribution_points"
    ].sum()
    expected = composite.set_index("admin_dong_code")["b_imd_score_0_100"]
    if not np.allclose(calculated.sort_index(), expected.sort_index(), atol=2e-5):
        raise ValueError("Domain contributions must sum to the published composite score")

    priority_domains = domain_contributions[
        domain_contributions["admin_dong_code"].isin(priority["admin_dong_code"])
    ].copy()
    priority_domains = priority_domains.sort_values(
        ["admin_dong_code", "weighted_excess_over_city_median", "domain"],
        ascending=[True, False, True],
        kind="stable",
    )
    leading_domain = priority_domains.groupby("admin_dong_code", sort=False).first()
    priority = priority.merge(
        leading_domain[["domain", "domain_score_0_100", "weighted_excess_over_city_median"]].rename(
            columns={
                "domain": "leading_domain",
                "domain_score_0_100": "leading_domain_score_0_100",
                "weighted_excess_over_city_median": "leading_domain_excess_points",
            }
        ),
        left_on="admin_dong_code",
        right_index=True,
        how="left",
        validate="one_to_one",
    )
    for domain in weight_by_domain.index:
        indexed = priority_domains[priority_domains["domain"] == domain].set_index(
            "admin_dong_code"
        )
        priority[f"{domain}_contribution_points"] = priority["admin_dong_code"].map(
            indexed["composite_contribution_points"]
        )
        priority[f"{domain}_excess_points"] = priority["admin_dong_code"].map(
            indexed["weighted_excess_over_city_median"]
        )

    indicators = indicator_scores.merge(
        weight_by_domain.rename("domain_weight"),
        left_on="domain",
        right_index=True,
        how="left",
        validate="many_to_one",
    )
    indicators["effective_composite_weight"] = (
        indicators["within_domain_weight"] * indicators["domain_weight"]
    )
    indicators["composite_contribution_points"] = (
        indicators["deprivation_percentile_0_100"] * indicators["effective_composite_weight"]
    )
    indicator_totals = indicators.groupby("admin_dong_code")["composite_contribution_points"].sum()
    if not np.allclose(indicator_totals.sort_index(), expected.sort_index(), atol=2e-5):
        raise ValueError("Indicator contributions must sum to the published composite score")
    indicator_medians = indicators.groupby("indicator")["deprivation_percentile_0_100"].median()
    indicators["city_indicator_median_0_100"] = indicators["indicator"].map(indicator_medians)
    indicators["weighted_excess_over_city_median"] = (
        indicators["deprivation_percentile_0_100"] - indicators["city_indicator_median_0_100"]
    ) * indicators["effective_composite_weight"]
    indicators = indicators.merge(
        composite[IDENTITY_COLUMNS + ["b_imd_score_0_100", "b_imd_rank", "b_imd_decile"]],
        on=["admin_dong_code", "sigungu_name", "admin_dong_name"],
        how="left",
        validate="many_to_one",
    )
    contributions = indicators[indicators["b_imd_decile"] == 1].copy()
    contributions["contribution_share_of_composite"] = (
        contributions["composite_contribution_points"] / contributions["b_imd_score_0_100"]
    )
    contributions = contributions.sort_values(
        ["b_imd_rank", "weighted_excess_over_city_median", "indicator"],
        ascending=[True, False, True],
        kind="stable",
    )
    contributions["driver_rank_within_area"] = (
        contributions.groupby("admin_dong_code").cumcount() + 1
    )

    leading_indicators = contributions[contributions["driver_rank_within_area"] == 1].set_index(
        "admin_dong_code"
    )
    priority["leading_indicator"] = priority["admin_dong_code"].map(leading_indicators["indicator"])
    priority["leading_indicator_excess_points"] = priority["admin_dong_code"].map(
        leading_indicators["weighted_excess_over_city_median"]
    )
    priority = priority.sort_values("b_imd_rank", kind="stable").reset_index(drop=True)

    leading_domain_counts = {
        str(domain): int(count)
        for domain, count in priority["leading_domain"].value_counts().sort_index().items()
    }
    top_areas = []
    for row in priority.head(10).itertuples(index=False):
        top_drivers = contributions[contributions["admin_dong_code"] == row.admin_dong_code].head(3)
        top_areas.append(
            {
                "admin_dong_code": row.admin_dong_code,
                "sigungu_name": row.sigungu_name,
                "admin_dong_name": row.admin_dong_name,
                "b_imd_score_0_100": round(float(row.b_imd_score_0_100), 6),
                "b_imd_rank": int(row.b_imd_rank),
                "leading_domain": row.leading_domain,
                "leading_indicator": row.leading_indicator,
                "top_indicator_drivers": [
                    {
                        "indicator": item.indicator,
                        "domain": item.domain,
                        "weighted_excess_over_city_median": round(
                            float(item.weighted_excess_over_city_median), 6
                        ),
                    }
                    for item in top_drivers.itertuples(index=False)
                ],
            }
        )
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "reference_year": 2025,
        "record_count": len(composite),
        "priority_area_rule": "B-IMD decile 1",
        "priority_area_count": len(priority),
        "indicator_count": int(indicator_scores["indicator"].nunique()),
        "contribution_definition": (
            "indicator percentile score multiplied by within-domain and composite-domain weights"
        ),
        "driver_definition": (
            "largest positive weighted contribution above the citywide indicator or domain median"
        ),
        "score_direction": "higher means greater relative deprivation",
        "leading_domain_counts": leading_domain_counts,
        "top_10_priority_areas": top_areas,
    }
    return priority, contributions, report


def run(
    composite_path: Path = DEFAULT_COMPOSITE,
    indicator_scores_path: Path = DEFAULT_INDICATOR_SCORES,
    weight_spec_path: Path = DEFAULT_COMPOSITE_SPEC,
    priority_output_path: Path = DEFAULT_PRIORITY_OUTPUT,
    contribution_output_path: Path = DEFAULT_CONTRIBUTION_OUTPUT,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    """Read upstream scores and write deterministic priority-area artifacts."""
    composite = pd.read_csv(composite_path, dtype={"admin_dong_code": str})
    indicator_scores = pd.read_csv(indicator_scores_path, dtype={"admin_dong_code": str})
    weights = load_weights(weight_spec_path)
    priority, contributions, report = build(composite, indicator_scores, weights)
    priority_output_path.parent.mkdir(parents=True, exist_ok=True)
    priority.to_csv(priority_output_path, index=False, encoding="utf-8-sig")
    contributions.to_csv(contribution_output_path, index=False, encoding="utf-8-sig")
    report.update(
        {
            "input_paths": {
                "composite": composite_path.as_posix(),
                "indicator_scores": indicator_scores_path.as_posix(),
                "weight_spec": weight_spec_path.as_posix(),
            },
            "input_sha256": {
                "composite": sha256_file(composite_path),
                "indicator_scores": sha256_file(indicator_scores_path),
                "weight_spec": sha256_file(weight_spec_path),
            },
            "output_paths": {
                "priority_areas": priority_output_path.as_posix(),
                "indicator_contributions": contribution_output_path.as_posix(),
            },
            "output_sha256": {
                "priority_areas": sha256_file(priority_output_path),
                "indicator_contributions": sha256_file(contribution_output_path),
            },
        }
    )
    write_json(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--composite", type=Path, default=DEFAULT_COMPOSITE)
    parser.add_argument("--indicator-scores", type=Path, default=DEFAULT_INDICATOR_SCORES)
    parser.add_argument("--weight-spec", type=Path, default=DEFAULT_COMPOSITE_SPEC)
    parser.add_argument("--priority-output", type=Path, default=DEFAULT_PRIORITY_OUTPUT)
    parser.add_argument("--contribution-output", type=Path, default=DEFAULT_CONTRIBUTION_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run(
        args.composite,
        args.indicator_scores,
        args.weight_spec,
        args.priority_output,
        args.contribution_output,
        args.report,
    )
    print(
        f"explained {report['priority_area_count']} priority areas using "
        f"{report['indicator_count']} indicators"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
