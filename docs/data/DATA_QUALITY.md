# 2025 행정동 후보 프로필 데이터 사전과 품질검사

COD-14는 2025년 부산 206개 행정동 후보 프로필의 컬럼 정의, 출처, 변환식, 결측,
값 범위와 품질 경고를 재현 가능한 산출물로 관리한다.

## 산출물

- 데이터 사전: [DATA_DICTIONARY_2025.csv](DATA_DICTIONARY_2025.csv)
- 품질 리포트: [DATA_QUALITY_REPORT_2025.json](manifests/DATA_QUALITY_REPORT_2025.json)
- 공간·코드 결합 상세: [STANDARDIZATION_REPORT_2025.json](manifests/STANDARDIZATION_REPORT_2025.json)
- 사용 역할: [DATA_USAGE_REGISTER_2025.md](DATA_USAGE_REGISTER_2025.md)
- 탐색 분석: [EDA_2025.md](EDA_2025.md)
- COD-16 지표 전달 결정: [EDA_INDICATOR_DECISIONS_2025.csv](EDA_INDICATOR_DECISIONS_2025.csv)
- COD-16 실행 계약: [DOMAIN_SCORE_SPEC_2025.csv](DOMAIN_SCORE_SPEC_2025.csv)
- 영역 점수 보고서: [DOMAIN_SCORE_REPORT_2025.json](manifests/DOMAIN_SCORE_REPORT_2025.json)
- 종합점수 보고서: [COMPOSITE_INDEX_REPORT_2025.json](manifests/COMPOSITE_INDEX_REPORT_2025.json)

데이터 사전은 후보 프로필의 모든 컬럼에 대해 다음을 기록한다.

- 원천 데이터셋 ID와 기준기간
- 점수 후보·검증·식별자 등 분석 역할
- 단위, 변환 방법, 점수 방향
- 결측 수와 비율, 고유값 수, 수치 범위
- 추정·시차·공간단위 불일치 등 품질 경고

알 수 없는 신규 컬럼에는 자동 설명을 붙이지 않는다. 명세가 없는 컬럼이 프로필에
추가되면 생성 과정이 실패하여 데이터 사전 누락을 방지한다.

## 재생성

raw-data bundle을 복원한 뒤 운영체제와 관계없이 저장소 루트에서 다음을 실행한다.

```bash
docker compose run --rm jupyter python scripts/rebuild_processed.py
```

파이프라인은 다음 순서를 고정한다.

1. 생활인구·학교·대기질·교통 후보자료 가공
2. 소득 추정 입력용 기초 행정동 프로필 생성
3. 2025년 구·군 관측 합계에 맞춘 행정동 소득 대리값 생성
4. 최종 206개 행정동 후보 프로필 재생성
5. 소비매출 검증자료 가공
6. 데이터 사전과 품질 리포트 생성
7. 분포·상관·공간 패턴 EDA와 COD-16 전달 산출물 생성
8. 지표 방향 통일, 백분위 정규화와 영역 내 동일가중 점수 생성
9. 영역 간 기준 가중합, 부산 내부 순위와 10분위 생성

도시공원처럼 현재 등록부인 검증자료는 별도 매니페스트로 관리하며 2025 주 점수
프로필에 자동 결합하지 않는다.

## 현재 품질 판정 원칙

- 관측 0과 결측을 구분한다.
- 구·군 값을 행정동에 반복 배분하지 않는다.
- 추정값은 컬럼명과 행별 계보에 `inferred`를 표시한다.
- 현재 등록부를 2025-12-31 스냅샷으로 표현하지 않는다.
- 검증자료는 결과의 방향·총량 점검에만 사용한다.
- 직접지표와 대리지표가 바뀌면 이전 순위와 직접 비교하지 않는다.
