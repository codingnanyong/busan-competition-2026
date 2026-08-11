# Git Branch and Pull-Request Policy

## Branch flow

```text
feat/<linear-id>-<slug>
          │ PR (Squash merge, Closes <LINEAR-ID>)
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
- Keep each branch small enough to close one Linear issue.

## Pull-request rules

### `feat/* → develop`

- Title: `<LINEAR-ID> <type>: <summary>`
- Include `Closes <LINEAR-ID>` in the body.
- Update both Korean and English documentation when analytical results, data contracts, or user-visible behavior change.
- Squash merge only after CI, reproducibility checks, and acceptance criteria pass.
- Delete the remote `feat/*` branch immediately after the merge completes.

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
- The Linear issue is closed by the pull request or synchronized to Done.
- The merged remote work branch is deleted.

## Recommended branch protection

- `develop`: pull request required, `PR policy` required, direct pushes disabled
- `main`: pull request required, `PR policy` required, only `develop` accepted as head, direct pushes disabled
- Force pushes and deletion disabled for protected branches (`develop`, `main`)
- Merged work branches (`feat/*`) are deleted automatically or manually
- Conversation resolution and up-to-date base required

