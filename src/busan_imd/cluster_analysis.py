"""Evaluate whether 2025 domain scores support a policy-usable cluster typology."""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.preprocessing import StandardScaler

from busan_imd.core.artifacts import sha256_file, write_json
from busan_imd.domain_scores import DEFAULT_OUTPUT_DIR, IDENTITY_COLUMNS

DEFAULT_DOMAIN_SCORES = DEFAULT_OUTPUT_DIR / "busan_admin_dong_domain_scores_2025.csv"
DEFAULT_EVALUATION_OUTPUT = DEFAULT_OUTPUT_DIR / "cluster_candidate_evaluation_2025.csv"
DEFAULT_PROFILE_OUTPUT = DEFAULT_OUTPUT_DIR / "cluster_candidate_profiles_2025.csv"
DEFAULT_ASSIGNMENT_OUTPUT = DEFAULT_OUTPUT_DIR / "admin_dong_cluster_typology_2025.csv"
DEFAULT_REPORT = Path("docs/data/manifests/CLUSTER_ANALYSIS_REPORT_2025.json")
DEFAULT_CLUSTER_COUNTS = tuple(range(2, 7))
DEFAULT_BOOTSTRAP_ITERATIONS = 100
DEFAULT_RANDOM_STATE = 2025
DEFAULT_GATES = {
    "minimum_silhouette": 0.25,
    "minimum_bootstrap_median_ari": 0.70,
    "minimum_bootstrap_p10_ari": 0.50,
    "minimum_cluster_size": 10,
    "minimum_distinctive_cluster_rate": 1.0,
    "distinctive_centroid_absolute_z": 0.50,
}


def _domain_columns(frame: pd.DataFrame) -> list[str]:
    columns = sorted(column for column in frame if column.endswith("_score_0_100"))
    if len(columns) != 6:
        raise ValueError("Cluster analysis requires exactly six domain-score columns")
    return columns


def _validate(frame: pd.DataFrame, cluster_counts: tuple[int, ...]) -> list[str]:
    if len(frame) != 206 or frame["admin_dong_code"].astype(str).duplicated().any():
        raise ValueError("Cluster analysis requires 206 unique administrative-dong rows")
    missing_identity = sorted(set(IDENTITY_COLUMNS) - set(frame.columns))
    if missing_identity:
        raise ValueError(f"Domain-score input is missing identity columns: {missing_identity}")
    if not cluster_counts or len(set(cluster_counts)) != len(cluster_counts):
        raise ValueError("Candidate cluster counts must be non-empty and unique")
    if min(cluster_counts) < 2 or max(cluster_counts) >= len(frame):
        raise ValueError("Candidate cluster counts must be between 2 and record_count - 1")
    columns = _domain_columns(frame)
    values = frame[columns].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(values).all().all():
        raise ValueError("Domain scores must be complete and finite")
    if ((values < 0) | (values > 100)).any().any():
        raise ValueError("Domain scores must be between 0 and 100")
    if (values.nunique() <= 1).any():
        raise ValueError("Every domain score must vary across administrative dongs")
    return columns


