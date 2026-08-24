# 2025 B-IMD environmental-exposure overlay

## Decision

COD-21 overlays the 2025 B-IMD with annual PM2.5 and PM10 estimates for all 206 Busan
administrative dongs. **Four** of the 21 first-decile B-IMD areas are also in the top quarter
of particulate exposure. This is suitable for exploratory ambient-air double-burden
screening. It does not show that ports or industrial complexes caused the exposure.

## Execution and review

Run only COD-21 from the repository root with:

```bash
docker compose run --rm jupyter python -m busan_imd.environmental_overlay
```

- `data/processed/scores/2025/busan_admin_dong_environmental_overlay_2025.csv`: B-IMD,
  pollutant percentiles and ranks, and overlap flags for 206 dongs
- [`notebooks/03_environmental_overlay_review.ipynb`](../../../notebooks/03_environmental_overlay_review.ipynb):
  interactive scatter plot, administrative-dong map, and double-burden list
- [ENVIRONMENTAL_OVERLAY_REPORT_2025.json](../../data/manifests/ENVIRONMENTAL_OVERLAY_REPORT_2025.json):
  rules, summary statistics, selected areas, checksums, and interpretation limits

With Jupyter running, open
`http://localhost:8888/lab/tree/notebooks/03_environmental_overlay_review.ipynb` and select
`Run All Cells`. The notebook locates the project root automatically and does not overwrite
the tracked report.

## Method

The exposure inputs are annual PM2.5 and PM10 values interpolated from the four nearest HEIS
monitoring stations using IDW. Each pollutant is converted to a percentile rank among all 206
dongs, and their arithmetic mean is the `particulate_exposure_score_0_100`. The highest 52
dongs—the ceiling of 25% of 206—are flagged as high exposure. Administrative-dong code breaks
ties deterministically.

An area is double burden only when it is both:

1. in B-IMD decile 1; and
2. in the top quarter of the particulate exposure score.

The threshold is an exploratory screening rule, not a final policy-eligibility cutoff. IDW
values are estimates rather than direct measurements in each dong and reflect monitor siting
and spatial smoothing.

## 2025 result

| Category | Dongs |
|---|---:|
| Double burden | 4 |
| B-IMD priority only | 17 |
| High exposure only | 48 |
| Neither | 137 |

The screened double-burden areas are Mora 3-dong (Sasang-gu), Sujeong 4-dong and Sujeong
1-dong (Dong-gu), and Garak-dong (Gangseo-gu). Spearman correlation between B-IMD and the
particulate score is weakly negative (`-0.126191`). Mean exposure is also lower among priority
areas (`42.810911`) than elsewhere (`51.086329`). The result therefore does not support a
citywide claim that greater social vulnerability consistently coincides with greater
particulate exposure. The four overlaps remain candidates for finer environmental and field
review.

## Port and industrial-complex limitation

The current data catalog and raw bundle contain no versioned port or industrial-complex
geometry with a reproducible reference year and provenance. COD-21 therefore does not compute
site distance, boundary overlap, or source emissions, and it does not attribute particulate
exposure to either source type. Extension requires:

- versioned 2025 port and industrial-complex boundaries, CRS, and use terms;
- source locations and emissions for the same reference period; and
- wind/dispersion evidence or another validated exposure model.

Once available, those variables should be joined to the canonical 206-dong geography and
validated separately from the ambient-air screen reported here.
