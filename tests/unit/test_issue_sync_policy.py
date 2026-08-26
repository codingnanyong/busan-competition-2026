import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def read_text(relative_path: str) -> str:
    return (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")


def test_pr_template_requires_both_mirrored_issue_references() -> None:
    template = read_text(".github/pull_request_template.md")

    assert "Closes COD-___" in template
    assert "Closes #___" in template
    assert "- Linear:" in template
    assert "- GitHub:" in template


def test_pr_policy_validates_and_closes_the_mirrored_github_issue() -> None:
    workflow = read_text(".github/workflows/pr-policy.yml")

    assert "Verify Linear and GitHub issue pair" in workflow
    assert "close-mirrored-github-issue:" in workflow
    assert "github.event.pull_request.merged == true" in workflow
    assert "github.event.action != 'closed' && github.event.pull_request.merged != true" in workflow
    assert 'state_reason: "completed"' in workflow
    assert "github.event.action != 'closed' && github.base_ref == 'main'" in workflow


def test_process_docs_keep_integration_secrets_in_one_guide() -> None:
    git_workflow = read_text("docs/kor/GIT_WORKFLOW.md")
    git_workflow_en = read_text("docs/eng/GIT_WORKFLOW.md")
    integrations = read_text("docs/kor/INTEGRATIONS.md")
    integrations_en = read_text("docs/eng/INTEGRATIONS.md")
    issues = read_text("docs/kor/ISSUES.md")
    issues_en = read_text("docs/eng/ISSUES.md")

    assert "INTEGRATIONS.md" in git_workflow
    assert "INTEGRATIONS.md" in git_workflow_en
    assert "LINEAR_API_KEY" not in git_workflow
    assert "LINEAR_API_KEY" not in git_workflow_en
    assert "LINEAR_API_KEY" in integrations
    assert "LINEAR_API_KEY" in integrations_en
    assert "feat/<linear-id>-<slug>" not in issues
    assert "feat/<linear-id>-<slug>" not in issues_en
    assert "INTEGRATIONS.md" in issues
    assert "INTEGRATIONS.md" in issues_en


def test_bilingual_issue_maps_contain_every_mirror_pair() -> None:
    mappings = {linear_id: linear_id + 9 for linear_id in range(5, 29)}
    mappings[29] = 39
    mappings[30] = 44
    mappings[31] = 48
    mappings[32] = 52
    mappings[33] = 59
    mappings[34] = 62
    mappings[35] = 67
    mappings[36] = 69
    mappings[37] = 72
    mappings[38] = 74
    mappings[39] = 77

    for path in ("docs/kor/ISSUES.md", "docs/eng/ISSUES.md"):
        issue_map = read_text(path)
        for linear_id, github_number in mappings.items():
            row_pattern = (
                rf"\| (?:M\d|—) \| \[COD-{linear_id}\]\([^)]*\) \| "
                rf"\[#{github_number}\]\([^)]*/issues/{github_number}\) \|"
            )
            assert re.search(row_pattern, issue_map), (
                f"Missing COD-{linear_id}/#{github_number} in {path}"
            )
