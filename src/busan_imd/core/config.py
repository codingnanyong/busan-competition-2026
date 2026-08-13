"""Configuration loading that never logs credential values."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


def read_env_file(path: Path) -> dict[str, str]:
    """Read a small dotenv file without mutating the process environment."""
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", maxsplit=1)
        name = name.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if name:
            values[name] = value
    return values


def require_values(config: dict[str, str], names: Iterable[str], source: Path) -> None:
    """Raise one safe error listing missing configuration names only."""
    missing = [name for name in names if not config.get(name)]
    if missing:
        raise ValueError(f"Missing credentials in {source}: {', '.join(missing)}")
