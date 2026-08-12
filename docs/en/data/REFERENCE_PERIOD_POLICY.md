# Data reference-period policy

## Decision

- Analytical cutoff: **2026-07-31**
- Reference geography: **206 Busan administrative dongs in SGIS 2025**
- Rule: use the latest available data through the cutoff while disclosing period type and lag.

The competition analysis uses as much data as is available through July 2026. Part-year cumulative
values are not directly comparable with complete annual values, so every dong must use the same
observation window within an indicator.

## Indicator selection

1. Prefer the latest observation ending on or before 2026-07-31.
2. Prefer 2025, the latest complete year, for annual indicators.
3. Monthly, quarterly, and snapshot indicators may extend through July 2026.
4. Apply one start and end date to every dong within an indicator. Never mix January–July 2026
   cumulative counts with 2025 annual counts in one comparison.
5. If the latest period is unavailable, use the nearest earlier complete period and record the real
   `reference_period`, period type (`annual`, `partial_year`, or `snapshot`), and `lag_months` or
   `lag_years`.
6. Keep `published_at`, `reference_period`, and `retrieved_at` distinct.
7. Multi-year measures must use a fixed window ending by the cutoff and disclose the window.
8. Institutional requests should seek both calendar-year 2025 and January–July 2026 or a
   2026-07-31 snapshot where possible.

## Disclosure

Tables and maps disclose the geography year, observation period, and period type. Older and
part-year inputs carry lag or partial-period warnings, and sensitivity analysis tests their effect
on rankings. Retrieval date supports provenance; it never substitutes for the observation period.
