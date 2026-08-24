# 2025 administrative-dong category assessment and policy gate

## Purpose

This assessment does not replace the baseline B-IMD. It transparently connects category
indicators to conditional policy examples. Estimated, proxy, and interpolated inputs remain
usable, but their evidence type, row-level confidence, and policy limitation are retained.

## Improvements

- Split housing from transit and air exposure from heat response, producing eight categories.
- Stabilize small-area facility rates toward the Busan-wide rate using a 5,000-person prior.
- Record `evidence_type`, `confidence_level`, and `quality_note` for every indicator.
- Treat a Busan-relative percentile of 70 or more as a validation candidate, not a decision.
- Keep the baseline B-IMD rank for comparison only; do not combine it with improved scores.

The versioned indicator contract is
[CATEGORY_ASSESSMENT_SPEC_2025.csv](../../data/CATEGORY_ASSESSMENT_SPEC_2025.csv), and conditional
examples are in [CATEGORY_POLICY_CATALOG_2025.csv](../../data/CATEGORY_POLICY_CATALOG_2025.csv).

## Myeongji regression check

The old education score used only centroid-to-school distance and gave Myeongji 1 and 2 scores
of 84.9 and 90.7. Combining distance with within-dong and two-kilometre school supply lowers
the improved scores to 51.9 and 58.6. Neither crosses the policy-review threshold of 70, while
the centroid-distance limitation remains visible as `medium_low` confidence.

## Run

```bash
docker compose run --rm jupyter python -m busan_imd.category_assessment
docker compose run --rm jupyter python -m busan_imd.infographic
```

The outputs contain 206×8 category assessments, 206×13 indicator evidence rows, and a manifest
with reproducibility checksums. They support screening only; observed administrative data,
travel time, capacity, and field demand must validate final policy choices.
