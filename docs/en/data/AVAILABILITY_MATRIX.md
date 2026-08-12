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
| Employment | SGIS establishments and workers | Proxy | C | Hold | Verify API years/coverage and obtain resident employment separately |
| Education | National school register | Proxy | B | Hold | Geocode, calculate service areas, and keep separate from outcomes |
| Health | Hospital, pharmacy, and AED locations | Proxy/context | B | Hold | Clean operating status, geocode, and obtain small-area outcomes |
| Safety | TAAS map | Validation | D | Validation only | Obtain reproducible raw data and verify derivative redistribution |
| Housing | Yeongdo and Suyeong vacancy | Direct | C | Exclude | One vacancy definition and date across Busan |
| Services | Bus-stop locations | Proxy | B | Hold | Retrieve source, join boundaries, and add frequency/walk-time evidence |
| Environment | Heat-shelter locations | Context | B | Hold | Spatial join plus hours and capacity checks |
| Environment | Air-monitoring network | Context | C | Hold | Join station coordinates and observations; disclose interpolation error |
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

The project fixes its geography at 206 Busan administrative dongs in SGIS 2025 and permits observations through 2026-07-31. Annual indicators prefer complete 2025 data; monthly, quarterly, and snapshot sources may extend through July 2026. When unavailable, the nearest earlier complete period is used with lag and partial-period status disclosed. See the [reference-period policy](REFERENCE_PERIOD_POLICY.md) and [administrative-dong boundary record](ADMIN_BOUNDARIES.md).

See [DATASET_AUDIT.csv](../../data/DATASET_AUDIT.csv) for row-level evidence.
