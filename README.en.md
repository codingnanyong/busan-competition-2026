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

See the [project plan](docs/eng/PROJECT_PLAN.md), [competition submission requirements and official template](docs/eng/COMPETITION_REQUIREMENTS.md), [Docker-based analysis environment](docs/eng/DEVELOPMENT_ENVIRONMENT.md), [macOS setup](docs/kor/MACOS_SETUP.md), [project structure](docs/eng/PROJECT_STRUCTURE.md), and [Linear/GitHub issue map](docs/eng/ISSUES.md). Current feasibility and future expansion requirements are maintained in the [data availability matrix](docs/eng/data/AVAILABILITY_MATRIX.md) and [B-IMD expansion model](docs/eng/methodology/EXPANSION_MODEL.md); candidate decisions are documented in the [2025 EDA](docs/eng/data/EDA_2025.md), normalization and domain scoring in the [2025 domain-score method](docs/eng/methodology/DOMAIN_SCORES_2025.md), composite scores, ranks, and deciles in the [2025 B-IMD composite method](docs/eng/methodology/COMPOSITE_INDEX_2025.md), result stability in the [2025 sensitivity analysis](docs/eng/methodology/SENSITIVITY_ANALYSIS_2025.md), priority-area drivers in the [2025 contribution analysis](docs/eng/methodology/PRIORITY_AREAS_2025.md), the typology decision in the [2025 clustering review](docs/eng/methodology/CLUSTER_ANALYSIS_2025.md), ambient-air double burden in the [2025 environmental overlay](docs/eng/methodology/ENVIRONMENTAL_OVERLAY_2025.md), action candidates in the [2025 policy-priority matrix](docs/eng/methodology/POLICY_MATRIX_2025.md), the submission visual draft in the [2025 one-page infographic](docs/eng/methodology/INFOGRAPHIC_2025.md), the contest-archive draft in the [2025 submission draft](docs/eng/methodology/SUBMISSION_DRAFT_2025.md), and the package review in the [2025 reproducibility review](docs/eng/methodology/REPRODUCIBILITY_QA_2025.md).

Evidence and row-level confidence for three major and eight child policy categories, including
estimated, proxy, and interpolated inputs, are maintained in the
[2025 category assessment](docs/eng/methodology/CATEGORY_ASSESSMENT_2025.md).

## Target deliverables

1. Composite and domain deprivation scores for each administrative dong in Busan
2. Deprivation typology and policy priorities
3. One-page data-visualization PDF
4. Analysis report in HWPX and PDF
5. Reproducible raw/processed data and analysis code
6. A documented open-data boundary and institutional data-request roadmap

## Analytical status

B-IMD is an experimental composite for exploring relative living-condition deprivation across Busan administrative dongs. It is not an official statistic, an individual deprivation assessment, or a statutory funding formula. Results disclose direct and proxy measures and data confidence.

## Contributing and license

Code and project documentation are under the [MIT License](LICENSE). Source open-data
terms stay with their providers. See [CONTRIBUTING.md](CONTRIBUTING.md),
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and [SECURITY.md](SECURITY.md).
