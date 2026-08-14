from __future__ import annotations

import pandas as pd
import pytest

from busan_imd.data_quality import build, column_spec


def test_column_spec_rejects_undocumented_columns() -> None:
    with pytest.raises(ValueError, match="No data-dictionary specification"):
        column_spec("mystery_indicator")


def test_quality_report_counts_missing_and_requires_unique_dongs() -> None:
    profile = pd.DataFrame(
        {
            "admin_dong_code": ["21000001", "21000002"],
            "total_population_2025": [100, 200],
            "elderly_alone_reference_date": ["2025-12-31", None],
        }
    )
    standardization = {
        "canonical_admin_dong_count": 2,
        "datasets": [{"match_rate": 0.75}],
    }

    dictionary, report = build(profile, standardization)

    assert set(dictionary["column_name"]) == set(profile.columns)
    assert report["columns_with_missing_values"] == {"elderly_alone_reference_date": 1}
    assert report["minimum_source_match_rate"] == 0.75
