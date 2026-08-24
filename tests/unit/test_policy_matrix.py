from __future__ import annotations

import hashlib
import json

import pandas as pd
import pytest

from busan_imd.cluster_analysis import DOMAINS
from busan_imd.policy_matrix import CATALOG_COLUMNS, build, run


def cluster_report() -> dict:
    return {
        "recommended_for_policy_typology": True,
        "decision": "use_as_exploratory_policy_typology",
    }


def inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    assignments = []
    for index in range(21):
        first = index < 5
        dominant = "education" if first else "income"
        secondary = "living_environment" if first else "employment"
        row = {
            "admin_dong_code": f"{index:03d}",
            "sigungu_name": "District",
            "admin_dong_name": f"Dong {index}",
            "b_imd_rank": index + 1,
            "cluster_id": "type_1" if first else "type_2",
            "cluster_label": (
                "education_living_environment" if first else "income_employment"
            ),
            "dominant_domain": dominant,
            "secondary_domain": secondary,
        }
        for domain_index, domain in enumerate(DOMAINS):
            row[f"{domain}_excess_points"] = 10 - domain_index + index / 100
        if first:
            row["living_environment_excess_points"] = -1 - index / 100
        assignments.append(row)

    overlay = pd.DataFrame(
        {
            "admin_dong_code": [f"{index:03d}" for index in range(206)],
            "double_burden": [index in {0, 5, 6} for index in range(206)],
            "particulate_free_b_imd_rank": list(range(1, 207)),
            "particulate_exposure_rank": list(range(206, 0, -1)),
        }
    )
    policies = []
    for value in ("education", "living_environment", "employment", "income"):
        policies.append(
            {
                "policy_id": f"POL-{value}",
                "trigger_kind": "domain",
                "trigger_value": value,
                "policy_title_ko": f"{value} 정책",
                "policy_title_en": f"{value} policy",
                "lead_implementer": "Lead",
                "implementation_partners": "Partners",
                "implementation_difficulty": "medium",
                "difficulty_basis": "Coordination",
                "expected_effect": "Improved access",
                "monitoring_indicator": "Linkage rate",
                "evidence_limit": "Proxy only",
            }
        )
    policies.append(
        {
            "policy_id": "POL-air",
            "trigger_kind": "overlay",
            "trigger_value": "double_burden",
            "policy_title_ko": "환경 정책",
            "policy_title_en": "Air policy",
            "lead_implementer": "Lead",
            "implementation_partners": "Partners",
            "implementation_difficulty": "high",
            "difficulty_basis": "New monitoring",
            "expected_effect": "Better evidence",
            "monitoring_indicator": "Monitoring days",
            "evidence_limit": "No causal attribution",
        }
    )
    return pd.DataFrame(assignments), overlay, pd.DataFrame(policies)[list(CATALOG_COLUMNS)]


def test_build_creates_type_and_overlay_policy_candidates() -> None:
    assignments, overlay, catalog = inputs()

    matrix, report = build(assignments, overlay, catalog, cluster_report())

    assert len(matrix) == report["matrix_row_count"] == 5
    assert report["cluster_count"] == 2
    assert report["unique_policy_count"] == 4
    assert set(matrix["decision_status"]) == {"candidate_for_field_validation"}
    assert matrix.groupby("cluster_id").size().to_dict() == {"type_1": 2, "type_2": 3}
    type_2_domains = matrix[
        (matrix["cluster_id"] == "type_2")
        & matrix["policy_trigger"].str.startswith("domain:")
    ]
    assert type_2_domains["policy_priority"].tolist() == [1, 2]
    assert type_2_domains["policy_trigger"].tolist() == [
        "domain:income",
        "domain:employment",
    ]
    air = matrix[matrix["policy_trigger"] == "overlay:double_burden"]
    assert air.set_index("cluster_id")["target_area_count"].to_dict() == {
        "type_1": 1,
        "type_2": 2,
    }
    assert report["cluster_summaries"][0]["excluded_nonpositive_domains"] == [
        {"domain": "living_environment", "mean_excess_points": -1.02}
    ]


def test_build_rejects_missing_policy_and_invalid_overlay() -> None:
    assignments, overlay, catalog = inputs()

    with pytest.raises(ValueError, match="exactly one domain:income"):
        build(
            assignments,
            overlay,
            catalog[catalog["trigger_value"] != "income"],
            cluster_report(),
        )
    with pytest.raises(ValueError, match="206 unique"):
        build(assignments, overlay.iloc[:-1], catalog, cluster_report())
    with pytest.raises(ValueError, match="21 unique"):
        build(assignments.iloc[:-1], overlay, catalog, cluster_report())


def test_build_stops_on_failed_typology_and_handles_no_candidates() -> None:
    assignments, overlay, catalog = inputs()
    failed_report = {
        "recommended_for_policy_typology": False,
        "decision": "do_not_use_as_policy_typology",
    }

    with pytest.raises(ValueError, match="passes the typology gate"):
        build(assignments, overlay, catalog, failed_report)

    for column in [name for name in assignments if name.endswith("_excess_points")]:
        assignments[column] = -1.0
    overlay["double_burden"] = False
    matrix, report = build(assignments, overlay, catalog, cluster_report())

    assert matrix.empty
    assert list(matrix.columns)
    assert report["matrix_row_count"] == 0
    assert report["unique_policy_count"] == 0


def test_run_creates_independent_output_directories(tmp_path) -> None:
    assignments, overlay, catalog = inputs()
    assignments_path = tmp_path / "input" / "assignments.csv"
    overlay_path = tmp_path / "input" / "overlay.csv"
    catalog_path = tmp_path / "input" / "catalog.csv"
    output_path = tmp_path / "output" / "matrix.csv"
    report_path = tmp_path / "report" / "matrix.json"
    cluster_report_path = tmp_path / "input" / "cluster.json"
    assignments_path.parent.mkdir(parents=True)
    assignments.to_csv(assignments_path, index=False)
    overlay.to_csv(overlay_path, index=False)
    catalog.to_csv(catalog_path, index=False)
    assignment_hash = hashlib.sha256(assignments_path.read_bytes()).hexdigest().upper()
    cluster_report_path.write_text(
        json.dumps(
            {
                **cluster_report(),
                "output_sha256": {"assignments": assignment_hash},
            }
        ),
        encoding="utf-8",
    )

    report = run(
        assignments_path,
        overlay_path,
        catalog_path,
        cluster_report_path,
        output_path,
        report_path,
    )

    assert output_path.is_file()
    assert report_path.is_file()
    assert report["matrix_row_count"] == 5
