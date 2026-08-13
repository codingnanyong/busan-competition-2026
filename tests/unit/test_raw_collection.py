"""Unit tests for raw-collection period classification."""

from busan_imd.collectors.approved_apis import cutoff_status


def test_cutoff_status() -> None:
    assert cutoff_status("2026-07-31") == "eligible"
    assert cutoff_status("2026-08-01") == "outside_cutoff"
    assert cutoff_status("current inventory") == "unverified"
