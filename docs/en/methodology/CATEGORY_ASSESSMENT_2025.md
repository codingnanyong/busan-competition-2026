# 2025 administrative-dong category assessment and policy gate

## Purpose

This assessment does not replace the baseline B-IMD. It transparently connects category
indicators to conditional policy examples. Estimated, proxy, and interpolated inputs remain
usable, but their evidence type, row-level confidence, and policy limitation are retained.

## Improvements

- Place eight child categories under three major categories.
- Stabilize small-area facility rates toward the Busan-wide rate using a 5,000-person prior.
- Record `estimate_used`, estimation method and reason, `confidence_level`, and
  `quality_note` for every indicator.
- Treat a Busan-relative percentile of 70 or more as a validation candidate, not a decision.
- Keep the baseline B-IMD rank for comparison only; do not combine it with improved scores.

The versioned indicator contract is
[CATEGORY_ASSESSMENT_SPEC_2025.csv](../../data/CATEGORY_ASSESSMENT_SPEC_2025.csv), and conditional
examples are in [CATEGORY_POLICY_CATALOG_2025.csv](../../data/CATEGORY_POLICY_CATALOG_2025.csv).

## Three-level structure

The calculation follows `major category → child category → indicator`:

- Socioeconomic base: income/support need and local employment opportunity, each weighted 0.50.
- Living infrastructure and housing: education, healthcare, housing, and transit, each weighted 0.25.
- Environment and climate response: air exposure and heat response, each weighted 0.50.

The major-category score applies the stated contribution share to each child-category
vulnerability score and then adds the results. It is not an unweighted average.

The major-category map therefore visualizes the combined child-category result, rather than any
single indicator. The dashboard expands a selected dong from the major score into child scores
and then the underlying indicators.

## Estimation disclosure

Nine of the fourteen indicators use estimation, reconstruction, interpolation, or small-area
shrinkage. The dashboard marks each one as `estimated value used` and displays both the method
and why it was necessary. The reasons distinguish unavailable dong-level income observations,
small population denominators, reconstructed operating-facility inventories, the absence of an
air monitor in every dong, and mixed reference dates. The other five indicators are marked as
not using missing-value estimation, while their proxy or lower-bound limitations remain visible.

## Reading the policy direction

Each policy card follows `detected signal → priority population → implementation sequence →
outcome measures → official reference case → adaptation caution`. Reference cases illustrate
implementable instruments; they do not mean that the same intervention has already been selected
for the dong. Field evidence must still determine whether to adapt, pilot, or reject an instrument.

## Myeongji regression check

The old education score used only centroid-to-school distance and gave Myeongji 1 and 2 scores
of 84.9 and 90.7. Combining distance with within-dong supply, two-kilometre school supply, and
2025 active-teacher disclosures gives improved scores of 58.1 and 67.9. Neither crosses the
policy-review threshold of 70, although Myeongji 2 is close because its two-kilometre supply is
low relative to denser Busan dongs. The centroid-radius limitation remains visible as
`medium_low` confidence.

## Run

```bash
docker compose run --rm jupyter python -m busan_imd.category_assessment
docker compose run --rm jupyter python -m busan_imd.infographic
```

The outputs contain 206×3 major-category assessments, 206×8 child-category assessments,
206×14 indicator evidence rows, and a manifest with reproducibility checksums. They support
screening only; observed administrative data, travel time, capacity, and field demand must
validate final policy choices.
