# 원본 데이터 수집과 출처 기록

## 2026-08-12~13 수집 결과

COD-12는 직접 다운로드, 인증 API와 공개 조회를 합쳐 23개 데이터셋의 원본을 로컬에
보존한다. 기존 인증 API와 직접 다운로드는
[RAW_DATA_MANIFEST.json](manifests/RAW_DATA_MANIFEST.json), HEIS 일평균자료는
[HEIS_AIR_MANIFEST_2026.json](manifests/HEIS_AIR_MANIFEST_2026.json), 학교·인구는
[REFERENCE_DATA_MANIFEST.json](manifests/REFERENCE_DATA_MANIFEST.json), 병원·의원·약국은
[HEALTHCARE_FACILITY_MANIFEST_2025.json](manifests/HEALTHCARE_FACILITY_MANIFEST_2025.json), 교통사고는
[KOROAD_TRAFFIC_ACCIDENT_MANIFEST.json](manifests/KOROAD_TRAFFIC_ACCIDENT_MANIFEST.json), 화재는
[FIRE_SUMMARY_MANIFEST_2025.json](manifests/FIRE_SUMMARY_MANIFEST_2025.json)에 기록한다.

| 구분 | 데이터셋 | 건수 | 컷오프 판정 |
|---|---|---:|---|
| 직접 다운로드 | 기초생활보장 5개 구, 빈집 2개 구, 무더위쉼터, 대기측정망 | 9개 파일 | 사용 가능 9; 침수흔적 1개는 범위 결정에 따라 제외 |
| SGIS API | 2024 사업체·종사자 | 206개 행정동 | 사용 가능 |
| SGIS API | 2024 노후주택 비율 → 2025 1년 시차 추론 | 206개 행정동 | 잠정 사용 가능 |
| 부산 버스 API | 정류소 | 8,790 | 관측 기준일 확인 필요 |
| 부산 AED API | 자동심장충격기 | 1,079 | 관측 기준일 확인 필요 |
| 부산 대기질 API | 시간별 측정값 | 1,184 | 제외: 2026-08-11~12 |
| 부산 HEIS 공개 조회 | 2025년 연간 측정소별 일평균 | 33개소·12,045행 | 주 분석: 2025-01-01~12-31 |
| 부산 HEIS 공개 조회 | 2026년 1~7월 측정소별 일평균 | 33개소·6,996행 | 보조 검증: 2026-01-01~07-31 |
| 부산 버스정류소 SHP | 2025-01-21 정류소 위치 | 8,522개소 | 사용 가능 |
| NEIS API | 부산 학교기본정보 | 전체 667개교·2025 기준 662개교 | 5개교 제외 |
| 행정안전부 병원 API | 현재 641건·2025 운영 후보 406건 | 좌표 377건 | 과거 완전성 검증 필요 |
| 행정안전부 의원 API | 현재 8,649건·2025 운영 후보 5,320건 | 좌표 5,270건 | 과거 완전성 검증 필요 |
| 행정안전부 약국 API | 현재 4,336건·2025 운영 후보 1,731건 | 좌표 1,712건 | 과거 완전성 검증 필요 |
| KOROAD API | 2025 구·군 통계·2024 다발지역 | 202행·48행 | 검증 전용 |
| 소방청 API | 2025 소방서별 일일 화재처리 요약 | 3,156행·365일 | 검증 전용 |

`사용 가능`은 수집 컷오프 이하라는 뜻이다. 주 지수에는 2025년 자료를 우선하며 2026년 부분연도 자료는 보조 검증으로만 사용한다.
공간범위, 정의, 직접/대리 적합성 및 재배포 조건을 포함한 A/B 게이트는 별도로 통과해야
한다. 버스와 AED는 API가 레코드별 관측 기준일을 제공하지 않아 점수 산정 전 확인이
필요하다. 실시간 대기질 스냅샷은 컷오프 밖이므로 출처 감사용으로만 보존한다. HEIS
자료는 컷오프 안이지만 측정소 관측값이므로 행정동 지수에 쓰기 전에 측정소 좌표 결합,
공간 보간 방식과 불확실성 검증이 필요하다.

