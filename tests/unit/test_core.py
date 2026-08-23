"""Unit tests for shared collection infrastructure."""

from datetime import date
from pathlib import Path

import pytest

from busan_imd.core.artifacts import sha256_file, write_csv, write_json
from busan_imd.core.config import read_env_file, require_values
from busan_imd.core.http import encoded_secret_url
from busan_imd.core.paths import REPOSITORY_ROOT, repository_path
from busan_imd.core.provenance import cutoff_status, ensure_secret_free


def test_read_env_file_handles_comments_quotes_and_equals(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text(
        "# comment\nPLAIN=value\nQUOTED='a=b'\nEMPTY=\ninvalid line\n",
        encoding="utf-8",
    )

    assert read_env_file(path) == {"PLAIN": "value", "QUOTED": "a=b", "EMPTY": ""}


def test_require_values_reports_names_without_values(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="API_KEY") as error:
        require_values({}, ("API_KEY",), tmp_path / ".env")
    assert "secret-value" not in str(error.value)


def test_encoded_secret_url_does_not_double_encode() -> None:
    url = encoded_secret_url("https://example.test", "key", "abc%2Fdef%3D", {"page": "1"})
    assert url == "https://example.test?key=abc%2Fdef%3D&page=1"


def test_provenance_helpers() -> None:
    assert cutoff_status("2026-07-31") == "eligible"
    assert cutoff_status("2026-08-01") == "outside_cutoff"
    assert cutoff_status("2026-07-01/2026-08-01") == "outside_cutoff"
    assert cutoff_status("current", date(2026, 7, 31)) == "unverified"
    ensure_secret_free({"endpoint": "https://example.test", "count": 1})
    with pytest.raises(ValueError, match="credential"):
        ensure_secret_free({"request": "https://example.test?authKey=secret"})


def test_artifact_helpers_write_stable_files(tmp_path: Path) -> None:
    json_path = tmp_path / "nested/data.json"
    csv_path = tmp_path / "nested/data.csv"
    write_json(json_path, {"name": "부산"})
    write_csv(csv_path, [{"b": 2, "a": 1}])

    assert '"name": "부산"' in json_path.read_text(encoding="utf-8")
    assert csv_path.read_text(encoding="utf-8-sig").splitlines() == ["a,b", "1,2"]
    assert len(sha256_file(json_path)) == 64


def test_repository_path_does_not_depend_on_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    assert repository_path("data/example.csv") == REPOSITORY_ROOT / "data/example.csv"
    assert repository_path(tmp_path / "absolute.csv") == tmp_path / "absolute.csv"
