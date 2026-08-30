# 2025 contest submission draft

## Scope

COD-24 builds a **machine-written draft** of the Track 1 archive: the one-page visualization,
the analysis-report PDF, and redistributable derived tables. The official HWPX report is
filled in Hangul by pasting the markdown body into a copy of the contest template. This
step does not copy the blank template in as the submitted report.

The artifact status is `submission_draft`. The Git draft and the contest ZIP differ. The
contest ZIP lives in `outputs/contest-upload/2025/` and Drive `output`. It carries the
Hangul HWPX, official PDF, one-page visual, derived tables, and the browser dashboard.
Leave the application number blank. Upload the consent PDF outside the ZIP.
Reproducibility, page counts, and license exclusions are recorded in
[2025 submission reproducibility review](REPRODUCIBILITY_QA_2025.md). COD-26 publishes
v1.0.0, the GitHub Release, and the Wiki.

## Package

| File | Role |
|---|---|
| [`01_data-visualization.pdf`](../../../outputs/submission/2025/01_data-visualization.pdf) | Copy of the COD-23 one-page PDF. Exactly one page |
| [`02_analysis-report.pdf`](../../../outputs/submission/2025/02_analysis-report.pdf) | Pipeline draft PDF. Not the contest file |
| `02_analysis-report-official.pdf` | Hangul-exported official PDF. Not committed |
| `02_analysis-report.hwpx` | Hangul-authored report. Not kept in the Git draft |
| [`02_analysis-report.md`](../../../outputs/submission/2025/02_analysis-report.md) | Korean body that was pasted into the template |
| [`03_data/source-catalog.csv`](../../../outputs/submission/2025/03_data/source-catalog.csv) | Provenance, dates, licenses, and decisions for 42 audited datasets. XLSX is regenerated locally |
| `03_data/README.txt` | Why raw extracts are omitted and how to refetch them |
| `04_interactive/` | Copied into the contest ZIP only from `outputs/infographic/2025/interactive/` |
| [`03_data/data-dictionary.csv`](../../../outputs/submission/2025/03_data/data-dictionary.csv) | Analysis-column dictionary |
| `03_data/*.csv` | Dong-level profile and category-assessment tables |
| [`README.md`](../../../outputs/submission/2025/README.md) | Hangul paste instructions |
| [SUBMISSION_DRAFT_REPORT_2025.json](../../data/manifests/SUBMISSION_DRAFT_REPORT_2025.json) | Page counts, checksums, and HWPX status |

`data/raw`, non-redistributable extracts, and personal identifiers are omitted. The one-page
visual follows the [2025 one-page infographic](INFOGRAPHIC_2025.md). The browser dashboard
from that document is copied into the contest ZIP as `04_interactive/`.

## Rebuild

Run from the repository root in the Docker image that ships Noto Sans CJK.

```bash
docker compose run --rm jupyter python -m busan_imd.submission
```

The full processed-data rebuild writes the same package as its final step.

```bash
docker compose run --rm jupyter python scripts/rebuild_processed.py
```

## Report outline

The body uses the official section titles:

1. Overview: purpose, need, tools and process, headline results
2. Data used: include-gate, domain sources, excluded and validation-only datasets
3. Method: preprocessing, normalization and weights, category assessment, validation
4. Results: top ten dongs, exploratory types, sensitivity, limits and prohibited uses
5. Application: operators and type-specific policy candidates
6. Expected effects and references: quantitative and qualitative effects, rebuild command

The cover is excluded from the page limit. The consent form and application number are
completed on the template original at submission time.

## HWPX

1. Copy
   [`docs/templates/2026-big-data-competition-submission-template.hwpx`](../../templates/2026-big-data-competition-submission-template.hwpx).
   Do not edit the template original in the repository.
2. Open the copy in Hangul and paste `02_analysis-report.md` into the matching sections.
3. Fill cover fields except the application number.
4. Sign the personal-data consent form at submission. This analysis does not collect
   personal identifiers.
5. COD-25 checks that the HWPX and PDF share titles, tables, and page structure.

## Limits

Draft figures match the committed 2025 scores and infographic. Proxy measures, the
six-domain composite, ecological fallacy, and prohibited uses follow
[Limitations](LIMITATIONS.md) and body section 4. The blank HWPX template is not the
submitted report.
