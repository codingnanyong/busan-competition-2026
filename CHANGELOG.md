# Changelog

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