def _canonical_labels(labels: np.ndarray, centroids: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Order labels from higher overall standardized deprivation to lower."""
    order = sorted(
        range(len(centroids)),
        key=lambda index: (-float(centroids[index].mean()), *(-centroids[index]).tolist()),
    )
    mapping = {old: new + 1 for new, old in enumerate(order)}
    canonical = np.array([mapping[int(label)] for label in labels], dtype=int)
    return canonical, centroids[order]


def build(
    domain_scores: pd.DataFrame,
    cluster_counts: Iterable[int] = DEFAULT_CLUSTER_COUNTS,
    bootstrap_iterations: int = DEFAULT_BOOTSTRAP_ITERATIONS,
    random_state: int = DEFAULT_RANDOM_STATE,
    gates: dict[str, float] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Evaluate K-means candidates and decide whether any typology is admissible."""
    candidate_counts = tuple(int(value) for value in cluster_counts)
    domain_columns = _validate(domain_scores, candidate_counts)
    if bootstrap_iterations < 10:
        raise ValueError("At least 10 bootstrap iterations are required")
    gate = {**DEFAULT_GATES, **(gates or {})}
    values = domain_scores[domain_columns].astype(float)
    standardized = StandardScaler().fit_transform(values)
    domains = [column.removesuffix("_score_0_100") for column in domain_columns]

    evaluation_rows: list[dict[str, Any]] = []
    profile_rows: list[dict[str, Any]] = []
    labels_by_count: dict[int, np.ndarray] = {}
    for cluster_count in candidate_counts:
        model = KMeans(
            n_clusters=cluster_count,
            random_state=random_state,
            n_init=50,
        ).fit(standardized)
        labels, centroids = _canonical_labels(model.labels_, model.cluster_centers_)
        labels_by_count[cluster_count] = labels
        sizes = np.bincount(labels, minlength=cluster_count + 1)[1:]

        rng = np.random.default_rng(random_state + cluster_count * 1000)
        bootstrap_ari: list[float] = []
        for iteration in range(bootstrap_iterations):
            sample = rng.integers(0, len(standardized), len(standardized))
            bootstrap_model = KMeans(
                n_clusters=cluster_count,
                random_state=random_state + iteration,
                n_init=10,
            ).fit(standardized[sample])
            predicted = bootstrap_model.predict(standardized)
            bootstrap_ari.append(float(adjusted_rand_score(labels, predicted)))

        distinctive = np.max(np.abs(centroids), axis=1) >= gate[
            "distinctive_centroid_absolute_z"
        ]
        silhouette = float(silhouette_score(standardized, labels))
        bootstrap_median = float(np.median(bootstrap_ari))
        bootstrap_p10 = float(np.quantile(bootstrap_ari, 0.10))
        distinctive_rate = float(distinctive.mean())
        passed = (
            silhouette >= gate["minimum_silhouette"]
            and bootstrap_median >= gate["minimum_bootstrap_median_ari"]
            and bootstrap_p10 >= gate["minimum_bootstrap_p10_ari"]
            and int(sizes.min()) >= gate["minimum_cluster_size"]
            and distinctive_rate >= gate["minimum_distinctive_cluster_rate"]
        )
        evaluation_rows.append(
            {
                "candidate_cluster_count": cluster_count,
                "silhouette_score": round(silhouette, 6),
                "davies_bouldin_score": round(
                    float(davies_bouldin_score(standardized, labels)), 6
                ),
                "calinski_harabasz_score": round(
                    float(calinski_harabasz_score(standardized, labels)), 6
                ),
                "minimum_cluster_size": int(sizes.min()),
                "maximum_cluster_size": int(sizes.max()),
                "bootstrap_median_ari": round(bootstrap_median, 6),
                "bootstrap_p10_ari": round(bootstrap_p10, 6),
                "distinctive_cluster_rate": round(distinctive_rate, 6),
                "passes_adoption_gate": bool(passed),
            }
        )

        for label in range(1, cluster_count + 1):
            membership = labels == label
            centroid = centroids[label - 1]
            high_index = int(np.argmax(centroid))
            low_index = int(np.argmin(centroid))
            row: dict[str, Any] = {
                "candidate_cluster_count": cluster_count,
                "candidate_cluster_label": label,
                "record_count": int(membership.sum()),
                "leading_high_domain": domains[high_index],
                "leading_high_domain_z": round(float(centroid[high_index]), 6),
                "leading_low_domain": domains[low_index],
                "leading_low_domain_z": round(float(centroid[low_index]), 6),
                "is_distinctive": bool(distinctive[label - 1]),
            }
            for index, domain in enumerate(domains):
                row[f"{domain}_centroid_z"] = round(float(centroid[index]), 6)
                row[f"{domain}_mean_0_100"] = round(
                    float(values.loc[membership, domain_columns[index]].mean()), 6
                )
            profile_rows.append(row)

    evaluation = pd.DataFrame(evaluation_rows).sort_values(
        "candidate_cluster_count", kind="stable"
    )
    profiles = pd.DataFrame(profile_rows).sort_values(
        ["candidate_cluster_count", "candidate_cluster_label"], kind="stable"
    )
    passing = evaluation[evaluation["passes_adoption_gate"]]
    selected = (
        None
        if passing.empty
        else int(
            passing.sort_values(
                ["silhouette_score", "bootstrap_median_ari", "candidate_cluster_count"],
                ascending=[False, False, True],
                kind="stable",
            ).iloc[0]["candidate_cluster_count"]
        )
    )
    best = evaluation.sort_values(
        ["silhouette_score", "bootstrap_median_ari", "candidate_cluster_count"],
        ascending=[False, False, True],
        kind="stable",
    ).iloc[0]
    assignment_columns = [
        *IDENTITY_COLUMNS,
        "selected_cluster_count",
        "cluster_label",
        "policy_typology_eligible",
    ]
    if selected is None:
        assignments = pd.DataFrame(columns=assignment_columns)
    else:
        assignments = domain_scores[IDENTITY_COLUMNS].copy()
        assignments["selected_cluster_count"] = selected
        assignments["cluster_label"] = labels_by_count[selected]
        assignments["policy_typology_eligible"] = True
        assignments = assignments[assignment_columns]
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "reference_year": 2025,
        "record_count": len(domain_scores),
        "domains": domains,
        "algorithm": "KMeans on six StandardScaler-transformed domain scores",
        "candidate_cluster_counts": list(candidate_counts),
        "bootstrap_iterations": bootstrap_iterations,
        "random_state": random_state,
        "adoption_gates": gate,
        "adoption_decision": "adopted" if selected is not None else "not_adopted",
        "policy_typology_eligible": selected is not None,
        "selected_cluster_count": selected,
        "best_candidate_by_silhouette": int(best["candidate_cluster_count"]),
        "best_candidate_silhouette": float(best["silhouette_score"]),
        "best_candidate_bootstrap_median_ari": float(best["bootstrap_median_ari"]),
        "decision_rationale": (
            "At least one candidate passed every documented separation, stability, size, "
            "and distinctiveness gate."
            if selected is not None
            else "No candidate passed every documented separation, stability, size, and "
            "distinctiveness gate; cluster labels must not be used for policy typology."
        ),
        "assignment_record_count": len(assignments),
    }
    return (
        evaluation.reset_index(drop=True),
        profiles.reset_index(drop=True),
        assignments.reset_index(drop=True),
        report,
    )


