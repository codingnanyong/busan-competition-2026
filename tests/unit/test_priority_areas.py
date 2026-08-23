from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from busan_imd.composite_index import DomainWeight
from busan_imd.priority_areas import build

DOMAINS = (
    "income",
    "employment",
    "education",
    "health",
    "housing_access",
    "living_environment",
)


def weights() -> list[DomainWeight]:
    return [
        DomainWeight(
            domain=domain,
            source_domain=f"Source {domain}",
            published_weight=1 / len(DOMAINS),
            scored_model_weight=1 / len(DOMAINS),
            evidence_status="conditional",
            quality_note="test",
        )
        for domain in DOMAINS
    ]


def inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    size = 206
    codes = [f"{index:03d}" for index in range(size)]
    base = np.linspace(0, 100, size)
    composite = pd.DataFrame(
        {
            "admin_dong_code": codes,
            "sido_name": ["Busan"] * size,
            "sigungu_name": ["District"] * size,
            "admin_dong_name": [f"Dong {index}" for index in range(size)],
        }
    )
    for domain in DOMAINS:
        composite[f"{domain}_score_0_100"] = base
    composite["b_imd_score_0_100"] = base.round(6)
    composite["b_imd_rank"] = np.arange(size, 0, -1)
    composite["b_imd_decile"] = ((composite["b_imd_rank"] - 1) * 10 // size) + 1

    rows = []
    for index, code in enumerate(codes):
        for domain in DOMAINS:
            rows.append(
                {
                    "admin_dong_code": code,
                    "sigungu_name": "District",
                    "admin_dong_name": f"Dong {index}",
                    "domain": domain,
                    "indicator": f"{domain}_indicator",
                    "source_dataset_id": f"{domain}-001",
                    "raw_value": float(base[index]),
                    "deprivation_percentile_0_100": float(base[index]),
                    "within_domain_weight": 1.0,
                    "evidence_status": "conditional",
                }
            )
    return composite, pd.DataFrame(rows)


def test_build_explains_first_decile_and_reconciles_contributions() -> None:
    composite, indicators = inputs()

    priority, contributions, report = build(composite, indicators, weights())

    assert len(priority) == 21
    assert priority["b_imd_rank"].tolist() == list(range(1, 22))
    assert len(contributions) == 21 * len(DOMAINS)
    assert set(contributions["driver_rank_within_area"]) == set(range(1, 7))
    totals = contributions.groupby("admin_dong_code")["composite_contribution_points"].sum()
    expected = priority.set_index("admin_dong_code")["b_imd_score_0_100"]
    assert np.allclose(totals.sort_index(), expected.sort_index())
    assert report["priority_area_count"] == 21
    assert len(report["top_10_priority_areas"]) == 10


def test_build_breaks_equal_driver_ties_by_indicator_name() -> None:
    composite, indicators = inputs()

    priority, contributions, _ = build(composite, indicators, weights())

    top = priority.iloc[0]
    assert top["leading_indicator"] == "education_indicator"
    assert contributions.iloc[0]["driver_rank_within_area"] == 1


def test_build_rejects_incomplete_upstream_inputs() -> None:
    composite, indicators = inputs()

    with pytest.raises(ValueError, match="missing columns"):
        build(composite.drop(columns="income_score_0_100"), indicators, weights())

    with pytest.raises(ValueError, match="same dong codes"):
        build(composite, indicators[indicators["admin_dong_code"] != "000"], weights())
