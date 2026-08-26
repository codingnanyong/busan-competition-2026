# 버전·릴리스·문서 정책

## 버전 규칙

Semantic Versioning(`MAJOR.MINOR.PATCH`)을 사용합니다.

- MAJOR: 분석 방법론 또는 제출물 계약의 호환되지 않는 변경
- MINOR: 새로운 데이터 영역, 분석 기능, 시각화 또는 정책 모듈 추가
- PATCH: 오류 수정, 데이터 정정, 문서 개선

## 릴리스 절차

1. `develop`에서 릴리스 후보를 검증합니다.
2. `VERSION`을 올립니다.
3. `CHANGELOG.md`와 `docs/kor/releases/vX.Y.Z.md`, `docs/eng/releases/vX.Y.Z.md`를 갱신합니다.
4. `develop → main` PR을 생성하고 승인·병합합니다.
5. GitHub Actions가 `vX.Y.Z` 태그와 GitHub Release를 생성합니다.
6. 최신 국문·영문 문서를 GitHub Wiki에 동기화합니다.
7. Linear 마일스톤과 Linear·GitHub 미러 이슈를 완료 처리하고 Slack에 릴리스 결과를 공유합니다.

`main`의 각 병합은 하나의 고유 버전을 가져야 합니다. 이미 존재하는 태그의 버전이면 릴리스 작업은 실패합니다.

## 국문·영문 문서 체계

- `README.md`: 한·영 언어 선택과 공통 개요
- `README.ko.md`: 국문 프로젝트 홈
- `README.en.md`: 영문 프로젝트 홈
- `docs/kor/`: 국문 문서. 계획·워크플로·데이터 설명·방법·릴리스 노트를 둔다
- `docs/eng/`: 영문 대응 문서
- `docs/data/tables/`, `docs/data/manifests/`: 언어에 묶이지 않는 표와 체크섬. 파이프라인이 다시 씀
- `docs/templates/`: 제출 서식

Wiki는 `KO-*`, `EN-*` 페이지와 공통 `_Sidebar.md`를 생성합니다. 번역이 필요하지 않은 변경은 PR에 그 이유를 명시하고, 그 외 문서 변경은 국문과 영문을 함께 갱신해야 완료로 인정합니다.