def run(
    domain_scores_path: Path = DEFAULT_DOMAIN_SCORES,
    evaluation_output_path: Path = DEFAULT_EVALUATION_OUTPUT,
    profile_output_path: Path = DEFAULT_PROFILE_OUTPUT,
    assignment_output_path: Path = DEFAULT_ASSIGNMENT_OUTPUT,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    """Read domain scores and write candidate diagnostics without policy labels."""
    domain_scores = pd.read_csv(domain_scores_path, dtype={"admin_dong_code": str})
    evaluation, profiles, assignments, report = build(domain_scores)
    evaluation_output_path.parent.mkdir(parents=True, exist_ok=True)
    evaluation.to_csv(evaluation_output_path, index=False, encoding="utf-8-sig")
    profiles.to_csv(profile_output_path, index=False, encoding="utf-8-sig")
    assignments.to_csv(assignment_output_path, index=False, encoding="utf-8-sig")
    report.update(
        {
            "domain_scores_path": domain_scores_path.as_posix(),
            "domain_scores_sha256": sha256_file(domain_scores_path),
            "output_paths": {
                "candidate_evaluation": evaluation_output_path.as_posix(),
                "candidate_profiles": profile_output_path.as_posix(),
                "assignments": assignment_output_path.as_posix(),
            },
            "output_sha256": {
                "candidate_evaluation": sha256_file(evaluation_output_path),
                "candidate_profiles": sha256_file(profile_output_path),
                "assignments": sha256_file(assignment_output_path),
            },
        }
    )
    write_json(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain-scores", type=Path, default=DEFAULT_DOMAIN_SCORES)
    parser.add_argument("--evaluation-output", type=Path, default=DEFAULT_EVALUATION_OUTPUT)
    parser.add_argument("--profile-output", type=Path, default=DEFAULT_PROFILE_OUTPUT)
    parser.add_argument("--assignment-output", type=Path, default=DEFAULT_ASSIGNMENT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run(
        args.domain_scores,
        args.evaluation_output,
        args.profile_output,
        args.assignment_output,
        args.report,
    )
    print(
        f"evaluated {len(report['candidate_cluster_counts'])} cluster candidates; "
        f"decision={report['adoption_decision']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
