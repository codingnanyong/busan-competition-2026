# 2025 B-IMD composite, rank, and decile

## Scope and interpretation

COD-17 combines the six 2025 domain scores for all 206 Busan administrative dongs into an
experimental `B-IMD 2025` composite, within-Busan rank, and decile. Higher composite scores mean
greater relative living-condition deprivation; rank and decile `1` are the most deprived.

This is an open-data experimental result for relative comparison within Busan. It is not an
official statistic, an individual assessment, a statutory funding formula, or an absolute score
that can be compared directly across years or cities.

## Run

After restoring the raw-data bundle, run the complete pipeline:

```bash
docker compose run --rm jupyter python scripts/rebuild_processed.py
```

To regenerate only the stage after domain scoring:

```bash
docker compose run --rm jupyter python -m busan_imd.analysis.composite_index
```

The executable contract is
[COMPOSITE_INDEX_SPEC_2025.csv](../../data/tables/COMPOSITE_INDEX_SPEC_2025.csv). Input/output hashes and
summary checks are recorded in
[COMPOSITE_INDEX_REPORT_2025.json](../../data/manifests/COMPOSITE_INDEX_REPORT_2025.json). The
result table is generated at the Git-ignored
`data/processed/scores/2025/busan_admin_dong_imd_2025.csv`.

## Domain weights

The baseline starts from the seven published weights in the UK government's
[English Indices of Deprivation 2025](https://www.gov.uk/government/statistics/english-indices-of-deprivation-2025/english-indices-of-deprivation-2025-statistical-release).
Safety is held because no direct dong-level incident indicator is available. The remaining six
published weights, which total `0.906`, are therefore renormalized to sum to one.

| B-IMD domain | Published weight | Six-domain normalized weight |
|---|---:|---:|
| Income | 22.5% | 24.8344% |
| Employment | 22.5% | 24.8344% |
| Education | 13.5% | 14.9007% |
| Health | 13.5% | 14.9007% |
| Housing and service access | 9.3% | 10.2649% |
| Living environment | 9.3% | 10.2649% |

This mapping is a documented, reproducible baseline; it does not claim that the English and Busan
indicators are equivalent. The [2025 sensitivity analysis](SENSITIVITY_ANALYSIS_2025.md) tests rank
stability under equal weights and systematic domain-unavailability scenarios.

## Calculation contract

For 0-100 domain score `domain_score_d` and normalized weight `w_d`:

```text
B_IMD_score = sum(w_d * domain_score_d)
```

- Scores are sorted descending and assigned ranks `1` through `206`.
- Equal scores are ordered by ascending administrative-dong code for deterministic output.
- Ordered ranks are split into ten deciles; `1` is the most deprived approximately 10%.
- With 206 dongs, each decile contains 20 or 21 dongs.

The 2025 run ranges from `20.956227` to `82.821838`, with a median of `51.048498`. The
[2025 priority-area contribution analysis](PRIORITY_AREAS_2025.md) interprets priority areas
and their domain contributions.

## Limitations

- This is a six-domain baseline with safety held, not a complete seven-domain index.
- Every scored domain still contains direct-measure or conditional-proxy limitations.
- Ranks and deciles can visually magnify small score differences and must accompany raw scores.
- Rank shifts under equal weights and domain-unavailability scenarios must be read alongside the
  sensitivity results.
