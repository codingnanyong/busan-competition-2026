"""Tests for constrained basic-livelihood inference helpers."""

import pandas as pd

from busan_imd.income_inference import (
    MODEL_FEATURE_DATASET_IDS,
    MODEL_PATTERN_DATASET_IDS,
    largest_remainder,
)


def test_largest_remainder_preserves_total_and_order() -> None:
    allocated = largest_remainder(pd.Series([1.0, 1.0, 2.0]), 7)

    assert allocated.tolist() == [2, 2, 3]
    assert int(allocated.sum()) == 7


def test_largest_remainder_handles_zero_weight_cells() -> None:
    allocated = largest_remainder(pd.Series([0.0, 1.0, 3.0]), 8)

    assert allocated.tolist() == [0, 2, 6]


def test_inference_lineage_lists_model_inputs() -> None:
    assert "INC-BLF-BUKGU-001" in MODEL_PATTERN_DATASET_IDS
    assert "INC-BLF-HAEUNDAE-2025-001" in MODEL_PATTERN_DATASET_IDS
    assert MODEL_FEATURE_DATASET_IDS.split("|") == [
        "SOC-BUSAN-ELDERLY-ALONE-001",
        "HOU-SGIS-OLD-001",
        "DEM-MOIS-POP-2025-001",
    ]
