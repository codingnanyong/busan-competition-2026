"""Build an evidence-linked policy-priority matrix for 2025 deprivation types."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from busan_imd.analysis.cluster_analysis import (
    DEFAULT_ASSIGNMENT_OUTPUT,
    FEATURE_COLUMNS,
)
from busan_imd.analysis.cluster_analysis import (
    DEFAULT_REPORT as DEFAULT_CLUSTER_REPORT,
)
from busan_imd.analysis.environmental_overlay import DEFAULT_OUTPUT as DEFAULT_OVERLAY
from busan_imd.core.artifacts import sha256_file, write_json

DEFAULT_CATALOG = Path("docs/data/POLICY_ACTION_CATALOG_2025.csv")
DEFAULT_OUTPUT = Path("data/processed/scores/2025/busan_admin_dong_policy_matrix_2025.csv")
DEFAULT_REPORT = Path("docs/data/manifests/POLICY_MATRIX_REPORT_2025.json")
EXPECTED_PRIORITY_COUNT = 21
CATALOG_COLUMNS = (
    "policy_id",
    "trigger_kind",
    "trigger_value",
    "policy_title_ko",
    "policy_title_en",
    "lead_implementer",
    "implementation_partners",
    "implementation_difficulty",
    "difficulty_basis",
    "expected_effect",
    "monitoring_indicator",
    "evidence_limit",
)
MATRIX_COLUMNS = (
    "matrix_id",
    "cluster_id",
    "cluster_label",
    "policy_priority",
    "policy_trigger",
    "policy_id",
    "policy_title_ko",
    "policy_title_en",
    "target_area_count",
    "target_admin_dong_codes",
    "target_admin_dongs",
    "analysis_basis",
    "analysis_basis_value",
    "lead_implementer",
    "implementation_partners",
    "implementation_difficulty",
    "difficulty_basis",
    "expected_effect",
    "monitoring_indicator",
    "evidence_limit",
    "decision_status",
)


def _validate_typology_report(cluster_report: dict[str, Any]) -> None:
    if (
        cluster_report.get("recommended_for_policy_typology") is not True
        or cluster_report.get("decision") != "use_as_exploratory_policy_typology"
    ):
        raise ValueError("Policy matrix requires a cluster report that passes the typology gate")


def _validate(
    assignments: pd.DataFrame,
    overlay: pd.DataFrame,
    catalog: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    assignment_required = {
        "admin_dong_code",
        "sigungu_name",
        "admin_dong_name",
        "b_imd_rank",
        "cluster_id",
        "cluster_label",
        "dominant_domain",
        "secondary_domain",
        *FEATURE_COLUMNS,
    }
    overlay_required = {
        "admin_dong_code",
        "double_burden",
        "particulate_free_b_imd_rank",
        "particulate_exposure_rank",
    }
    missing_assignments = sorted(assignment_required - set(assignments.columns))
    missing_overlay = sorted(overlay_required - set(overlay.columns))
    if missing_assignments:
        raise ValueError(f"Cluster assignments are missing columns: {missing_assignments}")
    if missing_overlay:
        raise ValueError(f"Environmental overlay is missing columns: {missing_overlay}")
    if tuple(catalog.columns) != CATALOG_COLUMNS:
        raise ValueError(f"Policy catalog columns must be {list(CATALOG_COLUMNS)}")

    assignments = assignments.copy()
    overlay = overlay.copy()
    catalog = catalog.copy()
    assignments["admin_dong_code"] = assignments["admin_dong_code"].astype(str)
    overlay["admin_dong_code"] = overlay["admin_dong_code"].astype(str)
    if (
        len(assignments) != EXPECTED_PRIORITY_COUNT
        or assignments["admin_dong_code"].duplicated().any()
    ):
        raise ValueError("Policy matrix requires 21 unique cluster assignments")
    if len(overlay) != 206 or overlay["admin_dong_code"].duplicated().any():
        raise ValueError("Environmental overlay requires 206 unique administrative-dong rows")
    if not set(assignments["admin_dong_code"]).issubset(set(overlay["admin_dong_code"])):
        raise ValueError("Environmental overlay must cover every clustered priority area")
    if catalog[["trigger_kind", "trigger_value"]].duplicated().any():
        raise ValueError("Policy catalog triggers must be unique")
    if catalog["policy_id"].duplicated().any():
        raise ValueError("Policy catalog policy ids must be unique")
    allowed_difficulties = {"low", "medium", "high"}
    if not set(catalog["implementation_difficulty"]).issubset(allowed_difficulties):
        raise ValueError("Implementation difficulty must be low, medium, or high")

    numeric = assignments[["b_imd_rank", *FEATURE_COLUMNS]].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(numeric).all().all():
        raise ValueError("Ranks and domain-excess values must be finite")
    assignments[["b_imd_rank", *FEATURE_COLUMNS]] = numeric
    if not pd.api.types.is_bool_dtype(overlay["double_burden"]):
        normalized = overlay["double_burden"].astype(str).str.lower()
        if not normalized.isin({"true", "false"}).all():
            raise ValueError("Double-burden flags must be boolean")
        overlay["double_burden"] = normalized == "true"
    return assignments, overlay, catalog


def _policy(catalog: pd.DataFrame, kind: str, value: str) -> pd.Series:
    matches = catalog[(catalog["trigger_kind"] == kind) & (catalog["trigger_value"] == value)]
    if len(matches) != 1:
        raise ValueError(f"Policy catalog requires exactly one {kind}:{value} action")
    return matches.iloc[0]


def _target_text(frame: pd.DataFrame) -> tuple[str, str]:
    ordered = frame.sort_values("b_imd_rank", kind="stable")
    codes = "|".join(ordered["admin_dong_code"].astype(str))
    names = "|".join(ordered["sigungu_name"] + " " + ordered["admin_dong_name"])
    return codes, names


def build(
    assignments: pd.DataFrame,
    overlay: pd.DataFrame,
    catalog: pd.DataFrame,
    cluster_report: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return deterministic type-level policy candidates and an audit report."""
    _validate_typology_report(cluster_report)
    assignments, overlay, catalog = _validate(assignments, overlay, catalog)
    joined = assignments.merge(
        overlay[
            [
                "admin_dong_code",
                "double_burden",
                "particulate_free_b_imd_rank",
                "particulate_exposure_rank",
            ]
        ],
        on="admin_dong_code",
        validate="one_to_one",
    )
    records: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for cluster_id, members in joined.groupby("cluster_id", sort=True):
        labels = members["cluster_label"].unique()
        dominant = members["dominant_domain"].unique()
        secondary = members["secondary_domain"].unique()
        if len(labels) != 1 or len(dominant) != 1 or len(secondary) != 1:
            raise ValueError("Cluster labels and dominant domains must be consistent")
        cluster_label = str(labels[0])
        target_codes, target_names = _target_text(members)
        cluster_policy_ids = []
        excluded_nonpositive_domains = []
        for priority_order, domain in enumerate((str(dominant[0]), str(secondary[0])), 1):
            mean_excess = float(members[f"{domain}_excess_points"].mean())
            if mean_excess <= 0:
                excluded_nonpositive_domains.append(
                    {"domain": domain, "mean_excess_points": round(mean_excess, 6)}
                )
                continue
            action = _policy(catalog, "domain", domain)
            cluster_policy_ids.append(str(action["policy_id"]))
            records.append(
                {
                    "matrix_id": f"{cluster_id}-domain-{priority_order}",
                    "cluster_id": cluster_id,
                    "cluster_label": cluster_label,
                    "policy_priority": priority_order,
                    "policy_trigger": f"domain:{domain}",
                    "policy_id": action["policy_id"],
                    "policy_title_ko": action["policy_title_ko"],
                    "policy_title_en": action["policy_title_en"],
                    "target_area_count": len(members),
                    "target_admin_dong_codes": target_codes,
                    "target_admin_dongs": target_names,
                    "analysis_basis": f"mean_{domain}_excess_points",
                    "analysis_basis_value": round(mean_excess, 6),
                    "lead_implementer": action["lead_implementer"],
                    "implementation_partners": action["implementation_partners"],
                    "implementation_difficulty": action["implementation_difficulty"],
                    "difficulty_basis": action["difficulty_basis"],
                    "expected_effect": action["expected_effect"],
                    "monitoring_indicator": action["monitoring_indicator"],
                    "evidence_limit": action["evidence_limit"],
                    "decision_status": "candidate_for_field_validation",
                }
            )

        burden = members[members["double_burden"]]
        burden_count = len(burden)
        if burden_count:
            action = _policy(catalog, "overlay", "double_burden")
            burden_codes, burden_names = _target_text(burden)
            cluster_policy_ids.append(str(action["policy_id"]))
            records.append(
                {
                    "matrix_id": f"{cluster_id}-overlay-1",
                    "cluster_id": cluster_id,
                    "cluster_label": cluster_label,
                    "policy_priority": 1,
                    "policy_trigger": "overlay:double_burden",
                    "policy_id": action["policy_id"],
                    "policy_title_ko": action["policy_title_ko"],
                    "policy_title_en": action["policy_title_en"],
                    "target_area_count": burden_count,
                    "target_admin_dong_codes": burden_codes,
                    "target_admin_dongs": burden_names,
                    "analysis_basis": "double_burden_area_count",
                    "analysis_basis_value": burden_count,
                    "lead_implementer": action["lead_implementer"],
                    "implementation_partners": action["implementation_partners"],
                    "implementation_difficulty": action["implementation_difficulty"],
                    "difficulty_basis": action["difficulty_basis"],
                    "expected_effect": action["expected_effect"],
                    "monitoring_indicator": action["monitoring_indicator"],
                    "evidence_limit": action["evidence_limit"],
                    "decision_status": "candidate_for_field_validation",
                }
            )
        summaries.append(
            {
                "cluster_id": cluster_id,
                "cluster_label": cluster_label,
                "member_count": len(members),
                "dominant_domain": str(dominant[0]),
                "secondary_domain": str(secondary[0]),
                "double_burden_area_count": burden_count,
                "policy_ids": cluster_policy_ids,
                "excluded_nonpositive_domains": excluded_nonpositive_domains,
            }
        )

    matrix = pd.DataFrame.from_records(records, columns=MATRIX_COLUMNS)
    matrix["_trigger_group"] = np.where(matrix["policy_trigger"].str.startswith("domain:"), 0, 1)
    matrix = matrix.sort_values(
        ["cluster_id", "_trigger_group", "policy_priority", "policy_trigger"],
        kind="stable",
    ).drop(columns="_trigger_group")
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "reference_year": 2025,
        "analysis_population": "21 B-IMD decile-1 exploratory priority areas",
        "priority_area_count": len(assignments),
        "cluster_count": assignments["cluster_id"].nunique(),
        "matrix_row_count": len(matrix),
        "unique_policy_count": matrix["policy_id"].nunique(),
        "decision_status": "candidate_for_field_validation",
        "selection_rule": (
            "one action for each cluster's dominant or secondary domain only when its mean "
            "excess contribution is above the Busan median, plus one ambient-air action for "
            "each cluster containing COD-21 double-burden areas"
        ),
        "implementation_difficulty_scale": {
            "low": "single-organization operational adjustment using existing delivery channels",
            "medium": "cross-service coordination or new targeting and follow-up required",
            "high": "new measurement, capital work, or sustained multi-organization coordination",
        },
        "cluster_summaries": summaries,
        "interpretation_guardrails": [
            "Policies are candidates for field validation, not automatic funding decisions",
            "Cluster domains are relative patterns among 21 areas and do not establish causality",
            "Expected effects are directional hypotheses and require monitored implementation",
            "Area-level proxies must not be used to determine individual eligibility",
        ],
    }
    return matrix.reset_index(drop=True), report


