# 2025 B-IMD domain scores

## Scope

COD-16 aligns candidate indicators to one deprivation direction, converts them to 0-100
percentile scores, and calculates within-domain scores for all 206 Busan administrative dongs. A
higher value means greater relative deprivation within Busan. This stage deliberately creates no
cross-domain composite, rank, or decile; those belong to the
[COD-17 composite-index stage](COMPOSITE_INDEX_2025.md).

## Run

After restoring the raw-data bundle, run the complete pipeline:

```bash
docker compose run --rm jupyter python scripts/rebuild_processed.py
```

To regenerate only this stage:

```bash
docker compose run --rm jupyter python -m busan_imd.analysis.domain_scores
```

The executable contract is [DOMAIN_SCORE_SPEC_2025.csv](../../data/tables/DOMAIN_SCORE_SPEC_2025.csv).
Input and output hashes and summary checks are recorded in
[DOMAIN_SCORE_REPORT_2025.json](../../data/manifests/DOMAIN_SCORE_REPORT_2025.json). Generated CSV
files are written to the Git-ignored `data/processed/scores/2025/` directory.

## Normalization

Each indicator receives its contracted `identity` or `log1p` transform and an average rank. Ties
share the average rank. For `N` dongs and average rank `r_i`, a higher-is-more-deprived indicator is
mapped as:

```text
score_i = 100 * (r_i - 1) / (N - 1)
```

Higher-is-better access indicators use `100 - score_i`. Every normalized indicator and domain
score therefore has one interpretation: higher means greater relative deprivation. Rank
percentiles limit the influence of extreme magnitudes, but they are relative within Busan and
cannot be compared as absolute levels across years or places.

## Base-domain contract

| Domain | Base indicators | Direction | Within-domain weight |
|---|---|---|---:|
| Income | Inferred basic-livelihood recipient rate | Higher is deprived | 1.0 |
| Employment | Workplace workers (`log1p`) | Lower is deprived | 1.0 |
| Education | Nearest core-school distance | Higher is deprived | 1.0 |
| Health | Hospital and clinic rates | Lower is deprived | 0.5 each |
| Housing/access | Old-housing lower-bound share and bus-stop rate | Higher, lower | 0.5 each |
| Living environment | Heat-shelter rate and PM2.5 IDW | Lower, higher | 0.5 each |

Domains with multiple indicators use an equal-weight arithmetic mean. This is the transparent
open-data baseline; COD-18 tests proxy substitutions and weighting sensitivity.

## Holds and interpretation limits

- Safety remains unscored because no direct dong-level crime or accident measure is available;
  CCTV infrastructure is not substituted for incident risk.
- All income values are inferred from observed district totals.
- Employment represents workplace opportunity, not resident unemployment.
- Healthcare history is reconstructed from current licence registers.
- The old-housing measure is a lower bound affected by suppressed cells.
- Air pollution includes IDW smoothing and interpolation uncertainty.
- These experimental scores must not be treated as official deprivation findings or a statutory
  allocation formula.
