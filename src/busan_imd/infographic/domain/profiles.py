"""Build domain-level dong action profiles from the composite index."""

import pandas as pd

from busan_imd.infographic.config import (
    DOMAIN_COLUMNS,
    IMPROVEMENT_ACTIONS,
    PRESERVATION_DIRECTIONS,
)


def build_action_profiles(composite: pd.DataFrame) -> pd.DataFrame:
    """Translate six-domain scores into transparent dong-level review directions."""
    required = {
        "admin_dong_code",
        "sigungu_name",
        "admin_dong_name",
        "b_imd_score_0_100",
        "b_imd_rank",
        "b_imd_decile",
        *(column for column, _ in DOMAIN_COLUMNS.values()),
    }
    missing = sorted(required - set(composite.columns))
    if missing:
        raise ValueError(f"Composite input is missing action-profile columns: {missing}")

    profiles = composite.copy()
    score_columns = [column for column, _ in DOMAIN_COLUMNS.values()]
    ordered = profiles[score_columns].apply(
        lambda row: row.sort_values(ascending=False, kind="stable").index.tolist(), axis=1
    )
    column_to_domain = {column: domain for domain, (column, _) in DOMAIN_COLUMNS.items()}
    profiles["primary_vulnerability_domain"] = ordered.map(
        lambda values: column_to_domain[values[0]]
    )
    profiles["secondary_vulnerability_domain"] = ordered.map(
        lambda values: column_to_domain[values[1]]
    )
    profiles["relative_low_deprivation_domain"] = ordered.map(
        lambda values: column_to_domain[values[-1]]
    )

    labels = {domain: values[1] for domain, values in DOMAIN_COLUMNS.items()}
    profiles["primary_vulnerability_ko"] = profiles["primary_vulnerability_domain"].map(labels)
    profiles["secondary_vulnerability_ko"] = profiles["secondary_vulnerability_domain"].map(labels)
    profiles["relative_low_deprivation_ko"] = profiles["relative_low_deprivation_domain"].map(
        labels
    )
    profiles["improvement_direction"] = profiles["primary_vulnerability_domain"].map(
        IMPROVEMENT_ACTIONS
    )
    profiles["preservation_direction"] = profiles["relative_low_deprivation_domain"].map(
        PRESERVATION_DIRECTIONS
    )
    profiles["review_level"] = pd.cut(
        profiles["b_imd_decile"],
        bins=[0, 1, 3, 7, 10],
        labels=["현장검증 우선", "집중 모니터링", "정기 모니터링", "상대 저취약"],
    ).astype(str)
    profiles["specialization_evidence_status"] = (
        "특화 확정 불가: 산업·상권·관광·생활SOC 자산 데이터 결합 필요"
    )

    columns = [
        "admin_dong_code",
        "sigungu_name",
        "admin_dong_name",
        "b_imd_score_0_100",
        "b_imd_rank",
        "b_imd_decile",
        *score_columns,
        "primary_vulnerability_domain",
        "primary_vulnerability_ko",
        "secondary_vulnerability_domain",
        "secondary_vulnerability_ko",
        "improvement_direction",
        "relative_low_deprivation_domain",
        "relative_low_deprivation_ko",
        "preservation_direction",
        "review_level",
        "specialization_evidence_status",
    ]
    return profiles[columns].sort_values("b_imd_rank", kind="stable").reset_index(drop=True)
