# 2025 B-IMD one-page map and infographic draft

## Fit to purpose

The project measures relative living-condition vulnerability across Busan administrative
dongs, explains its drivers, and proposes place-based policy priorities. The COD-23 draft
communicates that chain on one page:

1. **Where vulnerability is concentrated:** a 206-dong B-IMD map and 21 first-decile areas.
2. **Which areas appear first:** the top ten areas and scores.
3. **What drives the result:** employment leads in 12 and income in nine priority areas.
4. **How it may be used:** two exploratory types linked to policy candidates.
5. **Where interpretation stops:** explicit proxy, sensitivity, causality, and individual-use
   warnings.

It therefore fits the current purpose of **screening places, explaining patterns, and linking
field-validation candidates** from public data. It does not fit the different purposes of
establishing an official index, deciding individual eligibility, or proving policy effects.
The submission should call it a public-data baseline for Busan vulnerability diagnosis and
make administrative-data and field-validation expansion part of the proposal's value.

## Outputs

- [`busan_imd_one_page_2025.pdf`](../../../outputs/infographic/busan_imd_one_page_2025.pdf):
  one-page competition PDF draft
- [`busan_imd_one_page_2025.svg`](../../../outputs/infographic/busan_imd_one_page_2025.svg):
  editable vector source
- [`busan_imd_one_page_2025.png`](../../../outputs/infographic/busan_imd_one_page_2025.png):
  quick-review preview
- [INFOGRAPHIC_REPORT_2025.json](../../data/manifests/INFOGRAPHIC_REPORT_2025.json):
  input/output checksums, page count, displayed statistics, and artifact status

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

This is a `submission_draft`. COD-24 should align report terminology, after which the final
submission check must reconfirm naming, source-note size, exactly one PDF page, and print
legibility.
