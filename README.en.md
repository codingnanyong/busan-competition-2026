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

See the [project plan](docs/en/PROJECT_PLAN.md), [competition submission requirements and official template](docs/en/COMPETITION_REQUIREMENTS.md), [Linear issue map](docs/en/ISSUES.md), [Git workflow](docs/en/GIT_WORKFLOW.md), and [release policy](docs/en/RELEASE_POLICY.md). Current feasibility and future expansion requirements are maintained in the [data availability matrix](docs/en/data/AVAILABILITY_MATRIX.md) and [B-IMD expansion model](docs/en/methodology/EXPANSION_MODEL.md).

## Target deliverables

1. Composite and domain deprivation scores for each administrative dong in Busan
2. Deprivation typology and policy priorities
3. One-page data-visualization PDF
4. Analysis report in HWPX and PDF
5. Reproducible raw/processed data and analysis code
6. A documented open-data boundary and institutional data-request roadmap

## Analytical status

B-IMD is an experimental composite for exploring relative living-condition deprivation across Busan administrative dongs. It is not an official statistic, an individual deprivation assessment, or a statutory funding formula. Results disclose direct and proxy measures and data confidence.
