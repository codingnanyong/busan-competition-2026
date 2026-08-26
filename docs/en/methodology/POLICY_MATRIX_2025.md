# 2025 policy-priority matrix by deprivation type

## Decision

COD-22 links the two exploratory deprivation types that passed the COD-20 quality gate with
the independent COD-21 environmental overlay. The result contains **five rows across two
types and four unique policy candidates**. Every row is a candidate for field validation,
not an automatic funding decision or individual eligibility rule.

| Type | Target | Priority | Candidate action | Difficulty | Evidence |
|---|---:|---:|---|---|---|
| Education/living-environment relative type | 5 dongs | 1 | After-school learning and school-access review | Medium | Education mean excess `3.975933` |
| Education/living-environment relative type | Garak-dong | Overlay | Focused particulate monitoring and sensitive-group protection | High | One COD-21 double-burden dong |
| Employment/income type | 16 dongs | 1 | Local job and training linkage | Medium | Employment mean excess `10.600065` |
| Employment/income type | 16 dongs | 2 | Benefit take-up review and integrated case management | Medium | Income mean excess `10.592493` |
| Employment/income type | Mora 3, Sujeong 4, Sujeong 1 | Overlay | Focused particulate monitoring and sensitive-group protection | High | Three COD-21 double-burden dongs |

The living-environment mean excess for the `education_living_environment` type is
`-0.252867`. Its name indicates a relative difference from the other priority-area type, not
worse-than-Busan-median evidence. The matrix therefore excludes a general living-environment
action from automatic recommendation.

## Execution and outputs

Run only COD-22 with:

```bash
docker compose run --rm jupyter python -m busan_imd.analysis.policy_matrix
```

- [POLICY_ACTION_CATALOG_2025.csv](../../data/tables/POLICY_ACTION_CATALOG_2025.csv): action names,
  implementation roles, partners, difficulty rationale, expected effects, monitoring, and
  evidence limits
- `data/processed/scores/2025/busan_admin_dong_policy_matrix_2025.csv`: executable matrix
  linking types, target dongs, and analysis values
- [`notebooks/04_policy_matrix_review.ipynb`](../../../notebooks/04_policy_matrix_review.ipynb):
  interactive evidence and target views
- [POLICY_MATRIX_REPORT_2025.json](../../data/manifests/POLICY_MATRIX_REPORT_2025.json):
  checksums, selection and exclusion rules, and interpretation guardrails

In Jupyter, open `http://localhost:8888/lab/tree/notebooks/04_policy_matrix_review.ipynb`
and select `Run All Cells`.

## Selection rule

1. Require the COD-20 report to recommend exploratory policy typology and require the
   assignment checksum to match that quality-gated report; otherwise stop.
2. Take each COD-20 type's dominant and secondary domains as candidates.
3. Create an action only when that domain's mean weighted excess over the Busan median is
   positive among the relevant priority areas.
4. Add an environmental-health action when a type contains COD-21 double-burden areas.
5. Join implementation roles, partners, difficulty, expected effect, and monitoring fields
   from the versioned policy catalog.
6. Keep every row at `candidate_for_field_validation` status. If no candidate qualifies,
   write a schema-correct zero-row matrix and report instead of inventing an action.

Medium difficulty requires new targeting, follow-up, or cross-service coordination. High
difficulty requires new measurement, capital work, or sustained multi-organization delivery.
Expected effects are directional hypotheses that require monitored implementation.

## Target areas

- Education/living-environment relative type: Garak, Yeongju 2, Songjeong, Goejeong 2, and
  Gupo 3
- Employment/income type: Mora 3, Choryang 6, Banyeo 3, Sujeong 4, Deokcheon 3, Gamcheon 2,
  Sujeong 5, Sujeong 1, Chojang, Banyeo 2, Sinseon, Nambumin 2, Dongsam 3, Seo 1,
  Goejeong 3, and Nambumin 1
- Focused environmental-health review: Garak, Mora 3, Sujeong 4, and Sujeong 1

## Interpretation limits

- Clusters are relative patterns among 21 areas and do not establish policy causality.
- Income and employment use inferred benefit and workplace-worker proxies; combine them with
  resident administrative records and field demand assessment before delivery.
- Expected effects do not claim a quantitative effect size.
- Never use area scores to determine an individual's eligibility.
- With no port or industrial-source dataset, the environmental action is limited to added
  measurement and sensitive-group protection.
