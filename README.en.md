# Busan Index of Multiple Deprivation (IMD) Analysis

**English** | [한국어](README.ko.md)

This project adapts the UK Index of Multiple Deprivation (IMD) to Busan's administrative-dong level to identify multidimensional deprivation, explain its local drivers, and prioritize place-based policy interventions.

## Operating principles

- One-to-one mirrored Linear/GitHub issue pairs are the unit of work.
- Every implementation starts from a `feat/<linear-id>-<slug>` branch.
- `feat/*` branches merge into `develop` only through pull requests.
- Release-ready `develop` merges into `main` only through a release pull request.
- A merge to `main` publishes a Git tag and GitHub Release from `VERSION`.
- Evidence, decisions, the data dictionary, and release changes are maintained in both Korean and English.

See the [project plan](docs/en/PROJECT_PLAN.md), [competition submission requirements and official template](docs/en/COMPETITION_REQUIREMENTS.md), [Docker-based analysis environment](docs/en/DEVELOPMENT_ENVIRONMENT.md), [macOS setup](docs/MACOS_SETUP.md), [project structure](docs/PROJECT_STRUCTURE.md), and [Linear/GitHub issue map](docs/en/ISSUES.md). Current feasibility and future expansion requirements are maintained in the [data availability matrix](docs/en/data/AVAILABILITY_MATRIX.md) and [B-IMD expansion model](docs/en/methodology/EXPANSION_MODEL.md); candidate decisions are documented in the [2025 EDA](docs/en/data/EDA_2025.md), normalization and domain scoring in the [2025 domain-score method](docs/en/methodology/DOMAIN_SCORES_2025.md), composite scores, ranks, and deciles in the [2025 B-IMD composite method](docs/en/methodology/COMPOSITE_INDEX_2025.md), result stability in the [2025 sensitivity analysis](docs/en/methodology/SENSITIVITY_ANALYSIS_2025.md), priority-area drivers in the [2025 contribution analysis](docs/en/methodology/PRIORITY_AREAS_2025.md), the typology decision in the [2025 clustering review](docs/en/methodology/CLUSTER_ANALYSIS_2025.md), ambient-air double burden in the [2025 environmental overlay](docs/en/methodology/ENVIRONMENTAL_OVERLAY_2025.md), action candidates in the [2025 policy-priority matrix](docs/en/methodology/POLICY_MATRIX_2025.md), and the submission visual draft in the [2025 one-page infographic](docs/en/methodology/INFOGRAPHIC_2025.md).

## Target deliverables

1. Composite and domain deprivation scores for each administrative dong in Busan
2. Deprivation typology and policy priorities
3. One-page data-visualization PDF
4. Analysis report in HWPX and PDF
5. Reproducible raw/processed data and analysis code
6. A documented open-data boundary and institutional data-request roadmap

## Analytical status

B-IMD is an experimental composite for exploring relative living-condition deprivation across Busan administrative dongs. It is not an official statistic, an individual deprivation assessment, or a statutory funding formula. Results disclose direct and proxy measures and data confidence.
