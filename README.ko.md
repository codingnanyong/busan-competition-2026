# 부산 다중결핍지수(IMD) 분석 프로젝트

[English](README.en.md) | **한국어**

영국의 Index of Multiple Deprivation(IMD) 방법론을 부산 행정동 단위로 재구성하여 생활 취약지역과 영역별 원인을 분석하고, 지역 맞춤형 정책 우선순위를 제안하는 프로젝트입니다.

## 운영 원칙

- 작업 단위는 1:1로 연결된 Linear·GitHub 이슈 쌍으로 관리합니다.
- 모든 구현은 `feat/<linear-id>-<slug>` 브랜치에서 시작합니다.
- `feat/*`는 PR을 통해 `develop`에 병합합니다.
- 릴리스 준비가 끝난 `develop`만 PR을 통해 `main`에 병합합니다.
- `main` 병합 시 `VERSION`을 기준으로 Git 태그와 GitHub Release를 발행합니다.
- 분석 근거, 의사결정, 데이터 사전과 릴리스 변경사항은 국문·영문 문서에 함께 반영합니다.

자세한 일정은 [프로젝트 계획](docs/PROJECT_PLAN.md), 확정된 제출물은 [공모전 제출 요구사항 및 공식 서식](docs/COMPETITION_REQUIREMENTS.md), 실행 환경은 [Docker 기반 분석 환경](docs/DEVELOPMENT_ENVIRONMENT.md), [macOS 이전 안내](docs/MACOS_SETUP.md), [프로젝트 구조](docs/PROJECT_STRUCTURE.md), 실행 항목은 [Linear·GitHub 이슈 맵](docs/ISSUES.md)을 참고하세요. 데이터의 현재 가용성과 향후 확장 조건은 [데이터 가용성 매트릭스](docs/data/AVAILABILITY_MATRIX.md)와 [B-IMD 확장 모델](docs/methodology/EXPANSION_MODEL.md)에서 관리하며, 최신 후보지표 판정은 [2025 EDA](docs/data/EDA_2025.md), 정규화와 영역 점수는 [2025 영역 점수 계산](docs/methodology/DOMAIN_SCORES_2025.md), 종합점수·순위·10분위는 [2025 B-IMD 종합지수](docs/methodology/COMPOSITE_INDEX_2025.md), 결과 안정성은 [2025 민감도 분석](docs/methodology/SENSITIVITY_ANALYSIS_2025.md), 우선지역 원인은 [2025 상위 취약지역·기여도 분석](docs/methodology/PRIORITY_AREAS_2025.md), 유형화 사용 여부는 [2025 취약유형 군집분석 검토](docs/methodology/CLUSTER_ANALYSIS_2025.md), 대기오염 이중부담은 [2025 환경노출 오버레이](docs/methodology/ENVIRONMENTAL_OVERLAY_2025.md), 정책 후보는 [2025 정책 우선순위 매트릭스](docs/methodology/POLICY_MATRIX_2025.md), 제출용 시각화 초안은 [2025 1페이지 인포그래픽](docs/methodology/INFOGRAPHIC_2025.md)에 기록합니다.

추정·대리·보간값을 포함한 3개 큰 카테고리·8개 하위 카테고리의 근거와 신뢰도는 [2025 카테고리 평가](docs/methodology/CATEGORY_ASSESSMENT_2025.md)에서 별도로 관리합니다.

## 목표 산출물

1. 부산 행정동별 다중결핍지수와 영역별 점수
2. 취약지역 유형 및 정책 우선순위
3. 1페이지 데이터 시각화 PDF
4. 분석보고서 HWPX/PDF
5. 재현 가능한 원본·가공 데이터와 분석 코드
6. 현재 공개데이터의 한계와 향후 기관협력 데이터 요청 로드맵

## 분석 지위

B-IMD는 공개데이터로 부산 행정동의 상대적 생활취약성을 탐색하는 실험적 복합지수입니다. 공식 통계, 개인의 박탈 판정 또는 법정 예산배분 기준으로 사용하지 않으며, 직접지표와 대리지표 및 데이터 신뢰도를 결과와 함께 공개합니다.

## 기여와 라이선스

코드와 프로젝트 문서는 [MIT License](LICENSE)입니다. 원천 공개데이터의 이용조건은
각 출처 문서를 따릅니다. 기여 절차는 [CONTRIBUTING.md](CONTRIBUTING.md), 행동 기준은
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), 취약점 신고는 [SECURITY.md](SECURITY.md)를
따릅니다.
