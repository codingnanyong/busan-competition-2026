# Data Availability Matrix

This document determines whether candidate measures can compare every Busan administrative dong. Initial ratings remain provisional until COD-10 verifies authoritative data.

## Grades

| Grade | Standard | Scoring rule |
|---|---|---|
| A | Same-period direct dong statistics with full coverage and verified reuse | Prefer for inclusion |
| B | Coordinates, census tracts, or legal-dong data can be reproducibly aggregated | Include with transformation error documented |
| C | Old, partial, proxy, or geographically incomplete | Hold or sensitivity analysis only |
| D | Closed, view-only, incompatible, or non-redistributable | Exclude from the composite |

## Initial assessment

| Domain | Open-data candidate | Expected grade | Main gap | Current-model rule |
|---|---|---:|---|---|
| Income | Benefit-recipient rate | B–C | Consistent dong and period coverage | Exclude without Busan-wide coverage |
| Employment | Establishment and worker change | B | Resident unemployment | Do not label as resident employment deprivation |
| Education | Attainment or education access | B–C | Recent small-area attainment | Separate access from outcomes |
| Health | Vulnerability and care access | B–C | Disease and mortality outcomes | Separate facilities from health status |
| Safety | Accidents, fire, hazards, infrastructure | B–C | Actual crime aggregates | Do not present proxies as crime rates |
| Housing/access | Age, vacancy, transit, essential services | A–B | Inconsistent vacancy definitions | Combine only common definitions |
| Environment | Flood, heat, air, green space, slope | B | Resolution and interpolation | Separate observations from modelled exposure |

## Inclusion gates

A core indicator must have consistent Busan-wide geography, a documented numerator and denominator, distinguish zero from missingness, provide reproducible spatial conversion, disclose missingness, and permit the intended reuse. Otherwise it is held, validation-only, or excluded. Missing values are never silently replaced with zero.

One reference year and administrative-code version are fixed before scoring. District values are not copied into every constituent dong, and boundary conversions are documented.
