# Git 브랜치 및 PR 정책

## 브랜치 구조

```text
feat/<linear-id>-<slug>
          │ PR (Squash merge, Closes <LINEAR-ID>)
          ▼
       develop
          │ Release PR (Merge commit)
          ▼
        main
          │
          ├─ tag: vX.Y.Z
          ├─ GitHub Release
          └─ docs → GitHub Wiki 동기화
```

초기 저장소를 만들기 위한 첫 커밋만 부트스트랩 예외로 허용합니다. 그 이후 `develop`과 `main` 직접 푸시는 금지합니다.

## 브랜치 이름

- 기능·분석·데이터·문서 작업: `feat/<linear-id>-<slug>`
- 예: `feat/cod-12-data-source-audit`
- 하나의 브랜치는 하나의 Linear 이슈를 닫을 수 있는 크기로 유지합니다.

## PR 규칙

### `feat/* → develop`

- PR 제목: `<LINEAR-ID> <type>: <summary>`
- 본문에 `Closes <LINEAR-ID>`를 포함합니다.
- 분석 결과, 데이터 스키마 또는 사용자 동작이 바뀌면 관련 `docs/`를 같은 PR에서 갱신합니다.
- CI, 재현성 검사와 완료조건을 통과한 뒤 squash merge합니다.

### `develop → main`

- 다른 head 브랜치에서 `main`으로 PR을 만들 수 없습니다.
- `VERSION`, `CHANGELOG.md`, `docs/releases/vX.Y.Z.md`를 반드시 갱신합니다.
- 버전은 기존 태그보다 커야 하며 Semantic Versioning을 사용합니다.
- 병합 후 자동으로 태그와 GitHub Release가 생성됩니다.

## 이슈 완료조건

- 코드 또는 산출물이 저장소에 존재함
- 실행·검증 방법과 결과가 PR에 기록됨
- 관련 문서가 갱신됨
- PR이 `develop`에 병합됨
- Linear 이슈가 PR에 의해 닫히거나 Done으로 동기화됨

## 권장 브랜치 보호 설정

원격 GitHub 저장소 연결 후 다음을 설정합니다.

- `develop`: PR 필수, 상태검사 `PR policy` 필수, 직접 푸시 금지
- `main`: PR 필수, 상태검사 `PR policy` 필수, head=`develop` 제한, 직접 푸시 금지
- force push와 branch deletion 금지
- 대화 해결과 최신 base 반영 필수