def run(
    assignments_path: Path = DEFAULT_ASSIGNMENT_OUTPUT,
    overlay_path: Path = DEFAULT_OVERLAY,
    catalog_path: Path = DEFAULT_CATALOG,
    cluster_report_path: Path = DEFAULT_CLUSTER_REPORT,
    output_path: Path = DEFAULT_OUTPUT,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    """Read canonical inputs and write COD-22 policy-matrix artifacts."""
    cluster_report = json.loads(cluster_report_path.read_text(encoding="utf-8"))
    _validate_typology_report(cluster_report)
    expected_assignment_hash = cluster_report.get("output_sha256", {}).get("assignments")
    if sha256_file(assignments_path) != expected_assignment_hash:
        raise ValueError("Cluster assignments do not match the quality-gated cluster report")
    assignments = pd.read_csv(assignments_path, dtype={"admin_dong_code": str})
    overlay = pd.read_csv(overlay_path, dtype={"admin_dong_code": str})
    catalog = pd.read_csv(catalog_path)
    matrix, report = build(assignments, overlay, catalog, cluster_report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    matrix.to_csv(output_path, index=False, encoding="utf-8-sig", lineterminator="\n")
    report.update(
        {
            "input_paths": {
                "cluster_assignments": assignments_path.as_posix(),
                "environmental_overlay": overlay_path.as_posix(),
                "policy_catalog": catalog_path.as_posix(),
                "cluster_report": cluster_report_path.as_posix(),
            },
            "input_sha256": {
                "cluster_assignments": sha256_file(assignments_path),
                "environmental_overlay": sha256_file(overlay_path),
                "policy_catalog": sha256_file(catalog_path),
                "cluster_report": sha256_file(cluster_report_path),
            },
            "output_path": output_path.as_posix(),
            "output_sha256": sha256_file(output_path),
        }
    )
    write_json(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cluster-assignments", type=Path, default=DEFAULT_ASSIGNMENT_OUTPUT)
    parser.add_argument("--environmental-overlay", type=Path, default=DEFAULT_OVERLAY)
    parser.add_argument("--policy-catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--cluster-report", type=Path, default=DEFAULT_CLUSTER_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run(
        args.cluster_assignments,
        args.environmental_overlay,
        args.policy_catalog,
        args.cluster_report,
        args.output,
        args.report,
    )
    print(
        f"built {report['matrix_row_count']} policy candidates for "
        f"{report['cluster_count']} deprivation types"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
