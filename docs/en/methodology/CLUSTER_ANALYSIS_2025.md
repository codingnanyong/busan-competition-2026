# 2025 administrative-dong cluster-analysis review

## Decision

COD-20 **does not adopt a policy typology**. None of the K-means candidates from `k=2` to
`k=6`, evaluated on six standardized domain scores for 206 Busan administrative dongs,
passed every documented separation and resampling-stability gate. No dong receives a cluster
label and later policy work must not treat the candidate profiles as validated types.

This is a quality decision rather than a failed deliverable. Later policy and visualization
work will use the continuous domain and indicator contributions from the
[priority-area analysis](PRIORITY_AREAS_2025.md).

## Reproduction and outputs

Rebuild the full pipeline with:

```bash
docker compose run --rm jupyter python scripts/rebuild_processed.py
```

Run only COD-20 with:

```bash
docker compose run --rm jupyter python -m busan_imd.cluster_analysis
```

The stage writes candidate-quality diagnostics, audit-only centroid profiles, an empty
assignment table, and the tracked
[CLUSTER_ANALYSIS_REPORT_2025.json](../../data/manifests/CLUSTER_ANALYSIS_REPORT_2025.json).
Processed CSVs remain excluded from Git and are regenerated from the restored data bundle.

## Evaluation design

The six domain scores are standardized to mean zero and unit variance. K-means uses random
state `2025` and `n_init=50`. Each candidate is assessed using silhouette,
Davies–Bouldin, Calinski–Harabasz, minimum cluster size, and 100 bootstrap resamples. Each
bootstrap model predicts all original dongs and is compared with the reference labels using
Adjusted Rand Index (ARI). Every cluster must also have at least one centroid dimension with
an absolute standardized value of `0.5` or greater.

The project-specific adoption gates are silhouette ≥ `0.25`, median bootstrap ARI ≥ `0.70`,
10th-percentile bootstrap ARI ≥ `0.50`, minimum size ≥ `10`, and a 100% distinctive-cluster
rate. These are conservative governance thresholds for this policy use case, not universal
statistical rules.

## Results

The strongest candidate is `k=2`, with silhouette `0.199017`, median bootstrap ARI `0.679481`,
and 10th-percentile ARI `0.513805`. It passes the size and lower-tail stability gates but fails
both the separation and median-stability gates. Every other candidate has lower silhouette and
also fails stability. The evidence therefore supports a continuous deprivation gradient more
strongly than a small set of stable, discrete types.

K-means assumes Euclidean, roughly spherical clusters and does not directly model spatial
adjacency. Proxy limitations in the income, employment, and other domain scores also propagate
into this review. If direct administrative data are added, rerun the same gates and do not
interpret any new labels as directly comparable with these rejected candidates.
