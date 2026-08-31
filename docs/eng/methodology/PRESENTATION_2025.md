# 2025 presentation package

Verified: 2026-08-31 (KST). COD-27. Presentation date: 2026-10-29.

## Scope

The contest filing is done. This note is the **slide script, dashboard demo, and anticipated
Q&A** for the oral round. Figures match the committed 2025 scores and policy matrix. The
official notice does not publish talk length, slide format, or a scoring rubric. The
ten-minute timing below is an internal rehearsal length, not a contest rule.

Sources are the [priority areas](PRIORITY_AREAS_2025.md),
[policy matrix](POLICY_MATRIX_2025.md), [sensitivity](SENSITIVITY_ANALYSIS_2025.md),
[limitations](LIMITATIONS.md), and [infographic](INFOGRAPHIC_2025.md). Do not invent
indicators or ranks.

## One-line message

Compare 206 Busan administrative dongs on one code, screen the **most relatively deprived
tenth (21 dongs)**, explain **why** each score is high, and open only **field-validation
policy candidates**. This is not official statistics, individual eligibility, or automatic
budget allocation.

## Rehearsal timing

| Block | Slides | Practice time |
|---|---|---|
| Conclusion and problem | 1–3 | 1 min 30 sec |
| Method | 4–5 | 2 min |
| Results and policy | 6–7 | 2 min 30 sec |
| Dashboard demo | 8 | 2 min |
| Limits, use, close | 9–11 | 2 min |
| Q&A | — | As the host directs |

If time is cut, replace slide 8 with a 30-second screenshot and skip backup answers.

## Slide script

**Bold** lines go on the slide. The paragraph under each slide is spoken.

### 1. Title

**Screening living-condition vulnerability in Busan administrative dongs**
**2026 Big Data Competition · Track 1 analysis and visualization**
**Team codingnanyong · Experimental public-data B-IMD 2025**

Spoken. This talk is not a rank announcement. It shows that public data can screen dongs,
explain drivers, and attach field-validation candidates.

### 2. One-slide conclusion

**206-dong comparison → decile-1 set of 21 → driver decomposition → four field-validation candidates**
**Top three: Mora 3-dong, Sasang-gu, 82.82; Choryang 6-dong, Dong-gu, 80.26; Banyeo 3-dong, Haeundae-gu, 79.70**

Spoken. Composite scores run from 20.96 to 82.82; the median is 51.05. Decile 1 is the most
relatively deprived tenth inside Busan. It is not an absolute poverty finding.

### 3. Why dong scale

**District averages hide within-district gaps. One indicator cannot explain compound deprivation.**
**We need one definition, one administrative-dong code, and a reproducible public pipeline.**

Spoken. Income alone, or stop counts alone, hide other domains. District totals were not
copied onto every dong. Missing values were not filled with zero to pass the inclusion gate.

### 4. What is measured

**Reference: English IoD 2025 domain structure. Rebuilt on Busan public data as a six-domain baseline.**
**Income 24.83% · Employment 24.83% · Education 14.90% · Health 14.90% · Barriers 10.26% · Living environment 10.26%**
**Crime/safety is held out of the composite; no dong-level incident measure is available.**

Spoken. We do not claim English indicators equal Busan indicators. The weights are a
documented baseline. Income is an inferred basic-livelihood allocation from district totals.
Employment is workplace workers, not resident unemployment.

### 5. How it was checked

**Collect → standardize to dongs → domain scores → weighted composite → sensitivity → contributions → exploratory types → environmental overlay → policy gate**
**Equal weights keep 18 of the 21 decile-1 dongs. Dropping income or employment cuts overlap to 57–67%.**

Spoken. We never present a single rank. Spearman correlation under equal weights is 0.936.
The score is sensitive to the two proxies, so welfare and employment registers should be
checked first.

### 6. What drives the top areas

| Rank | Dong | B-IMD | Leading domain |
|---:|---|---:|---|
| 1 | Mora 3 | 82.82 | Income |
| 2 | Choryang 6 | 80.26 | Employment |
| 3 | Banyeo 3 | 79.70 | Employment |
| 4 | Sujeong 4 | 77.22 | Employment |
| 5 | Deokcheon 3 | 76.36 | Employment |

**Among 21 priority dongs, employment leads 12 and income leads 9. The leading driver is weighted excess over the Busan median, not raw contribution.**

