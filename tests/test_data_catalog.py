from pathlib import Path

from busan_imd.data_catalog import validate_catalog

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_dataset_audit_is_valid() -> None:
    rows = validate_catalog(REPOSITORY_ROOT / "docs/data/DATASET_AUDIT.csv")

    assert len(rows) >= 18
    assert {row["availability_grade"] for row in rows} >= {"B", "C", "D"}
    assert {row["decision"] for row in rows} >= {"hold", "exclude", "validation-only"}
    assert {
        "income",
        "employment",
        "education",
        "health",
        "safety",
        "housing_access",
        "living_environment",
    } <= {row["domain"] for row in rows}
