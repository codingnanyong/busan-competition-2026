from __future__ import annotations

import pandas as pd
import pytest

from busan_imd.analysis.domain_scores import IndicatorRule, build, percentile_score


def rule(domain: str, indicator: str, direction: str, weight: float = 1.0) -> IndicatorRule:
    return IndicatorRule(
        domain=domain,
        indicator=indicator,
        source_dataset_id="TEST-001",
        input_transform="identity",
        deprivation_direction=direction,
        normalization="percentile_rank",
        within_domain_weight=weight,
        evidence_status="conditional",
        quality_note="test",
    )


def test_percentile_score_aligns_direction_and_averages_ties() -> None:
    values = pd.Series([10.0, 20.0, 20.0, 40.0])

    higher = percentile_score(values, "higher")
    lower = percentile_score(values, "lower")

    assert higher.tolist() == pytest.approx([0.0, 50.0, 50.0, 100.0])
    assert lower.tolist() == pytest.approx([100.0, 50.0, 50.0, 0.0])


def test_build_calculates_weighted_domain_scores_without_composite() -> None:
    size = 206
    profile = pd.DataFrame(
        {
            "admin_dong_code": [str(index) for index in range(size)],
            "sido_name": ["Busan"] * size,
            "sigungu_name": ["District"] * size,
            "admin_dong_name": [f"Dong {index}" for index in range(size)],
            "risk": range(size),
            "access_a": range(size),
            "access_b": range(size),
        }
    )
    rules = [
        rule("risk", "risk", "higher"),
        rule("access", "access_a", "lower", 0.5),
        rule("access", "access_b", "lower", 0.5),
    ]

    indicator_scores, domain_scores, report = build(profile, rules)

    assert len(indicator_scores) == size * 3
    assert domain_scores.loc[0, "risk_score_0_100"] == pytest.approx(0.0)
    assert domain_scores.loc[0, "access_score_0_100"] == pytest.approx(100.0)
    assert not any("composite" in column for column in domain_scores.columns)
    assert report["composite_score_created"] is False


def test_percentile_score_rejects_constant_or_missing_values() -> None:
    with pytest.raises(ValueError, match="non-constant"):
        percentile_score(pd.Series([1.0, 1.0]), "higher")
    with pytest.raises(ValueError, match="finite"):
        percentile_score(pd.Series([1.0, None]), "higher")
