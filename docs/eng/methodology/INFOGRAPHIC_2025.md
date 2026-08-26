# 2025 B-IMD one-page map and infographic draft

## Fit to purpose

The project measures relative living-condition vulnerability across Busan administrative
dongs, explains its drivers, and proposes place-based policy priorities. The COD-23 draft
communicates that chain on one page:

1. **Where vulnerability is concentrated:** a 206-dong B-IMD map and 21 first-decile areas.
2. **What is vulnerable in each dong:** six domain scores and the first two domains for all 206.
3. **What should be improved:** a review direction tied directly to the leading domain.
4. **Which areas appear first:** the top ten areas and two exploratory types.
5. **Where interpretation stops:** explicit proxy, sensitivity, causality, and individual-use
   warnings.

It therefore fits the current purpose of **screening places, explaining patterns, and linking
field-validation candidates** from public data. It does not fit the different purposes of
establishing an official index, deciding individual eligibility, or proving policy effects.
The submission should call it a public-data baseline for Busan vulnerability diagnosis and
make administrative-data and field-validation expansion part of the proposal's value.

Specialization is not inferred merely from low deprivation. The outputs identify a relative
low-deprivation domain as a preservation/linkage candidate, but a specialization strategy
requires additional local asset data on industry, commerce, tourism, and living infrastructure.

## Outputs

- [`busan_imd_one_page_2025.pdf`](../../../outputs/infographic/2025/static/busan_imd_one_page_2025.pdf):
  one-page competition PDF draft
- [`busan_imd_one_page_2025.svg`](../../../outputs/infographic/2025/static/busan_imd_one_page_2025.svg):
  editable vector source
- [`busan_imd_one_page_2025.png`](../../../outputs/infographic/2025/static/busan_imd_one_page_2025.png):
  quick-review preview
- [`busan_admin_dong_action_map_2025.html`](../../../outputs/infographic/2025/interactive/busan_admin_dong_action_map_2025.html):
  standalone 206-dong dashboard with a collapsible tree for four major categories, ten child
  categories, nineteen indicators, and policy examples. Sibling `css/` (layout, overlays,
  evidence, policy) and `js/` (data, map, evidence, policy, boot) files load by relative
  path; the page opens in a browser with no JavaScript server. Edit `html/`, `css/`, and
  `js/` in this output folder. Only `js/data.js` is regenerated.
- [`busan_admin_dong_action_profile_2025.csv`](../../../outputs/infographic/2025/tables/busan_admin_dong_action_profile_2025.csv):
  six scores, vulnerability order, improvement direction, and relative low-deprivation domain
- [INFOGRAPHIC_REPORT_2025.json](../../data/manifests/INFOGRAPHIC_REPORT_2025.json):
  input/output checksums, page count, displayed statistics, and artifact status

The PNG is a screen preview; page-count and submission-format checks use the PDF.
The HTML opens directly in a browser with its sibling CSS and JS files and has no external
map or JavaScript-server dependency. Edit the files under
`outputs/infographic/2025/interactive/`.
Selecting a major tree node maps its weighted child-category composite. Selecting a child node
switches the map to that category's score distribution. Selecting a dong then shows indicators,
deprivation percentiles, weights, estimation reasons, and confidence in the right-hand evidence
panel. Selecting a child category also opens a full-width policy panel below the map. The panel
recommends that category's intervention only when the selected dong scores 70 or above; below
the gate it shows monitoring or relative low-deprivation instead of the same package for every
dong. Each candidate card also gives this dong's threshold evidence, a priority population,
implementation sequence, outcome measures, an official reference case, and a caution against
copying the case without local validation.
The contract and Myeongji regression check are documented in the
[2025 category assessment](CATEGORY_ASSESSMENT_2025.md).

## Rebuild

Use the Docker image with pinned Matplotlib and Noto CJK fonts:

```bash
docker compose build jupyter
docker compose run --rm jupyter python -m busan_imd.infographic
```

The full processed-data rebuild also renders the infographic as its final step.

```bash
docker compose run --rm jupyter python scripts/rebuild_processed.py
```

## Headline results included

- Geography: 206 SGIS 2025 Busan administrative dongs
- Priority population: 21 B-IMD first-decile dongs
- Top three: Mora 3, Choryang 6, and Banyeo 3
- Exploratory types: five education-relative and 16 employment/income areas
- Particulate-independent double burden: Garak, Mora 3, Sujeong 4, and Sujeong 1
- Equal-weight sensitivity: 18 of the top 21 remain
- Main uncertainty: inferred income and workplace-worker rather than resident-employment proxies

## Design and next revision

The map uses a continuous B-IMD scale, bold outlines for first-decile areas, and teal points
for COD-21 double burden. Policy cards include only candidates passing COD-22's positive-excess
gate. The footer always displays experimental status and prohibited interpretations.

This is a `submission_draft`. The report and data-package draft in the
[2025 submission draft](SUBMISSION_DRAFT_2025.md) uses the same terms. The final
submission check must reconfirm naming, source-note size, exactly one PDF page, and print
legibility.
