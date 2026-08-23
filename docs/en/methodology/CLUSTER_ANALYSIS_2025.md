# 2025 B-IMD deprivation-type clustering review

## Purpose and decision

COD-20 tests whether the 21 first-decile B-IMD priority areas form stable, interpretable
deprivation types. The clusters produced from the current open-data indicators are unstable
under changes in initialization, so they are **not used as a policy typology**. The assignment
CSV is an exploratory diagnostic artifact, not a policy classification.

## Execution and outputs

Rebuild the full pipeline with:

```bash
docker compose run --rm jupyter python scripts/rebuild_processed.py
```

Run only COD-20 with:

```bash
docker compose run --rm jupyter python -m busan_imd.cluster_analysis
```

- `data/processed/scores/2025/busan_admin_dong_deprivation_clusters_2025.csv`: exploratory
  assignments and domain excess contributions
- `data/processed/scores/2025/busan_admin_dong_cluster_metrics_2025.csv`: quality and stability
  metrics for `k=2..6`
- [CLUSTER_ANALYSIS_REPORT_2025.json](../../data/manifests/CLUSTER_ANALYSIS_REPORT_2025.json):
  checksums, selection rule, quality gate, and final decision

## Method

The model standardizes the six weighted domain excess contributions above the Busan median
produced by COD-19, then fits K-means for `k=2..6`. A candidate must meet all three gates:

- silhouette score of at least `0.25`;
- mean adjusted Rand index (ARI) of at least `0.80` over 20 initialization seeds; and
- at least three administrative dongs in every cluster.

The selected candidate has the highest silhouette among candidates satisfying the minimum
size, with stability and then fewer clusters breaking ties. Policy use is recommended only
when the selected candidate passes every gate. Arbitrary model labels are deterministically
renumbered by their dominant mean domain excess contributions.

## 2025 result

| k | Silhouette | Mean stability ARI | Minimum ARI | Min size | Max size | Gate |
|---:|---:|---:|---:|---:|---:|---|
| 2 | 0.280819 | 0.371521 | -0.061798 | 5 | 16 | Fail |
| 3 | 0.231277 | 0.559224 | 0.162152 | 5 | 9 | Fail |
| 4 | 0.256291 | 0.628769 | 0.412123 | 3 | 8 | Fail |
| 5 | 0.230808 | 0.518872 | 0.135802 | 2 | 8 | Fail |
| 6 | 0.219943 | 0.466686 | 0.237131 | 1 | 7 | Fail |

The selection rule chooses `k=2`. Its silhouette and minimum size pass, but its mean stability
ARI of `0.371521` is far below `0.80`. The relatively stronger `k=4` alternative also fails
the stability gate. The 16- and five-member exploratory split is therefore not named or used
as a fixed deprivation typology.

## Interpretation and next step

The nine current indicators are strongly influenced by income and employment proxies, and the
priority-area population contains only 21 observations. Connecting unstable membership to
policy labels would overinterpret an accidental partition. COD-22 should build its policy
priority matrix directly from COD-19's continuous area contributions and leading drivers,
rather than cluster IDs. Repeat this gate when direct resident employment and income data
become available.
