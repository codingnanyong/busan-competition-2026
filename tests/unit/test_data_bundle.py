from __future__ import annotations

from pathlib import Path

import pytest
from scripts import data_bundle


def test_raw_bundle_round_trip_is_platform_independent(tmp_path, monkeypatch) -> None:
    source_root = tmp_path / "source" / "data" / "raw"
    source_root.mkdir(parents=True)
    (source_root / "한글 자료.csv").write_text("행정동,값\n중앙동,1\n", encoding="utf-8")
    archive = tmp_path / "raw.tar.gz"
    monkeypatch.setattr(data_bundle, "RAW_ROOT", source_root)

    data_bundle.export_bundle(archive)

    destination = tmp_path / "destination"
    destination_raw = destination / "data" / "raw"
    destination_raw.mkdir(parents=True)
    monkeypatch.setattr(data_bundle, "REPOSITORY_ROOT", destination)
    monkeypatch.setattr(data_bundle, "RAW_ROOT", destination_raw)
    data_bundle.import_bundle(archive)

    restored = destination_raw / "한글 자료.csv"
    assert restored.read_text(encoding="utf-8") == "행정동,값\n중앙동,1\n"
    checksum = Path(str(archive) + ".sha256").read_text(encoding="ascii")
    assert data_bundle.sha256(archive) in checksum


def test_bundle_checksum_rejects_tampering(tmp_path: Path) -> None:
    archive = tmp_path / "raw.tar.gz"
    archive.write_bytes(b"changed")
    archive.with_suffix(".gz.sha256").write_text(
        "0" * 64 + "  raw.tar.gz\n", encoding="ascii"
    )

    with pytest.raises(ValueError, match="checksum mismatch"):
        data_bundle.verify_bundle_checksum(archive, required=True)
