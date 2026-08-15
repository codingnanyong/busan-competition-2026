# Git Branch and Pull-Request Policy

## Branch flow

```text
feat/<linear-id>-<slug>
          │ PR (Squash merge)
          │ Closes <LINEAR-ID> + Closes #<GITHUB-ISSUE>
          ▼
       develop
          │ Release PR (Merge commit)
          ▼
        main
          │
          ├─ tag: vX.Y.Z
          ├─ GitHub Release
          └─ bilingual docs → GitHub Wiki
```

Only the initial repository commit is allowed as a bootstrap exception. Direct pushes to `develop` and `main` are prohibited afterward.

## Branch names

- Feature, analysis, data, and documentation work: `feat/<linear-id>-<slug>`
- Example: `feat/cod-12-data-source-audit`
- Keep each branch small enough to close one mirrored Linear/GitHub issue pair.

## Pull-request rules

### `feat/* → develop`

- Title: `<LINEAR-ID> <type>: <summary>`
- Include both `Closes <LINEAR-ID>` and `Closes #<GITHUB-ISSUE>` in the body.
- CI verifies that the branch, title, Linear ID, and mirrored GitHub Issue all identify the same work item.
- Update both Korean and English documentation when analytical results, data contracts, or user-visible behavior change.
- Squash merge only after CI, reproducibility checks, and acceptance criteria pass.
- On merge to `develop`, the workflow closes the GitHub Issue and the Linear integration synchronizes the Linear issue to Done.
- Delete the remote `feat/*` branch immediately after the merge completes.

## Issue mirroring rules

- Linear and GitHub Issues are one-to-one copies of the same work item.
- Create new work in both systems with matching title, description, priority, milestone, due date, and assignee.
- Store the GitHub Issue link in Linear and the Linear link in the GitHub Issue.
- When content or state changes, update both copies in the same work session.
- GitHub Issues provide public traceability and PR completion; Linear owns scheduling, priority, and milestone operations.
- If automation fails, reconcile both states immediately from the merged PR result.

### `develop → main`

- `main` accepts pull requests only from `develop`.
- Update `VERSION`, `CHANGELOG.md`, `docs/releases/vX.Y.Z.md`, and the matching English release note.
- The version must be greater than every existing tag and follow Semantic Versioning.
- The merge automatically creates a tag, GitHub Release, and bilingual Wiki update.

## Definition of done

- Code or artifact exists in the repository.
- Execution and verification results are recorded in the pull request.
- Korean and English documentation are updated where required.
- The pull request is merged into `develop`.
- The GitHub Issue is closed as completed and the Linear issue is synchronized to Done.
- The merged remote work branch is deleted.

## Recommended branch protection

- `develop`: pull request required, `PR policy` required, direct pushes disabled
- `main`: pull request required, `PR policy` required, only `develop` accepted as head, direct pushes disabled
- Force pushes and deletion disabled for protected branches (`develop`, `main`)
- Merged work branches (`feat/*`) are deleted automatically or manually
- Conversation resolution and up-to-date base required
