# 2025 B-IMD priority areas and contribution analysis

## Scope

COD-19 defines the 21 administrative dongs in B-IMD decile 1 as priority areas and
decomposes each composite score into domain- and indicator-level contributions. The analysis
is diagnostic: it explains which public-data proxies drive a high score rather than treating
the rank as a sufficient policy-allocation rule.

## Reproduction

Rebuild the complete pipeline with:

```bash
docker compose run --rm jupyter python scripts/rebuild_processed.py
```

Run only this stage with:

```bash
docker compose run --rm jupyter python -m busan_imd.priority_areas
```

The stage writes a 21-row priority-area profile, a 21-by-9 long-form indicator contribution
table, and the tracked
[PRIORITY_AREA_REPORT_2025.json](../../data/manifests/PRIORITY_AREA_REPORT_2025.json)
containing definitions, checksums, and summary results. Processed CSV outputs remain excluded
from Git and are regenerated from the restored data bundle.

## Method

For indicator `i` in domain `d`:

```text
indicator_contribution_i
  = deprivation_percentile_i × within_domain_weight_i × composite_domain_weight_d
```

The nine contributions for a dong reconcile to its published B-IMD score. To distinguish an
area-specific driver from the mechanical effect of larger domain weights, the leading driver
is the largest weighted contribution above the citywide median for that indicator or domain.
Name order resolves exact ties deterministically.

## Result and limitations

The three highest-ranked areas are Mora 3-dong in Sasang-gu (82.821838), Choryang 6-dong in
Dong-gu (80.255209), and Banyeo 3-dong in Haeundae-gu (79.701987). Among all 21 priority
areas, employment is the leading domain for 12 and income for nine.

These results do not directly observe resident unemployment or individual income. The income
measure is an inferred basic-livelihood-recipient proxy based partly on district totals, and
the employment measure uses workplace workers as a proxy for local opportunity. Contributions
are arithmetic score decompositions, not causal effects. Use them as signals for administrative
data validation and field review, together with the documented sensitivity analysis.

The subsequent [COD-20 clustering review](CLUSTER_ANALYSIS_2025.md) tested whether these
contribution vectors form stable deprivation types. They failed the initialization-stability
gate and are not used as a policy typology.