## 저장 구조

```text
data/raw/
├── audit/                         # 기존 직접 다운로드 10개
├── bus_stops/2025/                # 2025-01-21 버스정류소 SHP ZIP
├── collection/                    # API 응답 4개와 로컬 manifest
│   ├── EMP-SGIS-001/
│   ├── ENV-AIR-REALTIME-001/
│   ├── HLT-AED-001/
│   ├── HOU-BUSSTOP-API-001/
│   └── manifest.json
├── heis/air_daily/                # HEIS 연도별 원본 HTML, 통합 CSV와 로컬 manifest
│   ├── 2025/                      # 원본 HTML 396개와 연간 12,045행
│   └── 2026/                      # 원본 HTML 231개와 1~7월 6,996행
├── reference/                     # SGIS 인구·가구 등 보조 원본
├── mois/resident_population/2025/ # 수동 다운로드 주민등록인구와 206동 통합 CSV
├── public_data_portal/
│   ├── healthcare_facilities/     # 병원·의원·약국 페이지 원본과 2025 후보 CSV
│   └── fire/2025/                 # 소방청 365일 원본과 부산 소방서 일일요약 CSV
├── koroad/traffic_accidents/       # 16개 구·군별 교통사고 API 원본
├── supplemental/                  # 생활인구·복지·CCTV·버스 이용량 등 보조자료
│   ├── basic_livelihood/          # 구·군별 기초생활보장 행정동 원본
│   └── bus_route_usage/           # 2025 노선별 버스 이용량
└── sgis/admin_boundaries/2025/    # COD-11 기준경계
```

`data/raw`는 Git에서 제외된다. 저장소에는 원본 대신 `docs/data/manifests` 아래의 비밀값이 제거된
출처 manifest를 커밋하며, 각
항목에 다음을 기록한다.

- 제공기관과 공식 원문 페이지
- 비밀 쿼리를 제외한 API 엔드포인트와 요청 파라미터
- 2025 주 분석 여부, 관측기간, 기간 유형, 수집시각과 2026-07-31 수집 컷오프 판정
- 이용허락 또는 이용정책
- 로컬 상대경로, 파일 크기, 레코드 수와 SHA-256
- 점수 사용 전 필요한 제한사항

## 실행

최상단 `.env`에 다음 값이 있어야 한다. 실제 값은 Git, 문서, Slack 또는 Linear에 넣지
않는다.

```dotenv
SGIS_CONSUMER_KEY=...
SGIS_CONSUMER_SECRET=...
DATA_GO_KR_SERVICE_KEY=...
NEIS_API_KEY=...
KOROAD_API_KEY=...
```

```powershell
$env:PYTHONPATH = "src"
python -m busan_imd.collectors.approved_apis
python -m busan_imd.collectors.reference_data
python -m busan_imd.collectors.healthcare_facilities
python -m busan_imd.collectors.traffic_accidents
python -m busan_imd.collectors.police_crime
python -m busan_imd.collectors.housing
```

수집기는 다음 검사를 모두 통과해야 manifest를 쓴다.

1. 직접 다운로드 10개의 SHA-256이 감사 원장과 일치한다.
2. SGIS 사업체 응답은 2024년 부산 행정동 206개 코드가 유일하다.
3. 공공데이터포털 응답코드는 성공이고 `totalCount`와 실제 항목 수가 일치한다.
4. manifest의 데이터셋 ID는 유일하고 인증키·access token을 포함하지 않는다.
5. 존재하는 모든 로컬 원본의 SHA-256이 manifest와 일치한다.

API는 갱신되므로 다시 실행하면 응답 건수와 체크섬이 달라질 수 있다. 갱신 결과는 자동으로
이전 자료를 덮어쓰므로, 기준 스냅샷을 바꿀 때만 실행하고 변경 사유와 수집시각을 PR에
기록한다.

