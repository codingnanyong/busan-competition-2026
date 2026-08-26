"""Create a Linear COD-team issue on the contest project using the Actions API key."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

LINEAR_API_URL = "https://api.linear.app/graphql"
DEFAULT_TEAM_KEY = "COD"
DEFAULT_PROJECT_SLUG = "83133e455764"
DEFAULT_PROJECT_NAME = "부산 IMD 생활취약지역 분석 2026"


def graphql(query: str, variables: dict | None = None) -> dict:
    request = urllib.request.Request(
        LINEAR_API_URL,
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={
            "Authorization": os.environ["LINEAR_API_KEY"],
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Linear HTTP error: {exc}") from exc


def data_or_die(body: dict) -> dict:
    if body.get("errors"):
        raise SystemExit(f"Linear API errors: {body['errors']}")
    data = body.get("data")
    if not data:
        raise SystemExit(f"Linear API returned no data: {body}")
    return data


def select_project(nodes: list[dict[str, Any]], slug: str, name: str) -> dict[str, Any]:
    """Pick the contest project by slug, then by exact name."""
    for node in nodes:
        if node.get("slugId") == slug or node.get("id") == slug:
            return node
    matches = [node for node in nodes if node.get("name") == name]
    if len(matches) == 1:
        return matches[0]
    raise SystemExit(
        f"Linear project was not found for slug={slug!r} name={name!r}; "
        f"candidates={[node.get('name') for node in nodes]}"
    )


def issue_create_input(
    team_id: str, project_id: str, title: str, description: str
) -> dict[str, str]:
    """Build IssueCreateInput with the contest project required."""
    return {
        "teamId": team_id,
        "projectId": project_id,
        "title": title,
        "description": description,
    }


def main() -> None:
    title = os.environ["LINEAR_ISSUE_TITLE"]
    description = os.environ.get("LINEAR_ISSUE_DESCRIPTION", "")
    team_key = os.environ.get("LINEAR_TEAM_KEY", DEFAULT_TEAM_KEY)
    project_slug = os.environ.get("LINEAR_PROJECT_SLUG", DEFAULT_PROJECT_SLUG)
    project_name = os.environ.get("LINEAR_PROJECT_NAME", DEFAULT_PROJECT_NAME)

    teams = data_or_die(
        graphql(
            "query($key: String!) { teams(filter: { key: { eq: $key } }) { nodes { id key } } }",
            {"key": team_key},
        )
    )["teams"]["nodes"]
    if not teams:
        raise SystemExit(f"Linear team {team_key} was not found")

    by_slug = data_or_die(
        graphql(
            """
            query($slug: String!) {
              projects(filter: { slugId: { eq: $slug } }) { nodes { id name slugId url } }
            }
            """,
            {"slug": project_slug},
        )
    )["projects"]["nodes"]
    if not by_slug:
        by_slug = data_or_die(
            graphql(
                """
                query($name: String!) {
                  projects(filter: { name: { eq: $name } }) { nodes { id name slugId url } }
                }
                """,
                {"name": project_name},
            )
        )["projects"]["nodes"]
    project = select_project(by_slug, project_slug, project_name)

    created = data_or_die(
        graphql(
            """
            mutation($input: IssueCreateInput!) {
              issueCreate(input: $input) {
                success
                issue {
                  identifier
                  url
                  title
                  project { id name url }
                }
              }
            }
            """,
            {
                "input": issue_create_input(
                    teams[0]["id"], project["id"], title, description
                )
            },
        )
    )["issueCreate"]
    if not created["success"] or not created["issue"]:
        raise SystemExit(f"Linear issueCreate failed: {created}")
    issue = created["issue"]
    attached = issue.get("project") or {}
    if attached.get("id") != project["id"]:
        raise SystemExit(
            f"Linear issue {issue['identifier']} was created without project "
            f"{project['name']}"
        )
    print(
        f"created {issue['identifier']} {issue['url']} "
        f"project={attached.get('name')}"
    )


if __name__ == "__main__":
    sys.exit(main())
