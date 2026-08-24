"""Evaluate whether 2025 B-IMD priority areas form usable deprivation types."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from busan_imd.core.artifacts import sha256_file, write_json
from busan_imd.priority_areas import DEFAULT_PRIORITY_OUTPUT

DEFAULT_OUTPUT_DIR = Path("data/processed/scores/2025")
DEFAULT_ASSIGNMENT_OUTPUT = DEFAULT_OUTPUT_DIR / "busan_admin_dong_deprivation_clusters_2025.csv"
DEFAULT_METRICS_OUTPUT = DEFAULT_OUTPUT_DIR / "busan_admin_dong_cluster_metrics_2025.csv"
DEFAULT_REPORT = Path("docs/data/manifests/CLUSTER_ANALYSIS_REPORT_2025.json")

DOMAINS = (
    "income",
    "employment",
    "education",
    "health",
    "housing_access",
    "living_environment",
)
FEATURE_COLUMNS = tuple(f"{domain}_excess_points" for domain in DOMAINS)
RANDOM_STATES = tuple(range(2026, 2046))
REFERENCE_N_INIT = 50
STABILITY_N_INIT = 20
MIN_SILHOUETTE = 0.25
MIN_STABILITY_ARI = 0.80
MIN_CLUSTER_SIZE = 3


def _validate(priority_areas: pd.DataFrame) -> pd.DataFrame:
    required = {
        "admin_dong_code",
        "sigungu_name",
        "admin_dong_name",
        "b_imd_score_0_100",
        "b_imd_rank",
        "b_imd_decile",
        *FEATURE_COLUMNS,
    }
    missing = sorted(required - set(priority_areas.columns))
    if missing:
        raise ValueError(f"Priority-area input is missing columns: {missing}")
    codes = priority_areas["admin_dong_code"].astype(str)
    if len(priority_areas) != 21 or codes.duplicated().any():
        raise ValueError("Cluster analysis requires 21 unique priority-area rows")
    if set(pd.to_numeric(priority_areas["b_imd_decile"], errors="raise")) != {1}:
        raise ValueError("Cluster analysis only accepts B-IMD decile-1 priority areas")
    values = priority_areas[list(FEATURE_COLUMNS)].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(values).all().all():
        raise ValueError("Cluster features must be finite")
    if (values.nunique() <= 1).all():
        raise ValueError("At least one cluster feature must vary")
    frame = priority_areas.copy()
    frame["admin_dong_code"] = codes
    frame[list(FEATURE_COLUMNS)] = values
    return frame


def _candidate_metrics(
    values: np.ndarray, cluster_counts: range
) -> tuple[pd.DataFrame, dict[int, np.ndarray]]:
    records: list[dict[str, Any]] = []
    labels_by_count: dict[int, np.ndarray] = {}
    for cluster_count in cluster_counts:
        reference = KMeans(
            n_clusters=cluster_count,
            random_state=2026,
            n_init=REFERENCE_N_INIT,
        ).fit(values)
        labels = reference.labels_
        labels_by_count[cluster_count] = labels
        stability = []
        for random_state in RANDOM_STATES:
            repeated = KMeans(
                n_clusters=cluster_count,
                random_state=random_state,
                n_init=STABILITY_N_INIT,
            ).fit_predict(values)
            stability.append(adjusted_rand_score(labels, repeated))
        sizes = np.bincount(labels, minlength=cluster_count)
        silhouette = float(silhouette_score(values, labels))
        records.append(
            {
                "cluster_count": cluster_count,
                "silhouette_score": round(silhouette, 6),
                "mean_seed_stability_ari": round(float(np.mean(stability)), 6),
                "minimum_seed_stability_ari": round(float(np.min(stability)), 6),
                "minimum_cluster_size": int(sizes.min()),
                "maximum_cluster_size": int(sizes.max()),
                "passes_quality_gate": bool(
                    silhouette >= MIN_SILHOUETTE
                    and float(np.mean(stability)) >= MIN_STABILITY_ARI
                    and int(sizes.min()) >= MIN_CLUSTER_SIZE
                ),
            }
        )
    return pd.DataFrame(records), labels_by_count


def _canonical_labels(
    labels: np.ndarray,
    original_values: pd.DataFrame,
    standardized_values: pd.DataFrame,
) -> tuple[pd.Series, list[dict[str, Any]]]:
    summaries = []
    for raw_label in sorted(set(labels)):
        member_values = original_values.loc[labels == raw_label]
        means = member_values.mean()
        standardized_means = standardized_values.loc[labels == raw_label].mean()
        ordered = sorted(
            DOMAINS,
            key=lambda domain: (-standardized_means[f"{domain}_excess_points"], domain),
        )
        summaries.append(
            {
                "raw_label": int(raw_label),
                "dominant_domain": ordered[0],
                "secondary_domain": ordered[1],
                "cluster_label": f"{ordered[0]}_{ordered[1]}",
                "member_count": len(member_values),
                "mean_excess_points": {
                    domain: round(float(means[f"{domain}_excess_points"]), 6)
                    for domain in DOMAINS
                },
                "mean_standardized_excess": {
                    domain: round(
                        float(standardized_means[f"{domain}_excess_points"]), 6
                    )
                    for domain in DOMAINS
                },
            }
        )
    summaries.sort(
        key=lambda item: (
            item["cluster_label"],
            tuple(-item["mean_excess_points"][domain] for domain in DOMAINS),
        )
    )
    mapping = {item["raw_label"]: f"type_{index}" for index, item in enumerate(summaries, 1)}
    for item in summaries:
        item["cluster_id"] = mapping[item.pop("raw_label")]
    return pd.Series(labels).map(mapping), summaries


def build(priority_areas: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Evaluate candidate cluster counts and return deterministic type assignments."""
    priority = _validate(priority_areas)
    original_values = priority[list(FEATURE_COLUMNS)]
    standardized = StandardScaler().fit_transform(original_values)
    standardized_values = pd.DataFrame(
        standardized,
        columns=FEATURE_COLUMNS,
        index=original_values.index,
    )
    metrics, labels_by_count = _candidate_metrics(standardized, range(2, 7))
    eligible = metrics[metrics["minimum_cluster_size"] >= MIN_CLUSTER_SIZE]
    selection_pool = eligible if not eligible.empty else metrics
    selected = selection_pool.sort_values(
        ["silhouette_score", "mean_seed_stability_ari", "cluster_count"],
        ascending=[False, False, True],
        kind="stable",
    ).iloc[0]
    selected_count = int(selected["cluster_count"])
    canonical, cluster_summaries = _canonical_labels(
        labels_by_count[selected_count], original_values, standardized_values
    )

    assignments = priority[
        [
            "admin_dong_code",
            "sigungu_name",
            "admin_dong_name",
            "b_imd_score_0_100",
            "b_imd_rank",
            *FEATURE_COLUMNS,
        ]
    ].copy()
    assignments["cluster_id"] = canonical.to_numpy()
    summary_by_id = {item["cluster_id"]: item for item in cluster_summaries}
    assignments["dominant_domain"] = assignments["cluster_id"].map(
        lambda value: summary_by_id[value]["dominant_domain"]
    )
    assignments["secondary_domain"] = assignments["cluster_id"].map(
        lambda value: summary_by_id[value]["secondary_domain"]
    )
    assignments["cluster_label"] = assignments["cluster_id"].map(
        lambda value: summary_by_id[value]["cluster_label"]
    )
    assignments = assignments.sort_values(["cluster_id", "b_imd_rank"], kind="stable")

    recommended = bool(selected["passes_quality_gate"])
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "reference_year": 2025,
        "analysis_population": "21 B-IMD decile-1 priority areas",
        "record_count": len(priority),
        "feature_definition": "weighted domain excess points above the Busan median",
        "features": list(FEATURE_COLUMNS),
        "candidate_cluster_counts": metrics["cluster_count"].astype(int).tolist(),
        "selection_rule": (
            "highest silhouette among candidates with at least three members per cluster; "
            "ties use seed stability then fewer clusters"
        ),
        "selected_cluster_count": selected_count,
        "selected_metrics": {
            "silhouette_score": float(selected["silhouette_score"]),
            "mean_seed_stability_ari": float(selected["mean_seed_stability_ari"]),
            "minimum_seed_stability_ari": float(selected["minimum_seed_stability_ari"]),
            "minimum_cluster_size": int(selected["minimum_cluster_size"]),
            "maximum_cluster_size": int(selected["maximum_cluster_size"]),
        },
        "quality_gate": {
            "minimum_silhouette": MIN_SILHOUETTE,
            "minimum_mean_seed_stability_ari": MIN_STABILITY_ARI,
            "minimum_cluster_size": MIN_CLUSTER_SIZE,
        },
        "stability_evaluation": {
            "random_seed_count": len(RANDOM_STATES),
            "reference_n_init": REFERENCE_N_INIT,
            "repeated_fit_n_init": STABILITY_N_INIT,
            "metric": "adjusted Rand index against the reference fit",
        },
        "recommended_for_policy_typology": recommended,
        "decision": (
            "use_as_exploratory_policy_typology"
            if recommended
            else "do_not_use_as_policy_typology"
        ),
        "cluster_summaries": cluster_summaries,
    }
    return assignments.reset_index(drop=True), metrics, report


