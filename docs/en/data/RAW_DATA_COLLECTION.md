# Raw-data collection and provenance

## Collection result on 2026-08-12

COD-12 preserves 14 local raw sources: ten direct downloads and four authenticated API responses.
The secret-free [RAW_DATA_MANIFEST.json](../../data/RAW_DATA_MANIFEST.json) records their provenance
and validation.

| Type | Dataset | Records | Cutoff status |
|---|---|---:|---|
| Direct downloads | Benefits in five districts, vacancies in two, heat shelters, air-station register, flood traces | 10 files | 10 eligible |
| SGIS API | 2024 establishments and workplace workers | 206 dongs | Eligible |
| Busan bus API | Stops | 8,790 | Observation date unverified |
| Busan AED API | Emergency equipment | 1,079 | Observation date unverified |
| Busan air API | Hourly observations | 1,184 | Excluded: 2026-08-11–12 |

`Eligible` only means the period ends by 2026-07-31. It does not bypass the A/B inclusion gate for
coverage, definition, direct/proxy validity, or reuse. The bus and AED APIs expose no record-level
observation date and therefore require confirmation before scoring. The real-time air snapshot is
outside the cutoff and remains provenance-only.

## Storage and metadata

Direct downloads remain in `data/raw/audit/`; API responses are written below
`data/raw/collection/`; COD-11 boundaries remain below `data/raw/sgis/`. All raw paths are excluded
from Git. The versioned manifest records provider, official source page, secret-free endpoint and
parameters, observation period and type, retrieval time, cutoff status, terms, local path, bytes,
record count, SHA-256, and usage caveats.

## Run

Keep `SGIS_CONSUMER_KEY`, `SGIS_CONSUMER_SECRET`, and `DATA_GO_KR_SERVICE_KEY` in the root `.env`.
Never commit or paste their values.

```powershell
$env:PYTHONPATH = "src"
python -m busan_imd.raw_collection
```

Before writing the manifest, the collector verifies all ten direct-download checksums, 206 unique
SGIS dong rows, successful portal responses, `totalCount` against returned item counts, unique
dataset IDs, absence of credentials, and local SHA-256 values.

API responses can change. Rerunning overwrites the local API snapshots and updates checksums, so do
so only when intentionally refreshing the reference snapshot and record the reason and retrieval
time in the pull request.

## Candidates still without raw files

- KERIS school-register external download
- Nationwide LOCALDATA hospital and pharmacy files
- Busan bus-stop SHP (the API XML is collected)
- Reproducible TAAS crash source

These remain `not_collected` in the audit. They are not presented as acquired until their external
download path, redistribution terms, or reproducible extraction method is verified. Only the 14
manifested sources form the current COD-12 snapshot.

Direct no-key downloads follow exactly the same attribution rule as APIs: provider, source URL,
observation period, retrieval date, terms, bytes, record count, and SHA-256 are mandatory.
