from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def load_create_linear_issue():
    path = REPOSITORY_ROOT / ".github" / "scripts" / "create_linear_issue.py"
    spec = importlib.util.spec_from_file_location("create_linear_issue", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_create_linear_issue_workflow_requires_the_contest_project() -> None:
    workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "create-linear-issue.yml").read_text(
        encoding="utf-8"
    )

    assert "workflow_dispatch:" in workflow
    assert "LINEAR_TEAM_KEY: COD" in workflow
    assert "LINEAR_PROJECT_SLUG: 83133e455764" in workflow
    assert "LINEAR_PROJECT_NAME: 부산 IMD 생활취약지역 분석 2026" in workflow


def test_select_project_prefers_slug_and_requires_a_match() -> None:
    module = load_create_linear_issue()
    contest = {
        "id": "proj-1",
        "slugId": "83133e455764",
        "name": "부산 IMD 생활취약지역 분석 2026",
    }

    assert module.select_project([contest], "83133e455764", contest["name"]) == contest
    with pytest.raises(SystemExit, match="Linear project was not found"):
        module.select_project([], "83133e455764", contest["name"])


def test_issue_create_input_includes_project_id() -> None:
    module = load_create_linear_issue()

    payload = module.issue_create_input("team-1", "proj-1", "제목", "설명")

    assert payload["teamId"] == "team-1"
    assert payload["projectId"] == "proj-1"
    assert payload["title"] == "제목"
