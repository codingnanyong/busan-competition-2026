# Data Availability Matrix

## Grades

| Grade | Test | Index rule |
|---|---|---|
| A | Same-period administrative-dong direct statistic, full Busan coverage, reuse verified | Prefer inclusion |
| B | Coordinates, census tracts, or legal dongs can be mapped reproducibly | May include with transformation error disclosed |
| C | Old, partial, proxy, or spatially incomplete | Sensitivity analysis or hold |
| D | Private, view-only, non-redistributable, or definition mismatch | Exclude from composite |

## Audit decisions at 2026-08-11

| Domain | Best public candidate | Type | Grade | Decision | Condition to pass |
|---|---|---|---:|---|---|
| Income | Basic-livelihood recipients in five districts | Proxy | C | Exclude | 100% of 16 districts with one date and benefit definition |
| Employment | SGIS 2024 establishments and workers | Proxy | C | Hold | All 206 dongs collected; obtain resident employment separately |
| Education | 667 Busan school records | Proxy | B | Hold | Geocode the 662 schools eligible at 2025-12-31, calculate service areas, and keep separate from outcomes |
| Health | Reconstructed 2025 hospital/pharmacy candidates and AED locations | Proxy/context | B | Hold | Validate historical completeness and coordinates, obtain an AED archive, and obtain small-area outcomes |
| Safety | KOROAD crash context and 2025 NFA daily fire-station summaries | Validation | C | Validation only | Obtain complete administrative-dong crash and fire counts and verify derivative redistribution |
| Housing | Yeongdo and Suyeong vacancy | Direct | C | Exclude | One vacancy definition and date across Busan |
| Services | Bus-stop locations | Proxy | B | Hold | Verify date for 8,790 records, join boundaries, and add frequency/walk-time evidence |
| Environment | Heat-shelter locations | Context | B | Hold | Spatial join plus hours and capacity checks |
| Environment | HEIS daily air quality | Context | C | Hold | Use 2025 as the primary period; use 2026 January-July only for validation, and disclose interpolation error |
| Environment | Sasang flood traces | Validation | C | Validation only | Same-period citywide geospatial records |

## Inclusion gate

A candidate enters the base composite only if it:

1. compares every Busan dong under one geography and definition;
2. documents numerator, denominator, direction, and period;
3. distinguishes observed zero, missing, uncollected, private, and not applicable;
4. has a reproducible code or spatial mapping path;
5. publishes mapping rate, unmatched count, and missingness; and
6. permits both source use and publication of analytical derivatives.
7. ends on or before 2026-07-31 and uses the same observation window for every dong.

Failure leads to `hold`, `validation-only`, or `exclude`. District values must never be repeated across dongs, and missing values must never be changed to zero to pass the gate.

## Reference year and data cutoff

The project fixes its geography at 206 Busan administrative dongs in SGIS 2025. The primary index uses complete 2025 observations or a 2025-12-31 snapshot. January-July 2026 observations are supplemental validation data, despite falling within the 2026-07-31 collection cutoff. When 2025 is unavailable, the nearest earlier complete period is used with its lag disclosed. See the [reference-period policy](REFERENCE_PERIOD_POLICY.md) and [administrative-dong boundary record](ADMIN_BOUNDARIES.md).

See [DATASET_AUDIT.csv](../../data/DATASET_AUDIT.csv) for row-level evidence.