def run(
    priority_path: Path = DEFAULT_PRIORITY_OUTPUT,
    assignment_output_path: Path = DEFAULT_ASSIGNMENT_OUTPUT,
    metrics_output_path: Path = DEFAULT_METRICS_OUTPUT,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    """Read COD-19 profiles and write clustering evaluation artifacts."""
    priority = pd.read_csv(priority_path, dtype={"admin_dong_code": str})
    assignments, metrics, report = build(priority)
    assignment_output_path.parent.mkdir(parents=True, exist_ok=True)
    assignments.to_csv(
        assignment_output_path, index=False, encoding="utf-8-sig", lineterminator="\n"
    )
    metrics.to_csv(
        metrics_output_path, index=False, encoding="utf-8-sig", lineterminator="\n"
    )
    report.update(
        {
            "input_path": priority_path.as_posix(),
            "input_sha256": sha256_file(priority_path),
            "output_paths": {
                "assignments": assignment_output_path.as_posix(),
                "candidate_metrics": metrics_output_path.as_posix(),
            },
            "output_sha256": {
                "assignments": sha256_file(assignment_output_path),
                "candidate_metrics": sha256_file(metrics_output_path),
            },
        }
    )
    write_json(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--priority-areas", type=Path, default=DEFAULT_PRIORITY_OUTPUT)
    parser.add_argument("--assignment-output", type=Path, default=DEFAULT_ASSIGNMENT_OUTPUT)
    parser.add_argument("--metrics-output", type=Path, default=DEFAULT_METRICS_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run(
        args.priority_areas,
        args.assignment_output,
        args.metrics_output,
        args.report,
    )
    print(
        f"evaluated k=2..6; selected k={report['selected_cluster_count']} and decision="
        f"{report['decision']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
