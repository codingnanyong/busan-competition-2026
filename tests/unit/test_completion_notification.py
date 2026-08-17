import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parents[2] / ".github" / "scripts" / "notify_completion.py"
SPEC = importlib.util.spec_from_file_location("notify_completion", SCRIPT_PATH)
notify_completion = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(notify_completion)


def test_parse_issue_refs_normalizes_linear_id():
    assert notify_completion.parse_issue_refs("Closes cod-30\nCloses #44") == ("COD-30", 44)


def test_parse_issue_refs_rejects_incomplete_pair():
    with pytest.raises(notify_completion.NotificationError):
        notify_completion.parse_issue_refs("Closes COD-30")


def test_completed_state_uses_linear_state_type():
    assert notify_completion.is_completed({"state": {"name": "Done", "type": "completed"}})
    assert not notify_completion.is_completed(
        {"state": {"name": "In Progress", "type": "started"}}
    )


def test_slack_payload_contains_all_completion_links():
    payload = notify_completion.build_slack_payload(
        {
            "number": 45,
            "title": "COD-30 feat: completion notification",
            "html_url": "https://github.test/pull/45",
            "merge_commit_sha": "1234567890abcdef",
        },
        {
            "number": 44,
            "html_url": "https://github.test/issues/44",
        },
        {
            "identifier": "COD-30",
            "url": "https://linear.test/COD-30",
            "state": {"name": "Done", "type": "completed"},
        },
    )
    rendered = str(payload)
    assert "pull/45" in rendered
    assert "issues/44" in rendered
    assert "linear.test/COD-30" in rendered
    assert "1234567" in rendered
