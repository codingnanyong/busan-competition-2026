# GitHub, Linear, and Slack Integration Operations

## Automation scope

After a `feat/* → develop` pull request is merged, the `PR policy` workflow:

1. validates the `Closes COD-n` and `Closes #n` pair in the PR body;
2. closes the mirrored GitHub Issue as completed;
3. polls for up to two minutes while the Linear GitHub integration moves the Linear issue to Done; and
4. posts the PR, merge commit, GitHub, and Linear links to Slack only after both issues are complete.

If Linear completion or Slack delivery fails, no success message is sent and the Actions job fails.
Merged pull requests are not re-validated when Linear later edits the GitHub PR. The mirrored
GitHub Issue is already closed by then, so repeating the pre-merge open-issue check would send a
false failure alert.

## One-time external setup

### 1. Linear API key

Create a key under **Linear Settings → Security & access → Personal API keys**. The key owner must be able to read issues and statuses for the `COD` team.

Store it in **GitHub repository Settings → Secrets and variables → Actions → Secrets** as:

```text
LINEAR_API_KEY
```

### 2. Slack Incoming Webhook

Enable Incoming Webhooks for a Slack app and select the conversation that will receive completion notifications. Store the generated URL as this GitHub Actions Secret:

```text
SLACK_WEBHOOK_URL
```

The webhook should only post to the selected conversation. If workspace policy does not allow selecting a personal DM, create a dedicated private channel containing only the user and the Slack app.

### 3. Enable the automation

After both secrets are present, add this repository Actions Variable under **Settings → Secrets and variables → Actions → Variables**:

```text
COMPLETION_NOTIFICATIONS_ENABLED=true
```

When using the CLI, enter secret values through standard input instead of command-line arguments:

```bash
gh secret set LINEAR_API_KEY --repo codingnanyong/busan-competition-2026
gh secret set SLACK_WEBHOOK_URL --repo codingnanyong/busan-competition-2026
gh variable set COMPLETION_NOTIFICATIONS_ENABLED --body true \
  --repo codingnanyong/busan-competition-2026
```

## Required permissions

- GitHub: repository administration access to manage Actions Secrets and Variables
- Linear: permission to create a personal API key and read `COD` team issues
- Slack: permission to install an app or add an Incoming Webhook and invite it to the target conversation
- Linear GitHub integration: a team workflow that moves the linked Linear issue to Done when a PR merges into `develop`

## Verification and recovery

1. Create a test mirrored issue pair and pull request.
2. Merge the pull request into `develop`.
3. Confirm GitHub Issue Closed and Linear Done.
4. Confirm the `notify-completion` job succeeds and the Slack message contains all four links.

Failure logs identify missing configuration or incomplete state without printing secret values. Leave the Variable absent or set to `false` until both secrets are ready. While automation is disabled, the work session that performs the merge must verify both issue states and post the result to Slack manually.

## Creating Linear issues

Create new COD issues with the `Create Linear issue` workflow. It attaches each issue to team
`COD` and project
[Busan IMD Living-Vulnerability Analysis 2026](https://linear.app/codingnanyong/project/부산-imd-생활취약지역-분석-2026-83133e455764).
Creation fails instead of opening an unscoped issue if that project is missing.

```bash
gh workflow run create-linear-issue.yml --ref develop \
  -f title="work title" \
  -f description="goal and acceptance"
```

Use `--ref develop` until the workflow is on `main`.
