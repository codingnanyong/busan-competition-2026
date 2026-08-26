# Git 브랜치 및 PR 정책

## 브랜치 구조

```text
feat/<linear-id>-<slug>
          │ PR (Squash merge)
          │ Closes <LINEAR-ID> + Closes #<GITHUB-ISSUE>
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
- 하나의 브랜치는 1:1로 연결된 Linear·GitHub 이슈 한 쌍을 닫을 수 있는 크기로 유지합니다.

## PR 규칙

### `feat/* → develop`

- PR 제목: `<LINEAR-ID> <type>: <summary>`
- 본문에 `Closes <LINEAR-ID>`와 `Closes #<GITHUB-ISSUE>`를 모두 포함합니다.
- CI는 브랜치·제목·Linear ID가 일치하고 GitHub Issue 제목이 같은 Linear ID로 시작하는지 확인합니다.
- 분석 결과, 데이터 스키마 또는 사용자 동작이 바뀌면 관련 국문·영문 문서를 같은 PR에서 갱신합니다.
- CI, 재현성 검사와 완료조건을 통과한 뒤 squash merge합니다.
- 병합이 완료되면 원격 `feat/*` 브랜치를 즉시 삭제합니다.
- 이슈 종료와 Slack 완료 알림은 [연동 운영 가이드](INTEGRATIONS.md)를 따릅니다.

## 이슈 미러링 규칙

- Linear와 GitHub Issues는 같은 작업을 나타내는 1:1 복사본으로 관리합니다.
- 새 작업은 두 시스템에 같은 제목·설명·우선순위·마일스톤·마감일·담당자로 생성합니다.
- Linear에는 GitHub Issue 링크를, GitHub Issue에는 Linear 링크를 기록합니다.
- 작업 중 설명이나 상태를 바꾸면 같은 작업 세션에서 양쪽을 함께 갱신합니다.
- GitHub Issue는 공개 추적과 PR 자동 종료에 사용하고, Linear는 일정·우선순위·마일스톤 운영에 사용합니다.
- 자동 동기화 실패 시 PR 병합 결과를 기준으로 두 상태를 즉시 맞춥니다.

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
- GitHub Issue가 `completed`로 닫히고 Linear 이슈가 Done으로 동기화됨
- 병합된 원격 작업 브랜치가 삭제됨
- 활성화된 완료 알림이 [연동 운영 가이드](INTEGRATIONS.md)대로 Slack에 전달됨

## GitHub·Linear·Slack 연결 설정

Secret 등록, Linear 이슈 생성, 완료 알림 검증은 [연동 운영 가이드](INTEGRATIONS.md)에만
적습니다. 자격정보는 `.env`, PR 본문, 이슈 또는 로그에 기록하지 않습니다.

## 권장 브랜치 보호 설정

원격 GitHub 저장소 연결 후 다음을 설정합니다.

- `develop`: PR 필수, 상태검사 `PR policy` 필수, 직접 푸시 금지
- `main`: PR 필수, 상태검사 `PR policy` 필수, head=`develop` 제한, 직접 푸시 금지
- 보호 브랜치(`develop`, `main`)의 force push와 삭제 금지
- 병합된 작업 브랜치(`feat/*`)는 자동 또는 수동으로 삭제
- 대화 해결과 최신 base 반영 필수
