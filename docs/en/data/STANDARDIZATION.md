# 2025 Administrative-dong Data Standardization and Validation

## Purpose

The pipeline joins collected source data to the 206 Busan administrative-dong boundaries for
SGIS 2025 and creates a candidate profile for later indicator design. The output is not an IMD
score. Sources with incompatible periods or definitions remain `proxy_hold` or
`validation_only`.

## Run

```bash
docker compose run --rm jupyter python -m busan_imd.standardization
```

Outputs:

- `data/processed/standardized/2025/busan_admin_dong_candidate_profile_2025.csv`: reproducible,
  Git-ignored processed data;
- `data/processed/standardized/2025/standardization_report.json`: local report copy; and
- `docs/data/manifests/STANDARDIZATION_REPORT_2025.json`: tracked validation and provenance report.

## Rules

1. The canonical geography is the 206 SGIS 2025 Busan administrative dongs in `EPSG:5179`.
2. Code-based sources are checked for format, duplicates, membership, and complete coverage.
3. Point sources retain their source CRS, are transformed to `EPSG:5179`, and use a `within` join.
4. Source nulls remain null. Zero is assigned only when a successfully joined inventory has no
   points in a canonical dong.
5. Per-population rates use the 31 December 2025 resident population denominator.
6. Source paths and SHA-256 values are recorded for reproducibility.

## Run result at 2026-08-13

| Source | Input | Matched | Missing coordinate | Invalid coordinate | Outside boundary | Dongs | Match rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| Resident population | 206 | 206 | - | - | 0 | 206 | 100.00% |
| SGIS establishments/workers | 206 | 206 | - | - | 0 | 206 | 100.00% |
| Latest elderly-living-alone data | 206 | 206 | - | - | 0 | 206 | 100.00% |
| Bus stops | 8,522 | 7,940 | 0 | 0 | 582 | 204 | 93.17% |
| Hospital candidates | 406 | 377 | 29 | 0 | 0 | 145 | 100.00%* |
| Clinic candidates | 5,320 | 5,270 | 50 | 0 | 0 | 199 | 100.00%* |
| Pharmacy candidates | 1,731 | 1,712 | 19 | 0 | 0 | 197 | 100.00%* |
| Current AED inventory | 1,079 | 1,078 | 0 | 0 | 1 | 187 | 99.91% |
| Crime-prevention CCTV | 21,060 | 20,956 | 6 | 43 | 55 | 206 | 99.74%* |
| Heat shelters | 1,789 | 1,787 | 0 | 0 | 2 | 206 | 99.89% |

`*` The match-rate denominator includes only records with present, valid coordinates. Missing and
invalid coordinates are disclosed separately and are never converted to zero.

The profile has 206 rows and a 2025 resident-population total of 3,241,600. Twenty dongs lack an
elderly-source reference date, and the source mixes dates, so it is validation-only. The 582
unmatched bus stops require source-level review for outside-city, coastal, or boundary cases.

## Current roles

- Primary denominator: 2025 resident population
- Held proxies: 2024 establishments and workplace workers; bus stops; hospitals, clinics, and
  pharmacies; crime-prevention CCTV; and heat shelters
- Validation only: mixed-date elderly-living-alone data and the current AED inventory whose
  historical reference date is unverified

Held sources must pass the [availability matrix](AVAILABILITY_MATRIX.md) inclusion gate before
entering the composite index.
