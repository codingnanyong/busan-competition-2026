# 2025 B-IMD weight and missing-data sensitivity analysis

## Purpose

COD-18 tests how strongly the baseline ranking depends on cross-domain weights and domain-score
availability. It does not replace the baseline; it supplies an uncertainty envelope for interpreting
priority areas.

## Run and outputs

```bash
docker compose run --rm jupyter python -m busan_imd.analysis.sensitivity_analysis
```

The executable contract is
[SENSITIVITY_SCENARIOS_2025.csv](../../data/SENSITIVITY_SCENARIOS_2025.csv). Summary metrics and
checksums are recorded in
[SENSITIVITY_ANALYSIS_REPORT_2025.json](../../data/manifests/SENSITIVITY_ANALYSIS_REPORT_2025.json).
Dong-level results are written to the Git-ignored
`data/processed/scores/2025/busan_admin_dong_sensitivity_2025.csv`.

## Scenarios

Nine scenarios are evaluated over the same 206 administrative dongs:

- published-weight baseline renormalized over six scored domains;
- equal domain weights of `1/6` each;
- median imputation when an observed domain score is missing; and
- six systematic domain-unavailability stress tests, each omitting one domain and renormalizing the
  remaining baseline weights row by row.

The current domain-score table has zero actual missing values. Median imputation is therefore exactly
identical to the baseline and cannot establish that one missing-data method is empirically superior.
Domain omission is a stress test of proxy dependence, not a claim that the domain is actually absent.

## Metrics

The report compares Spearman rank correlation, mean and maximum absolute rank change, decile
agreement, and overlap with the 21 dongs in the baseline most-deprived decile. Positive
`rank_change_from_baseline` means a dong becomes less deprived relative to the baseline.

## 2025 results

| Scenario | Rank correlation | Mean absolute change | Maximum change | Decile agreement | Top-decile overlap |
|---|---:|---:|---:|---:|---:|
| Equal weights | 0.935706 | 15.98 | 65 | 41.75% | 85.71% |
| Omit income | 0.816712 | 29.03 | 81 | 26.21% | 57.14% |
| Omit employment | 0.800421 | 28.61 | 91 | 28.16% | 66.67% |
| Omit education | 0.940855 | 16.75 | 48 | 34.47% | 80.95% |
| Omit health | 0.957656 | 13.26 | 46 | 46.12% | 85.71% |
| Omit housing/access | 0.986311 | 7.18 | 41 | 66.99% | 90.48% |
| Omit living environment | 0.985888 | 7.69 | 26 | 64.08% | 95.24% |

Equal weighting retains 18 of 21 baseline top-decile dongs, but only 41.75% of all dongs remain in
the same decile. Income and employment omission produce the largest instability. COD-19 should
therefore present equal-weight ranks, domain contributions, and top-decile persistence alongside the
single baseline rank.

## Limitations and decision

- Retain the baseline, but do not interpret its ranks as precise absolute ordering.
- Income is inferred for every dong and employment measures workplace opportunity rather than
  resident unemployment; their high influence is not itself a policy fact.
- Re-run complete-case, median-imputation, and row-renormalization comparisons if future inputs
  introduce actual missing domain scores.
- No Busan-context alternative weights are invented without independent evidence or policy agreement;
  the transparent published baseline and equal weights are the defensible comparators here.