Spoken. In Mora 3-dong the income proxy lifts the composite above the city median. Do not
read that number as observed resident income. It is a signal for field and register checks.

### 7. Which candidates to review

**Two exploratory types. Four policy candidates. Every row is a field-validation candidate.**

| Type | Places | Candidate |
|---|---|---|
| Education / living-environment relative | 5 dongs | After-school and school-access review |
| Same type | Garak | Particulate monitoring and sensitive-group protection |
| Employment / income | 16 dongs | Local jobs and training; missed-benefit case review |
| Same type | Mora 3, Sujeong 4, Sujeong 1 | Particulate monitoring and sensitive-group protection |

Spoken. The five education-relative dongs are Garak, Yeongju 2, Songjeong, Goejeong 2, and
Gupo 3. That type’s living-environment mean excess is negative, so a generic environment
package is not auto-recommended. A category policy card opens only when the child score is
70 or higher.

### 8. Demo — browser dashboard

**Open the HTML with no server. It does not replace the one-page PDF.**
**Pick a tree item → map colors change → click a dong → see estimate notes and the 70-point gate.**

Spoken. I will open Mora 3-dong and show when a policy card appears. Follow the demo
section below.

### 9. Where interpretation stops

**Do not: decide individual eligibility, label statutory lagging areas, auto-allocate budgets, or rename proxies as unemployment, crime, or disease.**
**Six-domain experimental baseline. Do not compare score changes across years or cities.**

Spoken. Not every resident of a high-scoring dong is deprived. Air quality is IDW from 32
monitors; the farthest nearest-station distance is 7.47 km. Those limits sit on the screen
and in the report.

### 10. Use and expected value

**Use: city and district staff in welfare, jobs, education, health, and environment pick field-review places.**
**Quantity: 206 dongs on one code, 21 in decile 1, 18 retained under equal weights, 42 audited sources with explicit roles.**
**Quality: each dong shows whether a value is estimated or a proxy, so a full register can replace it immediately.**

Spoken. The dashboard never adds the composite rank to the category scores. That is
intentional, to reduce misuse.

### 11. Close

**The public-data baseline narrows where to look, why, and what to check first.**
**Next inputs: observed dong-level basic livelihood, resident employment, full crime and accident counts, health and education outcomes.**
**Questions welcome.**

## Dashboard demo

Rehearse for two minutes. No network is required. No JavaScript server is required.

### File to open

Repository:

`outputs/infographic/2025/interactive/busan_admin_dong_action_map_2025.html`

Contest ZIP:

`04_interactive/busan_admin_dong_action_map_2025.html`

`css/` and `js/` must sit beside the HTML. Without `js/data.js` the map is empty. Open it
in Chrome or Edge. Copy the folder locally before the talk. Do not present from a syncing
cloud folder.

### Click path

1. Point at the four-step guide: tree → map → dong → evidence and policy.
2. In the Korean tree, select **사회·경제**. Map colors switch to the weighted child scores.
3. Select **소득·복지수요**. Confirm the estimate notice is visible.
4. Click **Mora 3-dong, Sasang-gu** on the map (western Busan, northern Sasang). Practice
   once before the talk; use the dong tooltip if needed.
5. Read the right panel: raw indicator, deprivation percentile, weight, estimate reason,
   confidence.
6. Open the bottom policy panel. Say that only child scores at or above 70 open a review
   card, and the same package is not applied below the gate.
7. If time remains, select **환경** and name the four double-burden candidates:
   Garak, Mora 3, Sujeong 4, and Sujeong 1. Teal points on the one-page PDF are the same
   COD-21 set.
8. Say in one sentence that reference overlays do not change scores. AED and parks are
   context layers.

### Fallback

| Problem | Response |
|---|---|
| White page | Confirm `css/` and `js/data.js` keep their relative paths. Do not email the HTML alone |
| Cannot find the dong | Point at Mora 3-dong on the one-page PDF, then show only the HTML panel |
| Small projector | Browser zoom 125%. Collapse the tree; keep the map and right panel |
| No time | Put one Mora 3-dong panel screenshot on slide 8 |

Regeneration is not needed for the demo. If asked how scores are rebuilt:

```bash
docker compose run --rm jupyter python scripts/rebuild_processed.py
```

The raw bundle lives on Drive `raw-data/2025/` and is not in the ZIP.

## Anticipated Q&A

