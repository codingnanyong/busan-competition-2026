# Data Catalog

This document manages candidate sources for the Busan Index of Multiple Deprivation (B-IMD). [DATASET_AUDIT.csv](../../data/tables/DATASET_AUDIT.csv) is the row-level COD-10 register; this page explains the decisions and usage rules.

## COD-10 audit result

- Audit date: 2026-08-11
- Registered candidates: 40
- Current decisions: 11 `include`, 13 `validation-only`, 6 `hold`, and 10 `exclude`
- Conclusion: six domains, including a disclosed inferred income proxy, now have provisional
  206-dong indicators. The safety domain remains outside the base score because complete
  administrative-dong incident data is unavailable.

The Busan administrative-area page labels its table as 205 units while the district row counts sum to 206. COD-11's single SGIS 2025 response contains 206 codes and 206 matching boundaries, so the project fixes its reference geography at 206 units. See [administrative-dong codes and boundaries](ADMIN_BOUNDARIES.md).

The primary analysis year is 2025. Complete 2025 data or a 2025-12-31 snapshot drives the primary score; January-July 2026 data is retained only for validation. If 2025 is unavailable, the nearest earlier complete year is used with its lag recorded. Publication, observation, and retrieval dates remain separate. See the [reference-period policy](REFERENCE_PERIOD_POLICY.md).

## Domain decisions

| Domain | Representative sources checked | Grade | Decision | Main reason |
|---|---|---:|---|---|
| Income | Basic-livelihood-recipient CSVs from five districts | C | Exclude | Reference dates span 2024–2026, definitions differ, and only five districts are covered |
| Employment | SGIS 2024 establishment and worker API | C | Provisional include | All 206 dongs joined; workplace employment is an opportunity proxy, not resident employment |
| Education | KERIS NEIS school register | B | Provisional include | 655 of 662 eligible schools geocoded; core-school access calculated for 206 dongs |
| Health | MOIS hospital/clinic/pharmacy APIs | B | Provisional include | Valid-coordinate 2025 candidates joined as facility-access proxies; AED remains validation only |
| Safety | KOROAD traffic and NFA fire APIs | C | Validation only | District crash context and daily fire-station summaries are reproducible but are not complete dong-level incident censuses |
| Housing/access | Yeongdo/Suyeong vacancy and 2025 Busan bus stops | B–C | Provisional include/exclude | 7,940 dated stops joined; vacancy remains partial and inconsistent |
| Living environment | Heat shelters and HEIS 2025 air quality | B | Provisional include | Heat shelters joined and air exposure interpolated to all 206 dongs |

The absence of an A-grade source is an audit finding. The `include` decisions are provisional
proxies rather than direct deprivation measures. Filling uncovered districts with zero or
repeating district values across their dongs would create false comparability and is prohibited.

## Raw-file findings

| Source | Finding |
|---|---|
| Basic livelihood | Geumjeong 16, Buk 13, Suyeong 10, Dong 12, and Nam 17 dongs. Periods and columns differ, so the files are excluded from index input |
| Vacancy | All 11 Yeongdo and 10 Suyeong dongs are present within each file, but condition definitions differ |
| Heat shelters | 1,789 rows and 0% coordinate missingness; opening hours, capacity, and cooling performance are absent |
| Air monitoring network | 37 rows and 34 unique station names; this file does not provide coordinates |
| Sasang flood traces | Nine rows; the source states that pre-2024 records are unavailable |
| SGIS establishments | 2024, all 206 Busan dongs, no duplicate code or missing count cells |
| Bus-stop API | The undated 8,790-record live response is held; the 8,522-record 2025-01-21 shapefile is the reference inventory |
| 2025 bus route usage | 333 unique routes and 444,461,191 card transactions; demand validation only, not actual service frequency |
| Haeundae basic-livelihood recipients | Eighteen administrative-dong rows plus one facility total at 2025-08-20; partial-coverage income validation only |
| AED API | All 1,079 records collected; held because the inventory date is absent |
| Real-time air API | 1,184 observations from 2026-08-11–12; excluded beyond the 2026-07-31 cutoff |
| School register | All 667 schools collected; 655 of 662 cutoff-eligible rows geocoded and 616 core schools used for access |
| Hospitals and pharmacies | Current API responses contain 641 and 4,336 rows; licence dates reconstruct 406 and 1,731 operating candidates at 2025-12-31, with 29 and 19 missing coordinates |
| KOROAD crashes | 202 rows of 2025 district statistics and 48 selected 2024 hotspots across all 16 Busan districts; validation only |

Raw files remain in the Git-ignored `data/raw/audit/` directory. Recheck catalog structure and local SHA-256 values with:

```powershell
$env:PYTHONPATH = "src"
python -m busan_imd.processing.data_catalog docs/data/tables/DATASET_AUDIT.csv --raw-dir data/raw/audit
```

## Missing-value states

- `0`: the publisher observed zero events for that unit and period
- `missing`: a collected cell is blank or cannot be parsed
- `uncollected`: a public source has not yet been retrieved
- `private/unavailable`: no reproducible source is available
- `not_applicable`: the indicator definition does not apply

These states are never substituted for one another, especially not with zero.

## Spatial mapping rules

1. Use a same-period administrative-code register.
2. Resolve name variants such as `제1동` and `1동` through an explicit district-aware crosswalk.
3. Convert legal dongs only with a verified crosswalk, documenting one-to-many weights.
4. Join coordinates by point-in-polygon after recording CRS and boundary date.
5. Map census tracts with area or population weights and publish mapping rates.
6. Never repeat district-level values across constituent dongs.

## Access information still needed

- SGIS and Public Data Portal credentials are now configured in the local `.env`.
- Institutional contact routes and source-specific redistribution terms for observations through July 2026 still require confirmation.

Secrets belong only in the local `.env`; they must not be pasted into chat or committed. Public-file auditing and institutional requests can continue without the keys.

## Related documents

- [Availability matrix](AVAILABILITY_MATRIX.md)
- [Reference-period policy](REFERENCE_PERIOD_POLICY.md)
- [Raw-data collection and provenance](RAW_DATA_COLLECTION.md)
- [2025 administrative-dong data standardization](STANDARDIZATION.md)
- [2025 candidate-indicator EDA](EDA_2025.md)
- [Data request roadmap](DATA_REQUEST_ROADMAP.md)
- [Indicator specification](../methodology/INDICATOR_SPEC.md)
- [Limitations](../methodology/LIMITATIONS.md)
