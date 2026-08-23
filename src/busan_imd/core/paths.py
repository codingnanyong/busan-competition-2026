"""Resolve repository artifacts independently of the process working directory."""

from __future__ import annotations

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def repository_path(path: str | Path) -> Path:
    """Return an absolute path, anchoring relative paths at the repository root."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPOSITORY_ROOT / candidate