Answer first in one sentence, then add one supporting sentence. Do not invent unpublished
rubrics or official indexes.

### Method

**Q. Did you apply the English IMD unchanged?**
A. Only the domain structure and published weights. Indicators are Busan public data, and
safety is out, so the composite is six domains. Equal-weight sensitivity is published with
it.

**Q. Are the weights arbitrary?**
A. The baseline renormalizes English IoD 2025 weights onto the six available domains. No
Busan-specific alternative weight was invented without a policy agreement. Equal weights
still keep 18 of 21 decile-1 dongs.

**Q. Income and employment are proxies. Can we trust first place?**
A. The report says not to use rank alone. Income is an allocated district total; employment
is workplace workers. Those two domains are the first to replace when resident registers
arrive.

**Q. Did you paste district values onto every dong?**
A. No. The inclusion gate forbids it. Sixteen district totals are held fixed, then split by
published dong shares or a relative-risk model. Dong values are labeled as not observed.

### Results

**Q. Is this official statistics or a statutory lagging-area list?**
A. No. It is an experimental public-data baseline. Do not use it for automatic budgets or
individual eligibility.

**Q. Is Mora 3-dong the poorest place in Busan?**
A. We cannot say that. It is first on a within-Busan relative score, and the leading signal
is an inferred basic-livelihood proxy. It is the first candidate for welfare-register and
field checks.

**Q. Can the two clusters be used as official types?**
A. They are exploratory. Only `k=2` passed the quality gate, and it does not replace
continuous contributions. Policy rows are created only when mean excess in that type is
positive.

**Q. What is particulate double burden?**
A. Decile-1 dongs whose social score stays in decile 1 after particulates are removed and
that also show high air-exposure. The four places are Garak, Mora 3, Sujeong 4, and
Sujeong 1. That is not an emissions causal claim.

### Data and reproducibility

**Q. Why is raw data missing from the ZIP?**
A. Redistribution terms for SGIS, HEIS, KOROAD, and similar sources are unconfirmed, and
the files are large or sensitive. Provider, URL, period, and license are in
`source-catalog`. The team raw bundle is on Drive `raw-data/2025/`.

**Q. Can this be reproduced?**
A. Docker rebuilds scores and graphics with `scripts/rebuild_processed.py`. The draft
package was checked for page counts, 42 catalog rows, and no secrets. The official HWPX is
the Hangul-authored file.

**Q. Why is missing bus headway not zero?**
A. A dong with no headway fields is missing, not zero. Only observed dongs enter that
percentile. That 20% weight is dropped from the category sum, and the policy gate stays
closed.

**Q. Why did Myeongji scores change?**
A. The older education score used centroid distance only (Myeongji 1 / 2 at 84.9 and
90.7). Adding school counts, 2 km supply, and active teachers moved them to 58.1 and 67.9,
below the 70-point gate.

### Use

**Q. How does the dashboard differ from the one-page PDF?**
A. The PDF is the required one-page visual. The dashboard is the operating view for 19
indicators and the 70-point gate. It does not replace the required PDF.

**Q. What is the specialization or tourism direction?**
A. Only relatively low-deprivation domains are kept as preservation candidates. Industry,
commerce, and living-SOC data are missing, so a specialization strategy is not claimed.

**Q. Can you promise a quantified policy effect?**
A. No effect size is claimed. The quantitative claim is 206 dongs on one code, 21 in
decile 1, and 18 retained under equal weights. Policy effects remain monitoring hypotheses.

**Q. Open Lab or Big Data Wave extra credit?**
A. Participation is not confirmed, so the filing does not claim it.

## Day-of checklist

- [ ] Slide figures match this note and the report. Do not invent a new rank live.
- [ ] Copy `busan_admin_dong_action_map_2025.html` with `css/` and `js/` to USB or local disk.
- [ ] Practice the Mora 3-dong click offline once.
- [ ] Keep the one-page PDF as a backup screen.
- [ ] Say “experimental baseline, no individual findings” once after the title or at the close.
- [ ] After document screening (2026-09-23), adjust only rehearsal timing if the host
      publishes equipment or talk length. Do not change committed figures.

## Related artifacts

- One-page visual: `outputs/infographic/2025/static/busan_imd_one_page_2025.pdf`
- Dashboard: `outputs/infographic/2025/interactive/busan_admin_dong_action_map_2025.html`
- Report body: `outputs/submission/2025/02_analysis-report.md`
