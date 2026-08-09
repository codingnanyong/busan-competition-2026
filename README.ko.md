# 부산 다중결핍지수(IMD) 분석 프로젝트

[English](README.en.md) | **한국어**

영국의 Index of Multiple Deprivation(IMD) 방법론을 부산 행정동 단위로 재구성하여 생활 취약지역과 영역별 원인을 분석하고, 지역 맞춤형 정책 우선순위를 제안하는 프로젝트입니다.

## 운영 원칙

- 작업 단위는 Linear 이슈로 관리합니다.
- 모든 구현은 `feat/<linear-id>-<slug>` 브랜치에서 시작합니다.
- `feat/*`는 PR을 통해 `develop`에 병합합니다.
- 릴리스 준비가 끝난 `develop`만 PR을 통해 `main`에 병합합니다.
- `main` 병합 시 `VERSION`을 기준으로 Git 태그와 GitHub Release를 발행합니다.
- 분석 근거, 의사결정, 데이터 사전과 릴리스 변경사항은 국문·영문 문서에 함께 반영합니다.

자세한 일정은 [프로젝트 계획](docs/PROJECT_PLAN.md), 실행 항목은 [Linear 이슈 맵](docs/ISSUES.md), 개발 방식은 [Git 워크플로](docs/GIT_WORKFLOW.md), 릴리스 방식은 [릴리스 정책](docs/RELEASE_POLICY.md)을 참고하세요. 데이터의 현재 가용성과 향후 확장 조건은 [데이터 가용성 매트릭스](docs/data/AVAILABILITY_MATRIX.md)와 [B-IMD 확장 모델](docs/methodology/EXPANSION_MODEL.md)에서 관리합니다.

## 목표 산출물

1. 부산 행정동별 다중결핍지수와 영역별 점수
2. 취약지역 유형 및 정책 우선순위
3. 1페이지 데이터 시각화 PDF
4. 분석보고서 HWPX/PDF
5. 재현 가능한 원본·가공 데이터와 분석 코드
6. 현재 공개데이터의 한계와 향후 기관협력 데이터 요청 로드맵

## 분석 지위

B-IMD는 공개데이터로 부산 행정동의 상대적 생활취약성을 탐색하는 실험적 복합지수입니다. 공식 통계, 개인의 박탈 판정 또는 법정 예산배분 기준으로 사용하지 않으며, 직접지표와 대리지표 및 데이터 신뢰도를 결과와 함께 공개합니다.
