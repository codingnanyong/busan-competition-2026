from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DIRECTORIES = (
    "data/raw",
    "data/processed",
    "notebooks",
    "outputs",
    "src/busan_imd",
    "tests",
)


def test_required_project_directories_exist() -> None:
    missing = [path for path in REQUIRED_DIRECTORIES if not (REPOSITORY_ROOT / path).is_dir()]

    assert not missing, f"Missing required project directories: {', '.join(missing)}"
