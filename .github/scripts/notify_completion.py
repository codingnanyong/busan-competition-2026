"""Notify Slack after a merged PR closes both mirrored issues."""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LINEAR_API_URL = "https://api.linear.app/graphql"
COMPLETED_STATE_TYPES = {"completed"}


class NotificationError(RuntimeError):
    """Raised when completion cannot be verified or delivered."""


def parse_issue_refs(pr_body: str) -> tuple[str, int]:
    """Extract the Linear and GitHub issue references from a PR body."""
    linear_match = re.search(r"\bCloses\s+(COD-\d+)\b", pr_body, re.IGNORECASE)
    github_match = re.search(r"\bCloses\s+#(\d+)\b", pr_body, re.IGNORECASE)
    if not linear_match or not github_match:
        raise NotificationError("Merged PR is missing its mirrored issue references")
    return linear_match.group(1).upper(), int(github_match.group(1))


def is_completed(linear_issue: dict[str, Any]) -> bool:
    """Return whether Linear reports the issue in a completed state."""
    state_type = linear_issue.get("state", {}).get("type", "")
    return state_type.lower() in COMPLETED_STATE_TYPES


def build_slack_payload(
    pr: dict[str, Any], github_issue: dict[str, Any], linear_issue: dict[str, Any]
) -> dict[str, Any]:
    """Build the Slack incoming-webhook payload."""
    merge_sha = pr.get("merge_commit_sha") or "unknown"
    short_sha = merge_sha[:7]
    summary = f"PR #{pr['number']} 병합 및 미러 이슈 완료"
    return {
        "text": summary,
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "PR 완료 알림"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*<{pr['html_url']}|PR #{pr['number']}>* {pr['title']}\n"
                        f"Merge commit: `{short_sha}`"
                    ),
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            f"*GitHub*\n<{github_issue['html_url']}|"
                            f"#{github_issue['number']} Closed>"
                        ),
                    },
                    {
                        "type": "mrkdwn",
                        "text": (
                            f"*Linear*\n<{linear_issue['url']}|"
                            f"{linear_issue['identifier']} {linear_issue['state']['name']}>"
                        ),
                    },
                ],
            },
        ],
    }


def request_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send an HTTP request and decode a JSON response."""
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(url, data=data, headers=headers or {}, method="POST" if data else "GET")
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310
            body = response.read().decode()
    except (HTTPError, URLError) as exc:
        raise NotificationError(f"Request failed for {url}: {exc}") from exc
    if not body:
        return {}
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"text": body}


def get_linear_issue(linear_id: str, api_key: str) -> dict[str, Any]:
    """Fetch the current Linear issue state."""
    response = request_json(
        LINEAR_API_URL,
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        payload={
            "query": (
                "query CompletionIssue($id: String!) {"
                " issue(id: $id) { identifier title url state { name type } }"
                " }"
            ),
            "variables": {"id": linear_id},
        },
    )
    if response.get("errors"):
        raise NotificationError(f"Linear API returned errors: {response['errors']}")
    issue = response.get("data", {}).get("issue")
    if not issue:
        raise NotificationError(f"Linear issue {linear_id} was not found")
    return issue


def wait_for_linear_completion(linear_id: str, api_key: str) -> dict[str, Any]:
    """Poll briefly to allow the Linear GitHub integration to update the issue."""
    attempts = int(os.getenv("LINEAR_STATUS_ATTEMPTS", "12"))
    delay_seconds = int(os.getenv("LINEAR_STATUS_DELAY_SECONDS", "10"))
    issue: dict[str, Any] = {}
    for attempt in range(attempts):
        issue = get_linear_issue(linear_id, api_key)
        if is_completed(issue):
            return issue
        if attempt + 1 < attempts:
            time.sleep(delay_seconds)
    state_name = issue.get("state", {}).get("name", "unknown")
    raise NotificationError(
        f"Linear issue {linear_id} did not reach a completed state; current state: {state_name}"
    )


def main() -> None:
    """Verify mirrored completion and deliver the configured Slack notification."""
    required_env = (
        "GITHUB_EVENT_PATH",
        "GITHUB_REPOSITORY",
        "GITHUB_TOKEN",
        "LINEAR_API_KEY",
        "SLACK_WEBHOOK_URL",
    )
    missing = [name for name in required_env if not os.getenv(name)]
    if missing:
        raise NotificationError(f"Missing required Actions configuration: {', '.join(missing)}")

    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    pr = event["pull_request"]
    linear_id, issue_number = parse_issue_refs(pr.get("body") or "")
    repository = os.environ["GITHUB_REPOSITORY"]
    github_issue = request_json(
        f"https://api.github.com/repos/{repository}/issues/{issue_number}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    if github_issue.get("state") != "closed":
        raise NotificationError(f"GitHub issue #{issue_number} is not closed")
    if not github_issue.get("title", "").upper().startswith(f"{linear_id} "):
        raise NotificationError(f"GitHub issue #{issue_number} is not the mirror for {linear_id}")

    linear_issue = wait_for_linear_completion(linear_id, os.environ["LINEAR_API_KEY"])
    payload = build_slack_payload(pr, github_issue, linear_issue)
    request_json(
        os.environ["SLACK_WEBHOOK_URL"],
        headers={"Content-Type": "application/json"},
        payload=payload,
    )
    print(f"Completion notification sent for PR #{pr['number']} ({linear_id}/#{issue_number})")


if __name__ == "__main__":
    main()
