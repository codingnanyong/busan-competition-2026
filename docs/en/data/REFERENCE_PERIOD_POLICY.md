# Data reference-period policy

## Decision

- Primary analysis year: **2025**
- Collection cutoff: **2026-07-31**
- Reference geography: **206 Busan administrative dongs in SGIS 2025**
- Rule: use complete 2025 observations or a 2025-12-31 snapshot for the primary index.

January-July 2026 observations are retained only for validation and sensitivity analysis. They do
not fill missing 2025 values and are never mixed with annual 2025 values within an indicator.

## Indicator selection

1. Prefer observations covering calendar-year 2025 or a snapshot dated 2025-12-31.
2. Use the same observation window for every dong within an indicator.
3. Treat monthly, quarterly, and snapshot observations from 2026 as supplemental validation only.
4. Never mix January-July 2026 cumulative counts with 2025 annual counts in one comparison.
5. If 2025 is unavailable, use the nearest earlier complete period and record the real
   `reference_period`, period type (`annual`, `partial_year`, or `snapshot`), and `lag_months` or
   `lag_years`.
6. Keep `published_at`, `reference_period`, and `retrieved_at` distinct.
7. Multi-year measures must use a fixed window ending by 2025-12-31 and disclose the window.
8. Institutional requests must seek calendar-year 2025 first. January-July 2026 or a 2026-07-31
   snapshot may be requested separately for validation.

## Disclosure

Tables and maps disclose the geography year, observation period, analysis role, and period type.
Earlier fallback inputs carry a lag warning, while 2026 part-year inputs are labelled supplemental
and excluded from the primary score. Retrieval date supports provenance; it never substitutes for
the observation period.
