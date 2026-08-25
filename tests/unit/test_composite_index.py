from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from busan_imd.analysis.composite_index import DomainWeight, build, load_weights


def weight(domain: str, value: float) -> DomainWeight:
    return DomainWeight(
        domain=domain,
        source_domain=f"Source {domain}",
        published_weight=value,
        scored_model_weight=value,
        evidence_status="conditional",
        quality_note="test",
    )


def profile() -> pd.DataFrame:
    size = 206
    return pd.DataFrame(
        {
            "admin_dong_code": [f"{index:03d}" for index in range(size)],
            "sido_name": ["Busan"] * size,
            "sigungu_name": ["District"] * size,
            "admin_dong_name": [f"Dong {index}" for index in range(size)],
            "income_score_0_100": np.linspace(0, 100, size),
            "employment_score_0_100": np.linspace(0, 100, size),
        }
    )


def test_build_calculates_composite_rank_and_decile() -> None:
    result, report = build(profile(), [weight("income", 0.75), weight("employment", 0.25)])

    assert result.iloc[0]["admin_dong_code"] == "205"
    assert result.iloc[0]["b_imd_score_0_100"] == pytest.approx(100.0)
    assert result.iloc[0]["b_imd_rank"] == 1
    assert result.iloc[0]["b_imd_decile"] == 1
    assert result.iloc[-1]["b_imd_rank"] == 206
    assert result.iloc[-1]["b_imd_decile"] == 10
    assert set(report["decile_counts"]) == {str(value) for value in range(1, 11)}
    assert max(report["decile_counts"].values()) - min(report["decile_counts"].values()) <= 1


def test_build_breaks_composite_ties_by_admin_dong_code() -> None:
    frame = profile()
    frame.loc[204, ["income_score_0_100", "employment_score_0_100"]] = 100

    result, _ = build(frame, [weight("income", 0.5), weight("employment", 0.5)])

    assert result.iloc[0]["admin_dong_code"] == "204"
    assert result.iloc[1]["admin_dong_code"] == "205"


def test_build_rejects_missing_or_out_of_range_domain_scores() -> None:
    weights = [weight("income", 0.5), weight("employment", 0.5)]
    with pytest.raises(ValueError, match="missing columns"):
        build(profile().drop(columns="employment_score_0_100"), weights)

    invalid = profile()
    invalid.loc[0, "income_score_0_100"] = 101
    with pytest.raises(ValueError, match="between 0 and 100"):
        build(invalid, weights)


def test_load_weights_validates_the_versioned_contract(tmp_path) -> None:
    path = tmp_path / "weights.csv"
    pd.DataFrame(
        [
            {
                "domain": domain,
                "source_domain": f"Source {domain}",
                "published_weight": 1,
                "scored_model_weight": 1 / 6,
                "evidence_status": "conditional",
                "quality_note": "test",
            }
            for domain in sorted(
                {
                    "income",
                    "employment",
                    "education",
                    "health",
                    "housing_access",
                    "living_environment",
                }
            )
        ]
    ).to_csv(path, index=False)

    assert len(load_weights(path)) == 6
