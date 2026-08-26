# Version, Release, and Documentation Policy

## Versioning

Use Semantic Versioning (`MAJOR.MINOR.PATCH`).

- MAJOR: incompatible analytical-method or submission-contract change
- MINOR: new data domain, analytical capability, visualization, or policy module
- PATCH: bug fix, data correction, or documentation improvement

## Release procedure

1. Validate the release candidate on `develop`.
2. Increment `VERSION`.
3. Update `CHANGELOG.md`, `docs/kor/releases/vX.Y.Z.md`, and `docs/eng/releases/vX.Y.Z.md`.
4. Create and merge the `develop → main` release pull request.
5. GitHub Actions creates `vX.Y.Z` and the GitHub Release.
6. The latest Korean and English documentation is published to GitHub Wiki.
7. Complete the Linear milestone and mirrored Linear/GitHub issues, then share the result in Slack.

Every merge to `main` must carry a unique version. The release fails if the tag already exists.

## Bilingual documentation layout

- `README.md`: bilingual language gateway
- `README.ko.md`: Korean project home
- `README.en.md`: English project home
- `docs/kor/`: Korean prose for plans, workflow, data notes, methods, and release notes
- `docs/eng/`: English counterparts
- `docs/data/tables/`, `docs/data/manifests/`: language-neutral CSVs and checksum JSON rewritten by the pipeline
- `docs/templates/`: submission templates

Wiki pages are generated with `KO-*` and `EN-*` prefixes plus a shared `_Sidebar.md`. A document change is complete only when its required counterpart is updated or the pull request explicitly explains why translation is not applicable.
