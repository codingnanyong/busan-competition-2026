# 2025 submission reproducibility review

Verified: 2026-08-31 (KST). COD-25.

## Scope

This review inspects the Git draft and the contest ZIP. It does not recompute scores from
a restored raw-data bundle. Full regeneration still follows
`scripts/rebuild_processed.py` after the Drive bundle is restored.

## Checks that passed

| Check | Result |
|---|---|
| Visualization PDF | Exactly one page |
| Draft report PDF | Eight pages including cover; seven body pages |
| Source catalog | 42 rows with provider, URL, access method, period, license, decision |
| Derived tables | Four dong-level profile and category CSVs |
| Raw extracts | Absent from Git and the ZIP. Reason is in `03_data/README.txt` |
| Secrets | No API keys or `consumer_secret` in submission text files |
| Official HWPX | Not in Git. The Hangul files live only in the contest ZIP |

Commands:

```bash
docker compose run --rm jupyter python -m pytest -q
python -c "from busan_imd.submission.verify import verify_committed_package; print(verify_committed_package())"
```

## Licenses

Sources whose redistribution terms are unconfirmed (SGIS, HEIS, KOROAD, and others) are
omitted from the archive. Provider, URL, access method, period, and license stay in
`03_data/source-catalog`.

## Contest ZIP versus Git draft

| Artifact | Git draft | Contest ZIP |
|---|---|---|
| One-page visualization | Yes | Yes |
| Pipeline report PDF | Yes | No. The Hangul PDF is used |
| Hangul HWPX/PDF | No | Yes |
| Browser dashboard | `outputs/infographic/2025/interactive/` | `04_interactive/` |
| Raw tar.gz | No. Drive `raw-data/2025/` | No |

## Interpretation

Figures match the committed 2025 scores. They are not official statistics, individual
findings, or a statutory budget rule.
