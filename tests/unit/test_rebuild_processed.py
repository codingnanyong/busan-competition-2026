from scripts.rebuild_processed import BOOTSTRAP_DIR, BOOTSTRAP_REPORT


def test_bootstrap_artifacts_are_inside_processed_data() -> None:
    assert BOOTSTRAP_DIR.as_posix() == "data/processed/bootstrap/2025"
    assert BOOTSTRAP_REPORT.parent == BOOTSTRAP_DIR
