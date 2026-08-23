from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from busan_imd.cluster_analysis import build

DOMAINS = (
    "education",
    "employment",
    "health",
    "housing_access",
    "income",
    "living_environment",
)


def domain_scores() -> pd.DataFrame:
    size = 206
    group = np.repeat([10.0, 90.0], size // 2)
    frame = pd.DataFrame(
        {
            "admin_dong_code": [f"{index:03d}" for index in range(size)],
            "sido_name": ["Busan"] * size,
            "sigungu_name": ["District"] * size,
            "admin_dong_name": [f"Dong {index}" for index in range(size)],
        }
    )
    for index, domain in enumerate(DOMAINS):
        frame[f"{domain}_score_0_100"] = group + index * 0.001
    return frame


def test_build_adopts_a_clear_stable_two_cluster_solution() -> None:
    evaluation, profiles, assignments, report = build(
        domain_scores(), cluster_counts=[2], bootstrap_iterations=10
    )

    assert evaluation.loc[0, "silhouette_score"] == pytest.approx(1.0)
    assert bool(evaluation.loc[0, "passes_adoption_gate"]) is True
    assert len(profiles) == 2
    assert set(assignments["cluster_label"]) == {1, 2}
    assert report["adoption_decision"] == "adopted"
    assert report["selected_cluster_count"] == 2
    assert report["assignment_record_count"] == 206


def test_build_withholds_assignments_when_a_gate_fails() -> None:
    evaluation, _, assignments, report = build(
        domain_scores(),
        cluster_counts=[2],
        bootstrap_iterations=10,
        gates={"minimum_silhouette": 1.01},
    )

    assert bool(evaluation.loc[0, "passes_adoption_gate"]) is False
    assert assignments.empty
    assert report["adoption_decision"] == "not_adopted"
    assert report["policy_typology_eligible"] is False
    assert report["assignment_record_count"] == 0


def test_build_rejects_invalid_domain_score_inputs() -> None:
    frame = domain_scores()

    with pytest.raises(ValueError, match="exactly six"):
        build(
            frame.drop(columns="income_score_0_100"),
            cluster_counts=[2],
            bootstrap_iterations=10,
        )

    invalid = frame.copy()
    invalid.loc[0, "income_score_0_100"] = np.nan
    with pytest.raises(ValueError, match="complete and finite"):
        build(invalid, cluster_counts=[2], bootstrap_iterations=10)
