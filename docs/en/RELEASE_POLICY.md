# Version, Release, and Documentation Policy

## Versioning

Use Semantic Versioning (`MAJOR.MINOR.PATCH`).

- MAJOR: incompatible analytical-method or submission-contract change
- MINOR: new data domain, analytical capability, visualization, or policy module
- PATCH: bug fix, data correction, or documentation improvement

## Release procedure

1. Validate the release candidate on `develop`.
2. Increment `VERSION`.
3. Update `CHANGELOG.md` and Korean/English release notes.
4. Create and merge the `develop → main` release pull request.
5. GitHub Actions creates `vX.Y.Z` and the GitHub Release.
6. The latest Korean and English documentation is published to GitHub Wiki.
7. Complete the Linear milestone and mirrored Linear/GitHub issues, then share the result in Slack.

Every merge to `main` must carry a unique version. The release fails if the tag already exists.

## Bilingual documentation layout

- `README.md`: bilingual language gateway
- `README.ko.md`: Korean project home
- `README.en.md`: English project home
- `docs/*.md`: Korean canonical project documents
- `docs/en/*.md`: English counterparts
- `docs/GIT_WORKFLOW.md`: branch, PR, and issue policy
- `docs/INTEGRATIONS.md`: Linear issue creation and Slack completion operations
- `docs/releases/`: Korean release notes
- `docs/en/releases/`: English release notes
- `docs/data/` and `docs/en/data/`: data catalog and dictionary
- `docs/methodology/` and `docs/en/methodology/`: indicators, normalization, weights, and sensitivity analysis

Wiki pages are generated with `KO-*` and `EN-*` prefixes plus a shared `_Sidebar.md`. A document change is complete only when its required counterpart is updated or the pull request explicitly explains why translation is not applicable.
