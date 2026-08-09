# Data Catalog

This is the single inventory of datasets considered for the Busan IMD (B-IMD). It tracks both the minimum open-data model and the direct measures that could replace proxies through future institutional cooperation.

## Recording rules

- Record provenance, reference period, geography, licence, and update cycle before inclusion.
- Distinguish `direct`, `proxy`, `context`, and `validation` measures.
- Document geocoding and spatial joins for sources that do not carry an administrative-dong code.
- Keep missing values distinct from observed zeroes.
- Preserve raw files and record collection timestamps and checksums.

## Catalog schema

| Field | Description |
|---|---|
| `dataset_id` | Repository-wide stable identifier |
| `domain` / `indicator_candidate` | Domain and candidate measure |
| `measure_type` | `direct`, `proxy`, `context`, or `validation` |
| `provider` / `source_url` | Publisher and authoritative URL |
| `reference_period` / `update_cycle` | Observation period and refresh schedule |
| `spatial_unit` | Census tract, administrative dong, legal dong, district, or coordinates |
| `format` / `access_method` | CSV, SHP, API, WMS, and authentication |
| `license` | Reuse and redistribution conditions |
| `coverage` / `missing_rate` | Busan coverage and missingness |
| `availability_grade` / `decision` | A–D and include/hold/exclude/validation-only |
| `fallback` | Substitute measure or domain exclusion rule |
| `collected_at` / `checksum` | Retrieval time and source integrity |

## Initial candidate register

COD-10 must verify URLs, periods, coverage, missingness, and licences before any row is finalized.

| Domain | Preferred candidate | Type | Initial assessment | COD-10 check |
|---|---|---|---|---|
| Income | Basic-livelihood-benefit recipient rate | Proxy | Partial | Consistent coverage for every Busan dong |
| Employment | Resident labour status or establishment/worker change | Direct/proxy | Partial | Availability of resident-based measures |
| Education | Low educational attainment or service access | Direct/proxy | Partial | Recent small-area attainment coverage |
| Health | Outcomes or vulnerable population and care access | Direct/proxy | Partial | Small-area outcomes and disclosure limits |
| Safety | Crime, accidents, fire, or safety infrastructure | Direct/proxy | Partial | Downloadable aggregates versus map-only access |
| Housing/access | Housing age, vacancy, transit, and essential services | Direct | Higher | Coordinate quality and spatial joins |
| Living environment | Flood, heat, air, green space, and slope exposure | Direct/modelled | Feasible | Resolution and interpolation uncertainty |

## Related documents

- [Availability matrix](AVAILABILITY_MATRIX.md)
- [Data request roadmap](DATA_REQUEST_ROADMAP.md)
- [Indicator specification](../methodology/INDICATOR_SPEC.md)
- [Limitations](../methodology/LIMITATIONS.md)
