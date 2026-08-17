from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from busan_imd.sensitivity_analysis import Scenario, build, load_scenarios


def scenario(
    scenario_id: str,
    *,
    weight_policy: str = "baseline",
    missing_policy: str = "complete_case",
    omitted_domain: str = "",
) -> Scenario:
    return Scenario(
        scenario_id=scenario_id,
        scenario_type="test",
        weight_policy=weight_policy,
        missing_policy=missing_policy,
        omitted_domain=omitted_domain,
        rationale="test",
    )


def domain_scores() -> pd.DataFrame:
    size = 206
    return pd.DataFrame(
        {
            "admin_dong_code": [f"{index:03d}" for index in range(size)],
            "sido_name": ["Busan"] * size,
            "sigungu_name": ["District"] * size,
            "admin_dong_name": [f"Dong {index}" for index in range(size)],
            "income_score_0_100": np.linspace(0, 100, size),
            "employment_score_0_100": np.linspace(100, 0, size),
        }
    )


def test_build_compares_equal_weights_and_systematic_omission() -> None:
    scenarios = [
        scenario("baseline"),
        scenario("equal", weight_policy="equal"),
        scenario(
            "omit_income",
            missing_policy="renormalize_after_systematic_omission",
            omitted_domain="income",
        ),
    ]
    output, report = build(
        domain_scores(), pd.Series({"income": 0.75, "employment": 0.25}), scenarios
    )

    assert len(output) == 206 * 3
    assert report["actual_missing_domain_score_count"] == 0
    assert report["scenario_summaries"]["baseline"]["spearman_rank_correlation"] == 1
    assert report["scenario_summaries"]["omit_income"]["maximum_absolute_rank_change"] > 0
    assert set(output["scenario_id"]) == {"baseline", "equal", "omit_income"}


def test_median_imputation_reports_real_missingness() -> None:
    frame = domain_scores()
    frame.loc[0, "income_score_0_100"] = np.nan
    scenarios = [scenario("baseline", missing_policy="median_imputation")]

    output, report = build(
        frame, pd.Series({"income": 0.5, "employment": 0.5}), scenarios
    )

    assert len(output) == 206
    assert report["actual_missing_domain_score_count"] == 1
    assert report["actual_missing_by_domain"]["income"] == 1


def test_complete_case_rejects_missing_domain_scores() -> None:
    frame = domain_scores()
    frame.loc[0, "income_score_0_100"] = np.nan

    with pytest.raises(ValueError, match="requires complete"):
        build(
            frame,
            pd.Series({"income": 0.5, "employment": 0.5}),
            [scenario("baseline")],
        )


def test_load_scenarios_validates_contract(tmp_path) -> None:
    path = tmp_path / "scenarios.csv"
    pd.DataFrame(
        [
            {
                "scenario_id": "baseline",
                "scenario_type": "reference",
                "weight_policy": "baseline",
                "missing_policy": "complete_case",
                "omitted_domain": "",
                "rationale": "test",
            }
        ]
    ).to_csv(path, index=False)

    assert load_scenarios(path)[0].scenario_id == "baseline"
