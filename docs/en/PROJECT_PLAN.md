# Project Plan

## Objective

Measure living-condition deprivation across Busan's administrative dongs in the income, employment, education, health, safety, housing and service access, and living-environment domains, then recommend place-based policy priorities grounded in the analysis.

## Top-level milestones

| ID | Milestone | Target | Definition of done |
|---|---|---:|---|
| M0 | Project governance and reproducible environment | 2026-08-12 | Git policy, Docker/Jupyter environment, core documentation, and CI are ready |
| M1 | Competition requirements and data availability | 2026-08-17 | Official template and criteria are confirmed; candidate data and spatial units are set for all seven domains |
| M2 | Data collection and administrative-dong standardization | 2026-08-24 | Raw data, provenance metadata, administrative-code mapping, and data dictionary are ready |
| M3 | EDA and Busan IMD model | 2026-08-31 | Quality checks, normalization, domain scores, weighted composite, and sensitivity analysis are reproducible |
| M4 | Area interpretation, policy, and visualization | 2026-09-07 | Priority areas and drivers are interpreted; policy matrix and map draft are complete |
| M5 | Submission artifacts and quality assurance | 2026-09-14 | One-page PDF, HWPX/PDF report, and data package are reviewed |
| M6 | Submission release v1.0.0 | 2026-09-18 | Final ZIP is submitted and `v1.0.0`, GitHub Release, and release documentation are published |
| M7 | Presentation package | 2026-10-29 | If shortlisted, slides, demo, and anticipated Q&A are complete |

## Core backlog

### M0 — Governance and environment

- Establish repository branch, pull-request, release, and documentation policy
- Configure a Docker-based Jupyter/GeoPandas environment
- Create the project structure and baseline quality automation

### M1 — Requirements and data design

- Confirm the competition notice, submission template, and evaluation criteria
- Draft Busan IMD domains, indicators, and weights
- Audit administrative-dong data availability and define fallback rules

### M2 — Data foundation

- Obtain administrative-dong reference codes and boundaries
- Collect raw domain data and record provenance metadata
- Implement code matching, missing-data, and unit-standardization pipelines
- Produce a data dictionary and quality report

### M3 — Analytical model

- Complete EDA notebooks and data-quality checks
- Implement indicator direction, normalization, and domain scoring
- Implement IMD weighting, ranking, and deciles
- Run weight and missing-data sensitivity analysis

### M4 — Interpretation and policy

- Analyze priority areas and domain contributions
- Use clustering only when it adds stable and interpretable value
- Evaluate Busan-specific environmental-exposure overlays
- Build a policy-priority and implementation matrix by deprivation type
- Produce a one-page map and infographic draft

### M5–M7 — Submission, release, and presentation

- Write the analytical report and evidence documentation
- Complete the one-page visualization PDF
- Verify reproducibility of submission data, code, and README
- Publish v1.0.0 and submit the final package
- Prepare slides, demo, and Q&A

## Key risks

| Risk | Response |
|---|---|
| Some indicators are available only at district level | Fix the spatial unit and fallback indicators in M1; prohibit unexplained mixed-granularity scoring |
| Crime, income, or employment data are unavailable or delayed | Pre-document public proxy indicators and exclusion criteria |
| Administrative-dong names and codes do not match | Use one reference-year administrative-code table as the canonical join key |
| Weights appear arbitrary | Use UK IMD weights as the baseline and compare equal and alternative weights |
| Solo execution misses validation | Require an artifact, verification method, and documentation update in every issue |

