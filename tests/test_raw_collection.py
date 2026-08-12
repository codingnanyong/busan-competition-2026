import json
from pathlib import Path

from busan_imd.raw_collection import cutoff_status, validate_manifest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_cutoff_status() -> None:
    assert cutoff_status("2026-07-31") == "eligible"
    assert cutoff_status("2026-08-01") == "outside_cutoff"
    assert cutoff_status("current inventory") == "unverified"


def test_committed_raw_manifest_is_valid() -> None:
    path = REPOSITORY_ROOT / "docs/data/RAW_DATA_MANIFEST.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))

    validate_manifest(manifest, REPOSITORY_ROOT)
    assert manifest["analysis_cutoff"] == "2026-07-31"
    assert manifest["dataset_count"] == 14
    assert manifest["cutoff_status_counts"] == {
        "eligible": 11,
        "outside_cutoff": 1,
        "unverified": 2,
    }
    assert {entry["access_method"] for entry in manifest["datasets"]} == {
        "authenticated OpenAPI",
        "public direct download",
    }


def test_committed_raw_manifest_has_no_credentials() -> None:
    text = (REPOSITORY_ROOT / "docs/data/RAW_DATA_MANIFEST.json").read_text(encoding="utf-8")

    assert "serviceKey=" not in text
    assert "accessToken=" not in text
    assert "consumer_secret" not in text
    assert "consumer_key" not in text
