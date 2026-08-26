# 2025 B-IMD 종합점수·순위·10분위

## 범위와 해석

COD-17은 COD-16에서 생성한 부산 206개 행정동의 6개 영역 점수를 가중합해 실험적
`B-IMD 2025` 종합점수, 부산 내부 순위와 10분위를 산출한다. 종합점수가 높을수록 상대적
생활취약성이 크며, 순위와 10분위는 `1`이 가장 취약하다.

이 결과는 부산 내부의 상대 비교를 위한 공개데이터형 실험 결과다. 공식 통계, 개인 단위
판정, 법정 예산배분 기준 또는 다른 연도·도시와 직접 비교 가능한 절대 점수가 아니다.

## 실행

raw-data bundle을 복원한 저장소 루트에서 전체 파이프라인을 실행한다.

```bash
docker compose run --rm jupyter python scripts/rebuild_processed.py
```

영역 점수 이후 단계만 다시 생성하려면 다음을 실행한다.

```bash
docker compose run --rm jupyter python -m busan_imd.analysis.composite_index
```

실행 계약은 [COMPOSITE_INDEX_SPEC_2025.csv](../data/tables/COMPOSITE_INDEX_SPEC_2025.csv), 입력·출력
체크섬과 요약값은
[COMPOSITE_INDEX_REPORT_2025.json](../data/manifests/COMPOSITE_INDEX_REPORT_2025.json)에
기록한다. 결과 테이블은 Git에서 제외되는
`data/processed/scores/2025/busan_admin_dong_imd_2025.csv`에 생성한다.

## 영역 가중치

기준 가중치는 영국 정부의
[English Indices of Deprivation 2025](https://www.gov.uk/government/statistics/english-indices-of-deprivation-2025/english-indices-of-deprivation-2025-statistical-release)가
공개한 7개 영역 가중치다. 안전 영역은 행정동 직접 사건지표가 없어 보류했으므로, 나머지
6개 영역의 공개 가중치 합 `0.906`을 기준으로 합계가 1이 되도록 재정규화한다.

| B-IMD 영역 | 공개 가중치 | 6개 영역 재정규화 가중치 |
|---|---:|---:|
| 소득 | 22.5% | 24.8344% |
| 고용 | 22.5% | 24.8344% |
| 교육 | 13.5% | 14.9007% |
| 건강 | 13.5% | 14.9007% |
| 주거·서비스 접근 | 9.3% | 10.2649% |
| 생활환경 | 9.3% | 10.2649% |

이 매핑은 영국 지표를 부산 지표와 동일하다고 주장하는 것이 아니라, 사전에 문서화한
재현 가능한 기준선이다. 동일가중과 영역 이용 불가 상황의 순위 안정성은
[2025 민감도 분석](SENSITIVITY_ANALYSIS_2025.md)에서 검증한다.

## 계산 계약

영역 `d`의 0~100 점수를 `domain_score_d`, 재정규화 가중치를 `w_d`라 하면:

```text
B_IMD_score = sum(w_d * domain_score_d)
```

- 종합점수를 내림차순으로 정렬해 `1`부터 `206`까지 순위를 부여한다.
- 종합점수가 같으면 행정동 코드를 오름차순으로 비교해 결과를 결정적으로 유지한다.
- 정렬 순위를 10개 그룹으로 나눠 10분위를 부여한다. `1`은 가장 취약한 약 10%다.
- 206개 행정동 때문에 각 10분위에는 20개 또는 21개 동이 포함된다.

2025 실행 결과 종합점수 범위는 `20.956227`~`82.821838`, 중앙값은 `51.048498`이다.
상위지역의 원인과 영역별 기여도는
[2025 상위 취약지역·기여도 분석](PRIORITY_AREAS_2025.md)에서 해석한다.

## 제한

- 안전 영역이 빠진 6개 영역 기준선이며 완전한 7영역 지수가 아니다.
- 모든 영역에 직접지표 또는 조건부 대리지표의 한계가 남아 있다.
- 순위와 10분위는 작은 점수 차이를 크게 보이게 할 수 있으므로 원점수와 함께 제시한다.
- 동일가중과 영역 이용 불가 시나리오의 변동폭은 민감도 분석 결과와 함께 해석해야 한다.
