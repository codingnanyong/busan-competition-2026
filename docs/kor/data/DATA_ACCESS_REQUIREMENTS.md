# 공개자료 접근 및 수집 현황

## 2026-08-13 확인 결과

| 자료 | 공식 위치 | 수집 결과 | 남은 조건 |
|---|---|---|---|
| SGIS 인구·가구 | [SGIS 센서스 API](https://sgis.mods.go.kr/developer/html/newOpenApi/api/dataApi/census.html) | 2024년 부산 206개 행정동 완료 | 2025 경계와 1년 시차 검증 |
| 학교기본정보 | [나이스 교육정보 개방포털](https://open.neis.go.kr/portal/data/service/selectServicePage.do?infId=OPEN17020190531110010104913&infSeq=1) | 부산 667개교 완료, 2025 기준 662개교 선별 | 주소 좌표화와 서비스권역 검증 |
| 병원 | [행정안전부 건강 병원 조회서비스](https://www.data.go.kr/data/15154458/openapi.do) | 현재 641건 전체 응답, 2025-12-31 운영 후보 406건 | 과거 완전성 및 EPSG:5174 좌표 검증 |
| 의원 | [행정안전부 건강 의원 조회서비스](https://www.data.go.kr/data/15154874/openapi.do) | 현재 8,649건 전체 응답, 2025-12-31 운영 후보 5,320건 | 과거 완전성 및 EPSG:5174 좌표 검증 |
| 약국 | [행정안전부 건강 약국 조회서비스](https://www.data.go.kr/data/15154822/openapi.do) | 현재 4,336건 전체 응답, 2025-12-31 운영 후보 1,731건 | 과거 완전성 및 EPSG:5174 좌표 검증 |
| 교통사고 | [KOROAD 교통사고정보 OpenAPI](https://opendata.koroad.or.kr/api/selectOpenApi.do#api1) | 2025 구·군 통계 202행, 2024 다발지역 48행 완료 | 행정동 원자료가 아니므로 검증 자료로만 사용 |
| 화재 | [소방청 국가화재정보 API](https://www.data.go.kr/data/15077644/openapi.do) | 2025년 365일·부산 소방서 3,156행 완료 | 주소·행정동이 없는 소방서 요약이므로 검증 자료로만 사용 |

학교, 병원, 의원, 약국과 KOROAD 수집에 필요한 키는 로컬 `.env`에 준비되어 있다. 키를 다시
발급하거나 대화에 전달할 필요가 없다.

## 재현 명령

```powershell
docker compose run --rm jupyter python -m busan_imd.collectors.reference_data
docker compose run --rm jupyter python -m busan_imd.collectors.healthcare_facilities --refresh
docker compose run --rm jupyter python -m busan_imd.collectors.traffic_accidents --refresh
docker compose run --rm jupyter python -m busan_imd.collectors.police_crime --refresh
docker compose run --rm jupyter python -m busan_imd.collectors.fire_incidents --refresh
```

수집 원본은 각각 `data/raw/reference`, `data/raw/public_data_portal/healthcare_facilities`,
`data/raw/koroad/traffic_accidents`에 보존한다. 이 경로는 Git에서 제외한다.

## 2025년 병원·의원·약국 재구성 주의사항

병원·의원·약국 신규 API는 현재 인허가 목록을 제공한다. 수집기는 인허가일, 폐업일, 허가취소일,
휴업 시작·종료일을 사용해 2025-12-31 당시 운영 후보를 재구성한다. 이는 기관이 보관한
2025-12-31 원본 스냅샷과 동일하다고 단정할 수 없으므로 다음 검증 전에는 주 점수에 넣지
않는다.

1. 폐업·취소 이력의 소급 누락 여부 확인
2. 병원 29건, 의원 50건, 약국 19건의 좌표 결측 처리
3. 원본 EPSG:5174 좌표를 기준지리 좌표계로 변환하고 주소와 교차검증
4. 206개 행정동 공간결합률과 미매칭 목록 공개

## 교통사고 자료의 범위

KOROAD 키로 확보한 2025년 자료는 16개 구·군 통계이며, 2024년 다발지역은 시·군·구별
상위 지점만 제공한다. 둘 다 개별 사고 전체 원자료나 행정동 집계가 아니다. 따라서 출처가
확인된 검증·지도 맥락 자료로 보존하되 행정동 안전 점수로 직접 사용하지 않는다. 행정동별
전체 사고 집계는 한국도로교통공단 또는 부산광역시에 별도로 요청한다.

## 보안 원칙

인증키는 `.env`에만 저장하고 GitHub, Linear, Slack, 문서 또는 대화에 붙이지 않는다.
Git에는 출처, 요청조건, 기준기간, 레코드 수와 SHA-256을 담은 manifest만 커밋한다.

## 2026-08-13 추가 수집 결과

이번에 승인된 두 API와 함께 공개 파일 3종을 실제로 조회·보존했다. 상세 URL, 요청조건,
체크섬은 [BUSAN_SUPPLEMENTAL_DATA_MANIFEST.json](../../data/manifests/BUSAN_SUPPLEMENTAL_DATA_MANIFEST.json)에
기록했다.

| 자료 | 실제 확인 결과 | 분석 판단 |
|---|---|---|
| 행정동 연령별 생활인구 | 2023-01~2025-12, 36개월, 206개 동, 44,340행 | 2025년 서비스 수요 보조지표로 사용 가능 |
| 부산 마을버스 운행현황 API | 136개 노선, 기준일은 2023-12-31~2025-12-11 혼재 | 마을버스 보조자료; 부산 전체 버스 운행횟수를 대신할 수 없음 |
| 행정동별 독거노인 API | 원본 241행을 최신 동별 206행으로 정규화 | 기준일 혼재 및 20개 동 기준일·연령내역 누락 때문에 검증용 |
| 교통사고 발생 현황 | 2007~2025년 부산 전체 19행 | 도시 전체 추세 검증용; 동별 안전지표로 사용 불가 |
| 사고위험지역 현황 | 2023년 위험지점 70개 | 공간 검증용; 전체 사고 모집단이 아님 |
| 의원 조회서비스 | 현재 8,649건, 2025-12-31 운영 후보 5,320건 | 병원·약국과 함께 의료접근성 후보 |
| 2025 복지사업 수급권자 | 전국 2,577행, 부산 16개 구·군 포함 | 구·군 합계 검증용; 행정동 자료는 계속 필요 |
| 방범용 CCTV | 2025-12-29 부산 21,060개 위치 | 안전서비스 보조지표; 범죄 건수는 아님 |
| 버스노선별 승하차 | 2023-07-31 노선·정류소 17,088행 | 과거 수요 검증용; 2025 자료 필요 |

생활인구 포털 화면에는 2019~2025년 50,294행으로 안내되어 있으나 실제 다운로드 파일은
2023~2025년 44,340행이다. 따라서 실제 파일의 기간과 행 수를 기준으로 사용한다.

공개 API·파일 키는 로컬 `.env`에 준비되어 있다. 키가 열려도 공간단위나 기준일이
행정동 2025 점수 게이트를 통과하지 못하면 검증·참고로만 둔다. 권한 확보 이후
재검토는 [2025년 데이터 사용 구분표](DATA_USAGE_REGISTER_2025.md)를 따른다.

아직 기관 요청이 필요한 핵심 자료는 행정동별 기초생활보장, 고용·실업, 범죄, 전체
교통사고·화재, 표준화 건강결과·의료이용, 거주지 기준 교육성과, 동일 정의의
빈집·노후주택·과밀가구, 2025-12-31 AED 이력, 전체 시내버스 운행횟수와 부산 전체
폭염·대기 노출자료다. 침수흔적도는 이번 분석 범위에서 제외한다.

## 공공데이터포털 추가 활용신청 우선순위

1. [국토교통부 건축물대장정보 서비스](https://www.data.go.kr/data/15044713/openapi.do):
   사용승인일·주용도·세대수로 노후주택 후보를 만들 수 있다. 법정동 주소를 2025 행정동
   경계에 공간 결합해야 하며 과밀가구는 별도 자료가 필요하다.
2. [소방청 지역별 화재피해 현황](https://www.data.go.kr/data/15142972/openapi.do):
   주소가 읍·면·동까지 있지만 공개기간은 2019~2023년이므로 과거 검증용이다.
3. 완료 — [소방청 화재현황](https://www.data.go.kr/data/15155635/fileData.do):
   활용신청은 완료됐지만 2026-08-14 실제 호출은 HTTP 401을 반환해 권한 전파를 다시
   확인해야 한다. 현재 원문도 2023-12-31 기준이므로 접근 후 부산 과거 패턴 검증용으로만
   사용한다.
4. 완료 — [소방청 화재정보서비스](https://www.data.go.kr/data/15077644/openapi.do):
   2025년 365일을 수집했다. 소방서별 일일 처리요약이며 주소·행정동이 없어 검증 전용이다.
5. [부산 시내버스 업체별 연도별 등록대수](https://www.data.go.kr/data/15043689/fileData.do):
   노선별 투입 차량수 보조자료다. 실제 운행횟수나 배차이력은 아니다.
6. [부산 버스정보안내기 현황](https://www.data.go.kr/data/15034014/openapi.do):
   정류소별 안내설비 접근성을 보완하지만 핵심 지표 우선순위는 낮다.

복지사업 구·군 통계, 부산 방범용 CCTV, 2023 버스 승하차 자료는 파일 다운로드가 가능해
별도 활용신청 없이 이미 수집했다. 범죄 발생건수, 2025 행정동별 화재, 2025 전체 버스
실제 운행횟수는 공공데이터포털의 공개자료만으로 아직 충족되지 않는다.

## 2026-08-25 교육·교통 보강

- 학교알리미 2025년 공시에서 학생 자료 618건, 교원 자료 615건을
  수집했고, 두 공시에 공통인 615개교를 학교 좌표와 결합했다.
- 2025년 활동 교원 24,366명을 기준으로 행정동 중심점 2km 내 교육 공급
  지표를 생성했다. 교원 수는 학교별 관측값이지만 2km 반경 할당은 공간 대리값이다.
- 부산 BIMS에서 현재 노선 290개의 배차간격·첫·막차를 수집했다. API에
  2025년 레코드 기준일이 없어 검증 전용으로 보존하고 2025 점수에는 합산하지 않았다.

```powershell
docker compose exec -T jupyter python -m busan_imd.collectors.school_disclosures
docker compose exec -T jupyter python -m busan_imd.collectors.transit_service
docker compose exec -T jupyter python scripts/rebuild_processed.py
```
