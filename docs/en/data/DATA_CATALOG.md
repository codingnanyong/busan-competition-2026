# Data Catalog

This document manages candidate sources for the Busan Index of Multiple Deprivation (B-IMD). [DATASET_AUDIT.csv](../../data/DATASET_AUDIT.csv) is the row-level COD-10 register; this page explains the decisions and usage rules.

## COD-10 audit result

- Audit date: 2026-08-11
- Registered candidates: 20
- Raw sources inspected: ten direct downloads and four authenticated APIs, including bytes, record counts, and SHA-256
- Current `include` decisions: 0
- Conclusion: public candidates exist, but they do not yet form a seven-domain set that compares every Busan administrative dong at one reference period and geography.

The Busan administrative-area page labels its table as 205 units while the district row counts sum to 206. COD-11's single SGIS 2025 response contains 206 codes and 206 matching boundaries, so the project fixes its reference geography at 206 units. See [administrative-dong codes and boundaries](ADMIN_BOUNDARIES.md).

The analytical cutoff is 2026-07-31. Annual indicators prefer complete 2025 data, while monthly, quarterly, and snapshot sources may extend through July 2026. Part-year cumulative and annual values are never mixed within an indicator, and publication, observation, and retrieval dates remain separate. See the [reference-period policy](REFERENCE_PERIOD_POLICY.md).

## Domain decisions

| Domain | Representative sources checked | Grade | Decision | Main reason |
|---|---|---:|---|---|
| Income | Basic-livelihood-recipient CSVs from five districts | C | Exclude | Reference dates span 2024–2026, definitions differ, and only five districts are covered |
| Employment | SGIS 2024 establishment and worker API | C | Hold | All 206 dongs are present, but workplace employment is not resident employment |
| Education | KERIS school register | B | Hold | Supports access measures, not adult attainment or outcomes |
| Health | LOCALDATA hospitals/pharmacies and AED API | B | Hold | 1,079 AED records are collected but undated; facility access is not a health outcome |
| Safety | TAAS web GIS | D | Validation only | A reproducible extract and derivative redistribution terms were not verified |
| Housing/access | Yeongdo/Suyeong vacancy and Busan bus stops | B–C | Hold/exclude | 8,790 stops need date verification and a spatial join; vacancy remains partial and inconsistent |
| Living environment | Heat shelters, air stations, real-time air, and Sasang flood traces | B–C | Hold/exclude/validation only | The real-time response is outside cutoff; other sources need joins, interpolation, or broader coverage |

The absence of an A-grade source is an audit finding. Filling uncovered districts with zero or repeating district values across their dongs would create false comparability and is prohibited.

## Raw-file findings

| Source | Finding |
|---|---|
| Basic livelihood | Geumjeong 16, Buk 13, Suyeong 10, Dong 12, and Nam 17 dongs. Periods and columns differ, so the files are excluded from index input |
| Vacancy | All 11 Yeongdo and 10 Suyeong dongs are present within each file, but condition definitions differ |
| Heat shelters | 1,789 rows and 0% coordinate missingness; opening hours, capacity, and cooling performance are absent |
| Air monitoring network | 37 rows and 34 unique station names; this file does not provide coordinates |
| Sasang flood traces | Nine rows; the source states that pre-2024 records are unavailable |
| SGIS establishments | 2024, all 206 Busan dongs, no duplicate code or missing count cells |
| Bus-stop API | All 8,790 records collected; held because the inventory date is absent |
| AED API | All 1,079 records collected; held because the inventory date is absent |
| Real-time air API | 1,184 observations from 2026-08-11–12; excluded beyond the 2026-07-31 cutoff |

Raw files remain in the Git-ignored `data/raw/audit/` directory. Recheck catalog structure and local SHA-256 values with:

```powershell
$env:PYTHONPATH = "src"
python -m busan_imd.data_catalog docs/data/DATASET_AUDIT.csv --raw-dir data/raw/audit
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
- [Data request roadmap](DATA_REQUEST_ROADMAP.md)
- [Indicator specification](../methodology/INDICATOR_SPEC.md)
- [Limitations](../methodology/LIMITATIONS.md)
