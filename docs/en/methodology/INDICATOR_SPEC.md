# B-IMD Indicator Specification

B-IMD is an experimental composite for exploring relative living-condition deprivation across Busan administrative dongs. It is not an official statistic, an individual assessment, or a statutory funding formula.

Each indicator records its domain, concept, formula and unit, direct/proxy status, direction, period and geography, transformations, quality and missingness, normalization, within-domain weight, provenance, licence, and inclusion decision.

| Domain | Construct | Open-data example | Future direct measure |
|---|---|---|---|
| Income | Lack of essential resources | Benefit-recipient rate | Income bands and housing-cost burden |
| Employment | Involuntary labour-market exclusion | Establishment/worker change | Resident unemployment and underemployment |
| Education | Lack of skills and opportunity | Attainment or service access | Adult attainment, dropout, outcomes |
| Health | Constraints on healthy life and care | Vulnerability and care access | Standardized disease, mortality, unmet care |
| Safety | Exposure to crime, accidents, and hazards | Incidents and safety infrastructure | Crime victimization aggregates |
| Housing/access | Inadequate housing and essential access | Age, vacancy, transit, facility access | Minimum standard and cost burden |
| Environment | Harmful external exposure | Flood, heat, air, green space, slope | High-resolution longitudinal exposure |

Only indicators passing COD-10 are included. Weights are not fixed before the audit. UK-style, equal, and Busan-context alternatives are compared through sensitivity analysis. A domain that fails minimum evidence requirements is held rather than filled with an arbitrary substitute. Every release provides scores, ranks, deciles, domain contributions, and data-confidence information.

## 2025 open-data domain-score implementation

The COD-16 baseline normalizes included indicators to average-rank 0-100 percentiles and aligns
every direction so that higher means more deprived. Indicators receive equal weight within each
domain. Safety remains held without direct incident evidence. COD-17 handles cross-domain
aggregation and COD-18 tests proxy and weight sensitivity. See the
[2025 domain-score method](DOMAIN_SCORES_2025.md) for the executable contract and interpretation
limits.
The baseline cross-domain weights, composite, rank, and decile are documented in the
[2025 B-IMD composite method](COMPOSITE_INDEX_2025.md).
