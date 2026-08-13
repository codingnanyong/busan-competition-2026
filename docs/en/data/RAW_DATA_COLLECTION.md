# Raw-data collection and provenance

## Collection result on 2026-08-12–13

COD-12 preserves 23 local datasets across direct downloads, authenticated APIs, and public queries.
Secret-free manifests in `docs/data/manifests` record provenance and validation for the base collection, HEIS,
reference data, healthcare facilities, KOROAD crashes, and the dated bus-stop snapshot.

| Type | Dataset | Records | Cutoff status |
|---|---|---:|---|
| Direct downloads | Benefits in five districts, vacancies in two, heat shelters, air-station register, flood traces | 10 files | 10 eligible |
| SGIS API | 2024 establishments and workplace workers | 206 dongs | Eligible |
| Busan bus API | Stops | 8,790 | Observation date unverified |
| Busan AED API | Emergency equipment | 1,079 | Observation date unverified |
| Busan air API | Hourly observations | 1,184 | Excluded: 2026-08-11–12 |
| NEIS API | Busan schools | 667 total; 662 eligible at 2025-12-31 | Hold for geocoding |
| MOIS hospital API | Current register and reconstructed 2025 candidates | 641 / 406 | History and coordinate validation required |
| MOIS pharmacy API | Current register and reconstructed 2025 candidates | 4,336 / 1,731 | History and coordinate validation required |
| KOROAD API | 2025 district statistics / 2024 hotspots | 202 / 48 | Validation only |
| National Fire Agency API | 2025 daily fire-station summaries | 3,156 rows / 365 dates | Validation only |

`Eligible` only means the period ends by the collection cutoff. The primary index still requires
2025 data; 2026 part-year data is supplemental validation only. Eligibility does not bypass the A/B
inclusion gate for coverage, definition, direct/proxy validity, or reuse. The bus and AED APIs expose no record-level
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
python -m busan_imd.collectors.approved_apis
```

Before writing the manifest, the collector verifies all ten direct-download checksums, 206 unique
SGIS dong rows, successful portal responses, `totalCount` against returned item counts, unique
dataset IDs, absence of credentials, and local SHA-256 values.

API responses can change. Rerunning overwrites the local API snapshots and updates checksums, so do
so only when intentionally refreshing the reference snapshot and record the reason and retrieval
time in the pull request.

## Collected candidates that still require validation

- The school register requires geocoding and service-area checks.
- Hospital and pharmacy 2025 candidates are reconstructed from the current licence register and
  require historical-completeness and coordinate checks.
- KOROAD statistics are district-level, while hotspots are selected locations rather than a complete
  crash census; both remain validation-only.

Direct no-key downloads follow exactly the same attribution rule as APIs: provider, source URL,
observation period, retrieval date, terms, bytes, record count, and SHA-256 are mandatory.
