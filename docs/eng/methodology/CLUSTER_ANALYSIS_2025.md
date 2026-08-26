# 2025 B-IMD deprivation-type clustering review

## Purpose and decision

COD-20 tests whether the 21 first-decile B-IMD priority areas form stable, interpretable
deprivation types. Repeated validation using the same multi-initialization K-means procedure
as production shows that `k=2` passes the quality gate. The two clusters may be **used as an
exploratory policy typology**, but not as an official classification or a replacement for
continuous area contributions.

## Execution and outputs

Rebuild the full pipeline with:

```bash
docker compose run --rm jupyter python scripts/rebuild_processed.py
```

Run only COD-20 with:

```bash
docker compose run --rm jupyter python -m busan_imd.analysis.cluster_analysis
```

- `data/processed/scores/2025/busan_admin_dong_deprivation_clusters_2025.csv`: exploratory
  assignments and domain excess contributions
- `data/processed/scores/2025/busan_admin_dong_cluster_metrics_2025.csv`: quality and stability
  metrics for `k=2..6`
- [`notebooks/02_deprivation_cluster_review.ipynb`](../../../notebooks/02_deprivation_cluster_review.ipynb):
  interactive quality-gate, PCA, cluster-profile, and area-assignment views
- [CLUSTER_ANALYSIS_REPORT_2025.json](../../data/manifests/CLUSTER_ANALYSIS_REPORT_2025.json):
  checksums, selection rule, quality gate, and final decision

## Method

The model standardizes the six weighted domain excess contributions above the Busan median
produced by COD-19, then fits K-means for `k=2..6`. A candidate must meet all three gates:

- silhouette score of at least `0.25`;
- mean adjusted Rand index (ARI) of at least `0.80` between the reference fit (`n_init=50`)
  and 20 repeated fits (each `n_init=20`); and
- at least three administrative dongs in every cluster.

The selected candidate has the highest silhouette among candidates satisfying the minimum
size, with stability and then fewer clusters breaking ties. Policy use is recommended only
when the selected candidate passes every gate. Arbitrary model labels are deterministically
renumbered by their dominant mean domain excess contributions.

## 2025 result

| k | Silhouette | Mean stability ARI | Minimum ARI | Min size | Max size | Gate |
|---:|---:|---:|---:|---:|---:|---|
| 2 | 0.280819 | 0.980282 | 0.802817 | 5 | 16 | Pass |
| 3 | 0.231277 | 0.991877 | 0.837545 | 5 | 9 | Fail |
| 4 | 0.256291 | 0.914807 | 0.625561 | 3 | 8 | Pass |
| 5 | 0.230808 | 0.705622 | 0.504021 | 2 | 8 | Fail |
| 6 | 0.219943 | 0.627300 | 0.343853 | 1 | 7 | Fail |

The selection rule chooses `k=2`. Its silhouette is `0.280819`, mean stability ARI is
`0.980282`, and minimum cluster size is five, so it passes all three gates. The `k=4`
alternative also passes, but has a lower silhouette of `0.256291`.

- `type_1 — education_living_environment` (five areas): relatively stronger education and
  living-environment excess contributions within the priority-area population
- `type_2 — employment_income` (16 areas): relatively stronger employment and income excess
  contributions within the priority-area population

These names describe standardized centroid differences among the 21 priority areas, not an
absolute deprivation cause. Interpret every assignment with its continuous COD-19 profile.

## Interpretation and next step

The nine current indicators are strongly influenced by income and employment proxies, and the
priority-area population contains only 21 observations. COD-22 may use the clusters as a
top-level branch, but must combine them with COD-19's continuous area contributions and leading
drivers. Repeat this gate when direct resident employment and income data become available or
the indicator set changes.
