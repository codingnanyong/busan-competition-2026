# Busan Index of Multiple Deprivation (IMD) Analysis

**English** | [한국어](README.ko.md)

This project adapts the UK Index of Multiple Deprivation (IMD) to Busan's administrative-dong level to identify multidimensional deprivation, explain its local drivers, and prioritize place-based policy interventions.

## Operating principles

- Linear issues are the unit of work.
- Every implementation starts from a `feat/<linear-id>-<slug>` branch.
- `feat/*` branches merge into `develop` only through pull requests.
- Release-ready `develop` merges into `main` only through a release pull request.
- A merge to `main` publishes a Git tag and GitHub Release from `VERSION`.
- Evidence, decisions, the data dictionary, and release changes are maintained in both Korean and English.

See the [project plan](docs/en/PROJECT_PLAN.md), [Linear issue map](docs/en/ISSUES.md), [Git workflow](docs/en/GIT_WORKFLOW.md), and [release policy](docs/en/RELEASE_POLICY.md).

## Target deliverables

1. Composite and domain deprivation scores for each administrative dong in Busan
2. Deprivation typology and policy priorities
3. One-page data-visualization PDF
4. Analysis report in HWPX and PDF
5. Reproducible raw/processed data and analysis code

