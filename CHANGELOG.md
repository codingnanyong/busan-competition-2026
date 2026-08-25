# Changelog

## [0.6.0] - 2026-08-24

### Added

- 부산 206개 행정동의 취약 특성이 연속적이라는 점을 검증하는 군집분석 검토
- 다중결핍과 대기오염 노출을 함께 살피는 환경 이중부담 분석
- 행정동별 취약 원인을 실행 가능한 정책 예시로 연결하는 정책 우선순위 매트릭스
- 3개 큰 카테고리, 8개 하위 카테고리와 13개 평가지표를 탐색하는 트리형 생활여건 지도
- 추정·대리·보간값의 사용 여부와 사유를 결과 행마다 공개하는 근거·신뢰도 자료
- Clustering review, environmental double-burden overlay, and policy-priority matrix
- Interactive living-condition map spanning three major categories, eight child categories,
  and 13 indicators

### Changed

- `busan_imd` 루트 분석·처리 모듈을 `analysis`와 `processing` 기능 패키지로 재구성하고 문서·노트북 실행 경로를 동기화
- 인포그래픽 단일 모듈을 설정·프로필 계산·렌더링·실행 파이프라인 패키지로 분리하고 기존 공개 API와 CLI 호환성을 유지
- 단일 종합점수 중심의 표현을 카테고리별 점수·근거·정책 방향을 함께 읽는 구조로 확장
- 지도 제목과 설명을 생활여건 진단 목적에 맞게 다듬고 `생활 인프라·주거` 용어를 적용
- 분석 재생성 파이프라인과 국문·영문 방법론을 정책 시각화 단계까지 확장
- Expanded the reproducible pipeline and bilingual methodology through policy visualization

### Fixed

- 명지권 등 신규 개발지역의 교육시설 접근성이 과도하게 취약해 보이지 않도록 보정 근거를 명시
- 카테고리 점수 산출 전에 하위 지표를 평가하도록 계층 구조와 화면 설명을 일치시킴
- Added explicit estimation reasons and aligned the interface with the hierarchical scoring model

## [0.5.0] - 2026-08-23

### Added

- B-IMD 1분위 21개 행정동의 영역·지표별 가중 기여도 분석
- 부산 중앙값 대비 가중 초과점수에 기반한 지역별 대표 취약 원인
- 우선지역 프로필·지표 기여도 CSV와 재현 가능한 체크섬 매니페스트
- Domain- and indicator-level contribution analysis for 21 first-decile B-IMD priority areas
- Area-specific leading drivers based on weighted excess above citywide medians

### Changed

- 전체 로컬 재생성 파이프라인에 우선지역 기여도 분석 단계를 연결
- 국문·영문 방법론에 계산식, 상위지역 결과와 대리지표 해석 한계를 추가
- Extended the offline rebuild and bilingual methodology through priority-area explanations

### Fixed

- 큰 영역 가중치와 지역별 고유 취약 원인을 구분하도록 중앙값 대비 초과 기여도를 함께 제공
- Distinguished mechanical domain-weight effects from area-specific drivers using median-relative contributions

## [0.4.0] - 2026-08-17

### Added

- 2025년 부산 206개 행정동 후보지표 EDA와 재현 가능한 노트북
- 6개 영역의 방향성·백분위 정규화·영역 점수 산출 파이프라인
- B-IMD 종합점수, 부산 내부 순위와 10분위 산출
- 기준가중·동일가중·영역 이용 불가 9개 시나리오 민감도 분석
- PR 병합 후 GitHub·Linear 완료 상태를 검증하는 Slack DM 자동 알림
- Reproducible EDA, six-domain scoring, composite ranks and deciles for 206 Busan dongs
- Nine-scenario weight and domain-availability sensitivity analysis

### Changed

- 전체 로컬 재생성 파이프라인에 EDA, 영역 점수, 종합지수와 민감도 분석 단계를 연결
- 국문·영문 Wiki에 분석 방법론과 결과 안정성 문서를 추가
- Extended the offline rebuild and bilingual Wiki through the sensitivity-analysis stage

### Fixed

- 완료 알림이 GitHub Issue Closed와 Linear Done을 모두 확인한 뒤에만 Slack으로 전송되도록 강화
- Ensured Slack completion notices are sent only after GitHub and Linear both report completion

## [0.3.0] - 2026-08-15

### Added

- Docker 기반 Jupyter 지리공간 분석 환경과 Python 패키지·테스트·품질검사 기반
- 2025년 부산 206개 행정동 경계·기준코드와 출처 메타데이터
- 인구·교통·의료·환경·안전·주거·소득 등 공개데이터 수집기와 재현 매니페스트
- 행정동 코드 매칭, 결측·단위 표준화, 데이터 사전과 품질 리포트
- Docker-based Jupyter geospatial environment with Python packaging, tests, and CI
- Reproducible collectors and manifests for 2025 Busan administrative-dong data

### Changed

- Linear와 GitHub Issues를 1:1 미러로 관리하고 PR 병합 시 완료 상태를 동기화
- 공모전 요구사항, 데이터 가용성, 부산형 IMD 지표·확장 모델 문서 보강
- Mirrored Linear/GitHub issue governance with validated PR completion
- Expanded competition, data-availability, and Busan IMD methodology documentation

### Fixed

- GitHub Wiki에서 깨지던 저장소 상대 링크를 Wiki 또는 원본 파일 URL로 변환
- Converted repository-relative documentation links into valid Wiki or source-file URLs

## [0.2.0] - 2026-08-09

### Added

- 국문·영문 README 및 영문 프로젝트 문서
- 언어별 Wiki 페이지와 공통 사이드바 생성 도구
- Bilingual README and English project documentation
- Language-prefixed Wiki pages and shared navigation

### Fixed

- Wiki가 초기화된 뒤 문서를 안정적으로 동기화하도록 릴리스 워크플로 개선
- Improved the release workflow to publish documentation after Wiki initialization

## [0.1.0] - 2026-08-09

### Added

- 프로젝트 마일스톤과 핵심 이슈 백로그
- Git 브랜치, PR, 이슈 완료 정책
- Semantic Versioning 및 GitHub Release 정책
- PR 정책 검사와 릴리스 자동화 워크플로
