from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from busan_imd.cluster_analysis import DOMAINS, build, run


def priority_input() -> pd.DataFrame:
    rows = []
    patterns = (
        {"income": 9.0, "employment": 7.0},
        {"health": 9.0, "living_environment": 7.0},
        {"education": 9.0, "housing_access": 7.0},
    )
    for index in range(21):
        pattern = patterns[index // 7]
        row = {
            "admin_dong_code": f"{index:03d}",
            "sigungu_name": "District",
            "admin_dong_name": f"Dong {index}",
            "b_imd_score_0_100": 80 - index,
            "b_imd_rank": index + 1,
            "b_imd_decile": 1,
        }
        for domain_index, domain in enumerate(DOMAINS):
            row[f"{domain}_excess_points"] = pattern.get(domain, -2.0) + (
                (index % 7) - 3
            ) * 0.03 * (domain_index + 1)
        rows.append(row)
    return pd.DataFrame(rows)


def test_build_selects_stable_interpretable_clusters() -> None:
    assignments, metrics, report = build(priority_input())

    assert len(assignments) == 21
    assert report["selected_cluster_count"] == 3
    assert report["recommended_for_policy_typology"] is True
    assert set(assignments["cluster_id"]) == {"type_1", "type_2", "type_3"}
    assert assignments.groupby("cluster_id").size().tolist() == [7, 7, 7]
    assert len(report["cluster_summaries"]) == 3
    assert report["stability_evaluation"]["repeated_fit_n_init"] == 20
    assert assignments["cluster_label"].nunique() == 3
    assert metrics["cluster_count"].tolist() == [2, 3, 4, 5, 6]


def test_build_is_deterministic() -> None:
    first_assignments, first_metrics, first_report = build(priority_input())
    second_assignments, second_metrics, second_report = build(priority_input())

    pd.testing.assert_frame_equal(first_assignments, second_assignments)
    assert first_metrics["cluster_count"].tolist() == second_metrics["cluster_count"].tolist()
    assert first_report["selected_cluster_count"] == second_report["selected_cluster_count"]
    assert first_report["cluster_summaries"] == second_report["cluster_summaries"]


def test_build_rejects_invalid_priority_population() -> None:
    frame = priority_input()

    with pytest.raises(ValueError, match="21 unique"):
        build(frame.iloc[:-1])
    with pytest.raises(ValueError, match="decile-1"):
        build(frame.assign(b_imd_decile=np.where(frame.index == 0, 2, 1)))
    with pytest.raises(ValueError, match="missing columns"):
        build(frame.drop(columns="income_excess_points"))


def test_run_creates_independent_output_directories(tmp_path) -> None:
    priority_path = tmp_path / "input" / "priority.csv"
    assignment_path = tmp_path / "assignments" / "clusters.csv"
    metrics_path = tmp_path / "metrics" / "candidates.csv"
    report_path = tmp_path / "reports" / "cluster.json"
    priority_path.parent.mkdir(parents=True)
    priority_input().to_csv(priority_path, index=False)

    report = run(priority_path, assignment_path, metrics_path, report_path)

    assert assignment_path.is_file()
    assert metrics_path.is_file()
    assert report_path.is_file()
    assert report["selected_cluster_count"] == 3
