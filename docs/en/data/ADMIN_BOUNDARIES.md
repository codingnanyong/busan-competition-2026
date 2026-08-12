# Busan administrative-dong codes and boundaries

## Reference-geography decision

- Reference year: **2025**
- Spatial unit: Busan administrative dong
- Canonical key: SGIS eight-digit `adm_cd`
- Unit count: **206 dongs** across 16 districts/counties
- Boundary CRS: UTM-K, `EPSG:5179`

The official SGIS administrative-boundary API serves 2025 boundaries. A request with
`adm_cd=21`, `low_search=2`, and `year=2025` returned the same 206 codes and boundary
features. This project therefore resolves the inconsistent 205 label and 206 district-count
sum on the Busan administrative-area page by adopting the **206-unit SGIS 2025 geography**.

This fixes the analytical geography, not every indicator's observation year. Dataset lags
remain explicit in the catalog and result metadata.

## Source and attribution

- Provider: Statistics Korea, Statistical Geographic Information Service (SGIS)
- [Official administrative-boundary API documentation](https://sgis.mods.go.kr/developer/html/newOpenApi/api/dataApi/addressBoundary.html)
- Endpoint: `https://sgisapi.mods.go.kr/OpenAPI3/boundary/hadmarea.geojson`
- [SGIS use policy](https://sgis.mods.go.kr/developer/html/newOpenApi/policy/policy.html)
- Access: short-lived access token issued from personal SGIS consumer credentials
- Versioned codes: `docs/data/BUSAN_ADMIN_DONG_CODES_2025.csv`
- Versioned provenance snapshot: `docs/data/BUSAN_ADMIN_DONG_MANIFEST_2025.json`

The authenticated raw GeoJSON is excluded from Git due to its size and redistribution
conditions. The manifest instead records the source, non-secret request parameters,
retrieval time, feature count, CRS, and SHA-256 checksums. Recheck the current SGIS terms
before publishing or redistributing raw boundaries.

## Reproduction

Place the following values in the repository-root `.env`; never commit the real values.

```dotenv
SGIS_CONSUMER_KEY=...
SGIS_CONSUMER_SECRET=...
```

```powershell
$env:PYTHONPATH = "src"
python -m busan_imd.admin_boundaries --year 2025
docker compose run --rm --no-deps jupyter python scripts/validate_admin_boundaries.py `
  data/raw/sgis/admin_boundaries/2025/busan_admin_dong_boundaries_2025.geojson `
  --repair-output data/raw/sgis/admin_boundaries/2025/busan_admin_dong_boundaries_2025_valid.geojson `
  --report docs/data/BUSAN_ADMIN_DONG_GEOMETRY_VALIDATION_2025.json
```

The command writes ignored raw artifacts under
`data/raw/sgis/admin_boundaries/2025/`. Add `--reference-dir docs/data` only when
intentionally refreshing the versioned code and provenance snapshots.

## Validation on 2026-08-12

| Check | Result |
|---|---:|
| API response | Success (`errCd=0`) |
| Administrative-dong codes | 206 |
| Boundary features | 206 |
| Duplicate codes | 0 |
| Code format | all eight digits beginning with `21` |
| Code-to-boundary join | 206/206 |
| Geometry types | Polygon, MultiPolygon |
| Empty geometries | 0 |
| Invalid source geometries | 1 (Dadae 1-dong, ring self-intersection) |
| Invalid geometries after `make_valid` | 0 |
| CRS | UTM-K (`EPSG:5179`) |

GeoPandas found one ring self-intersection in the SGIS source for Dadae 1-dong
(`21100620`). The source and its checksum remain unchanged for auditability. The analytical
copy applies Shapely `make_valid`, after which all 206 geometries are valid. The validation
report records the error coordinate, area change, and source/repaired SHA-256 checksums.

## Downstream rules

1. Join administrative dongs by `admin_dong_code`, not names.
2. Use the `_valid.geojson` copy for spatial analysis and preserve the SGIS source for audit.
3. Confirm source CRS and transform point datasets to `EPSG:5179` before spatial joins.
4. Never silently relabel another year's units as 2025; use a documented crosswalk or
   spatial-weighting rule.
5. Record provider, source URL/API, reference period, retrieval time, licence or terms, and
   SHA-256 for every source, including no-key direct downloads.