HEIS 일평균자료는 인증키가 필요 없다. 아래 명령은 기본적으로 이미 저장된 HTML을
재사용하며, `--refresh`를 붙이면 33개 측정소의 2026년 1~7월 페이지를 다시 요청한다.

```powershell
$env:PYTHONPATH = "src"
python -m busan_imd.collectors.heis_air
python -m busan_imd.collectors.heis_air --year 2025
python -m busan_imd.collectors.heis_air --refresh
```

수집기는 광복동을 포함한 측정소 목록을 페이지에서 자동 탐색하고, 각 월의 달력 일수와
표 행 수가 일치할 때만 CSV를 만든다. `점검중`과 `-`는 0으로 바꾸지 않고 오염물질 값을
비워 둔 뒤 `measurement_status`에 원문 상태를 보존한다.

## 확보했지만 주 분석 전 검증이 필요한 후보

- 병원·의원·약국: 현재 목록에서 2025-12-31 상태를 재구성했으므로 과거 완전성 검증 필요
- KOROAD: 구·군 통계와 일부 다발지역만 제공하므로 행정동 전체 사고자료가 아님
- 학교: 2025년 이후 개교 5개교를 제외하고 662개 중 655개를 SGIS 공식 좌표화했다.
  핵심 학교 616개로 206개 동 접근성 후보를 생성했으며 주소 없는 7개는 별도 공개한다.

세부 범위와 남은 검증은 [공개자료 접근 및 수집 현황](DATA_ACCESS_REQUIREMENTS.md)을 따른다.

## 출처 원칙

인증키가 없는 직접 다운로드도 API와 동일하게 제공기관, 원문 URL, 관측기간, 수집일,
이용조건, 파일 크기, 레코드 수와 SHA-256을 기록한다. 파일명이나 포털 게시일만으로
관측기간을 추정하지 않는다.
# 2025년 주민등록 인구·세대 자료

행정안전부 주민등록 인구통계에서 내려받은 부산 16개 구·군 CSV를 행정동 206개 행의
단일 파일로 결합했다. 원본은 CP949, 결합 결과는 UTF-8 BOM CSV이며, MOIS 10자리 코드와
2025년 SGIS 행정동 코드를 함께 보존한다.

- 결합 파일: `data/raw/mois/resident_population/2025/busan_resident_population_admin_dong_2025_12.csv`
- 출처 및 무결성 기록: [MOIS_RESIDENT_POPULATION_MANIFEST_2025.json](manifests/MOIS_RESIDENT_POPULATION_MANIFEST_2025.json)
- 기준시점: 2025-12-31
- 행정동 수: 206개
- 검증: 구·군별 합계, 부산시 합계, 남녀 인구 합, 세대당 인구, 성비, 코드 중복 및 SGIS 매칭

재생성 명령은 다음과 같다.

```powershell
$env:PYTHONPATH = "src"
python -m busan_imd.collectors.resident_population
```

## 부산 보조자료 10종

승인된 공공데이터포털 키로 마을버스와 독거노인 API를 수집하고, 공개 파일인 생활인구,
교통사고 추세, 사고위험지역, 2025 복지사업 구·군 통계, 해운대구 기초생활수급자,
방범용 CCTV, 2023 정류소별 승하차와 2025 노선별 버스 이용량을 함께 수집한다.

```powershell
$env:PYTHONPATH = "src"
python -m busan_imd.collectors.supplemental_data
python -m busan_imd.collectors.supplemental_data --refresh
```

기본 실행은 기존 원본을 재사용하며 `--refresh`일 때만 원격 자료를 다시 요청한다. 결과는
`data/raw/supplemental`에 보존하고 출처·건수·기간·체크섬은
[BUSAN_SUPPLEMENTAL_DATA_MANIFEST.json](manifests/BUSAN_SUPPLEMENTAL_DATA_MANIFEST.json)에 기록한다.
독거노인 자료는 16개 구·군 응답 원본과 2025 SGIS 행정동 206개에 맞춘 최신 동별 CSV를
함께 보존한다.
