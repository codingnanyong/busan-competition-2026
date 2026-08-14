from pathlib import Path

from scripts.bootstrap_data import COLLECTION_STEPS, collect_network, locate_bundle


def test_locate_bundle_prefers_explicit_path(tmp_path: Path) -> None:
    bundle = tmp_path / "raw.tar.gz"
    bundle.write_bytes(b"archive")

    assert locate_bundle(bundle, tmp_path / "missing.env") == bundle.resolve()


def test_current_snapshot_sources_are_not_recollected() -> None:
    identifiers = "|".join(step.dataset_id for step in COLLECTION_STEPS)

    for excluded in ("HLT-AED-001", "HOU-BUSSTOP-API-001", "ENV-CITY-PARK-001"):
        assert excluded not in identifiers


def test_collect_network_dry_run_does_not_start_process(
    tmp_path: Path, capsys
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SGIS_CONSUMER_KEY=x\nSGIS_CONSUMER_SECRET=y\n",
        encoding="utf-8",
    )

    collect_network(
        env_file,
        {"GEO-SGIS-ADM-001"},
        refresh=False,
        dry_run=True,
    )

    assert "historical_api" in capsys.readouterr().out
