from __future__ import annotations

import pandas as pd
import pytest

from busan_imd.category_assessment import build, derive_indicators, load_spec


def profile() -> pd.DataFrame:
    size = 206
    index = pd.Series(range(size), dtype=float)
    return pd.DataFrame(
        {
            "admin_dong_code": [f"{value:03d}" for value in range(size)],
            "sigungu_name": "District",
            "admin_dong_name": [f"Dong {value}" for value in range(size)],
            "total_population_2025": 1_000 + index * 100,
            "workplace_workers_2024": 300 + index * 20,
            "establishments_2024": 100 + index * 3,
            "hospital_count_2025_candidate": 1 + index % 5,
            "clinic_count_2025_candidate": 2 + index % 11,
            "bus_stop_count_2025": 3 + index % 17,
            "heat_shelter_count_2025": 1 + index % 9,
            "elderly_alone_latest_count": 50 + index * 2,
            "nearest_core_school_distance_m_2025": 50 + index * 10,
            "school_count_2025": 1 + index % 10,
            "core_schools_within_2000m_2025": 2 + index % 20,
            "old_house_share_30plus_2024_lower_bound_pct": index / 3,
            "annual_pm25_ug_m3_idw_2025": 12 + index / 100,
            "nearest_air_station_distance_m": 500 + index * 20,
            "basic_livelihood_recipients_per_1000_population_2025_inferred": (
                20 + index / 10
            ),
            "inference_quality_tier": [
                "C1_observed_pattern_rescaled" if value < 86 else "C2_model_pattern_rescaled"
                for value in range(size)
            ],
        }
    )


def test_build_creates_complete_transparent_category_contract() -> None:
    indicators, categories, report = build(profile(), load_spec())

    assert report["category_count"] == 8
    assert report["indicator_count"] == 13
    assert len(indicators) == 206 * 13
    assert len(categories) == 206 * 8
    assert categories.groupby("admin_dong_code")["category"].nunique().eq(8).all()
    assert set(indicators["confidence_level"]) == {"low", "medium_low", "medium"}
    assert set(categories["policy_review_status"]) <= {
        "candidate_after_validation",
        "monitor",
    }


def test_small_area_rate_shrinkage_reduces_denominator_extremes() -> None:
    source = profile()
    source.loc[0, ["total_population_2025", "clinic_count_2025_candidate"]] = [100, 20]

    derived = derive_indicators(source)
    raw_rate = 20 / 100 * 10_000

    assert derived.loc[0, "clinic_per_10000_smoothed"] < raw_rate
    assert derived.loc[0, "clinic_per_10000_smoothed"] > 0


def test_build_rejects_incomplete_population() -> None:
    with pytest.raises(ValueError, match="206 unique"):
        build(profile().iloc[:-1], load_spec())
