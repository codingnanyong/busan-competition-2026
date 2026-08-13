# 부산 행정동 기준코드와 경계

## 기준지리 결정

- 기준연도: **2025년**
- 공간단위: 부산광역시 행정동
- 기준키: SGIS 8자리 `adm_cd`
- 행정동 수: **206개**(16개 구·군)
- 경계 좌표계: UTM-K, `EPSG:5179`

SGIS 공식 행정구역경계 API는 2025년 경계를 제공한다. `adm_cd=21`, `low_search=2`,
`year=2025`로 조회한 결과 206개 행정동 코드와 206개 경계가 같은 응답에 포함되었다.
따라서 부산시 행정구역 안내 페이지의 205개 표기와 구·군별 합계 206개 간 불일치는 이
프로젝트에서 **SGIS 2025년 206개**를 기준으로 해소한다.

이는 분석의 공간 기준연도를 고정한 결정이다. 모든 지표의 관측연도가 반드시 2025년이어야
한다는 뜻은 아니다. 지표별 시차는 데이터 카탈로그와 결과 메타데이터에 별도로 기록한다.

## 출처와 귀속

- 제공기관: 국가데이터처 통계지리정보서비스(SGIS)
- [공식 행정구역경계 API 문서](https://sgis.mods.go.kr/developer/html/newOpenApi/api/dataApi/addressBoundary.html)
- API 엔드포인트: `https://sgisapi.mods.go.kr/OpenAPI3/boundary/hadmarea.geojson`
- [SGIS 이용정책](https://sgis.mods.go.kr/developer/html/newOpenApi/policy/policy.html)
- 접근방식: 개인 SGIS consumer key/secret으로 단기 access token 발급 후 OpenAPI 호출
- 저장소 기준코드: `docs/data/BUSAN_ADMIN_DONG_CODES_2025.csv`
- 저장소 출처 스냅샷: `docs/data/manifests/BUSAN_ADMIN_DONG_MANIFEST_2025.json`

원본 GeoJSON은 인증 API 산출물이며 크기와 재배포 조건을 고려해 Git에 커밋하지 않는다.
대신 출처, 요청 파라미터, 조회시각, 피처 수, 좌표계 및 원본 SHA-256 체크섬을 manifest에
기록한다. 외부 공개·재배포 전에는 당시 SGIS 이용정책을 다시 확인해야 한다.

## 재현 방법

프로젝트 최상단 `.env`에 다음 값을 넣는다. 실제 키는 Git에 커밋하지 않는다.

```dotenv
SGIS_CONSUMER_KEY=...
SGIS_CONSUMER_SECRET=...
```

```powershell
$env:PYTHONPATH = "src"
python -m busan_imd.collectors.admin_boundaries --year 2025
docker compose run --rm --no-deps jupyter python scripts/validate_admin_boundaries.py `
  data/raw/sgis/admin_boundaries/2025/busan_admin_dong_boundaries_2025.geojson `
  --repair-output data/raw/sgis/admin_boundaries/2025/busan_admin_dong_boundaries_2025_valid.geojson `
  --report docs/data/manifests/BUSAN_ADMIN_DONG_GEOMETRY_VALIDATION_2025.json
```

결과는 Git에서 제외되는 다음 위치에 생성된다.

```text
data/raw/sgis/admin_boundaries/2025/
├── busan_admin_dong_boundaries_2025.geojson
├── busan_admin_dong_codes_2025.csv
└── busan_admin_dong_manifest_2025.json
```

기준코드와 출처 스냅샷을 의도적으로 갱신할 때만 `--reference-dir docs/data`를 추가한다.

## 2026-08-12 검증 결과

| 검사 | 결과 |
|---|---:|
| API 응답 | 성공(`errCd=0`) |
| 행정동 코드 | 206개 |
| 경계 피처 | 206개 |
| 코드 중복 | 0개 |
| 코드 길이/접두사 | 전부 8자리/`21` |
| 코드-경계 결합 | 206/206 |
| 경계 유형 | Polygon, MultiPolygon |
| 빈 경계 | 0개 |
| 원본 유효하지 않은 경계 | 1개(다대1동, ring self-intersection) |
| `make_valid` 보정본 유효하지 않은 경계 | 0개 |
| 좌표계 | UTM-K (`EPSG:5179`) |

스크립트는 응답 성공, 피처 수, 코드 형식·유일성, 부산 명칭, 경계 유형과 빈 좌표를
검사한다. GeoPandas 검증 결과 SGIS 원본의 다대1동(`21100620`)에 ring self-intersection
1건이 확인됐다. 원본과 체크섬은 그대로 보존하고 Shapely `make_valid`로 보정한 별도
GeoJSON을 분석 입력으로 사용한다. 보정 뒤 206개 형상은 모두 유효하다. 오류 좌표,
면적 변화와 원본·보정본 체크섬은 `BUSAN_ADMIN_DONG_GEOMETRY_VALIDATION_2025.json`에
기록한다.

## 후속 사용 규칙

1. 행정동 결합키는 이름이 아니라 `admin_dong_code`를 사용한다.
2. 공간 분석에는 `_valid.geojson` 보정본을 사용한다. SGIS 원본은 감사 추적용으로 보존한다.
3. 좌표 자료는 원본 CRS를 확인하고 `EPSG:5179`로 변환한 뒤 공간결합한다.
4. 다른 연도 자료는 2025 코드로 임의 치환하지 않고 코드 변경표 또는 공간 가중 규칙을 둔다.
5. 모든 수집 자료는 제공기관, 원문 URL/API, 기준기간, 수집시각, 라이선스·이용조건과
   SHA-256을 기록한다. 인증키 없는 직접 다운로드도 같은 규칙을 적용한다.
