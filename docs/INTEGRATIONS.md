# GitHub·Linear·Slack 연동 운영 가이드

## 자동화 범위

`feat/* → develop` PR이 병합되면 `PR policy` 워크플로가 다음 순서로 동작합니다.

1. PR 본문의 `Closes COD-n`과 `Closes #n` 쌍을 확인합니다.
2. 미러 GitHub Issue를 `completed`로 닫습니다.
3. Linear GitHub 연동이 Linear 이슈를 Done으로 변경할 때까지 최대 2분 동안 확인합니다.
4. 두 이슈의 완료가 확인된 경우에만 PR·병합 커밋·GitHub·Linear 링크를 Slack에 전송합니다.

Linear 완료 또는 Slack 전송이 실패하면 성공 메시지는 전송되지 않으며 해당 Actions 작업이 실패합니다.
병합이 끝난 PR은 Linear가 GitHub PR을 다시 수정해도 정책 검사를 반복하지 않습니다. 그때는 미러
GitHub Issue가 이미 닫혀 있어, 병합 전 열림 검사를 다시 하면 거짓 실패 알림이 납니다.

## 최초 1회 외부 설정

### 1. Linear API 키

Linear의 **Settings → Security & access → Personal API keys**에서 키를 생성합니다. `COD` 팀의 이슈와 상태를 읽을 수 있는 계정의 키가 필요합니다.

GitHub 저장소 **Settings → Secrets and variables → Actions → Secrets**에 다음 이름으로 저장합니다.

```text
LINEAR_API_KEY
```

### 2. Slack Incoming Webhook

Slack 앱에서 Incoming Webhooks를 활성화하고 완료 알림을 받을 대상 대화를 선택합니다. 생성된 URL을 GitHub Actions Secret으로 저장합니다.

```text
SLACK_WEBHOOK_URL
```

Webhook은 선택한 대화에만 게시할 수 있어야 합니다. 개인 DM을 대상으로 선택할 수 없는 워크스페이스 정책이면 전용 비공개 채널을 만들고 본인과 Slack 앱만 참여시킵니다.

### 3. 자동화 활성화

두 Secret을 등록한 다음 GitHub 저장소 **Settings → Secrets and variables → Actions → Variables**에 다음 값을 추가합니다.

```text
COMPLETION_NOTIFICATIONS_ENABLED=true
```

CLI를 사용할 경우 비밀값을 명령줄 인자에 직접 넣지 않고 표준 입력으로 등록합니다.

```bash
gh secret set LINEAR_API_KEY --repo codingnanyong/busan-competition-2026
gh secret set SLACK_WEBHOOK_URL --repo codingnanyong/busan-competition-2026
gh variable set COMPLETION_NOTIFICATIONS_ENABLED --body true \
  --repo codingnanyong/busan-competition-2026
```

## 필요한 권한

- GitHub: 저장소 Actions Secret과 Variable을 관리할 수 있는 관리자 권한
- Linear: 개인 API 키 생성 권한과 `COD` 팀 이슈 읽기 권한
- Slack: 앱 설치 또는 Incoming Webhook 추가 권한, 대상 대화에 앱을 추가할 권한
- Linear GitHub 연동: `develop` 병합 시 연결된 Linear 이슈를 Done으로 바꾸는 팀 워크플로 자동화

## 검증 및 장애 처리

1. 시험용 미러 이슈 쌍과 PR을 생성합니다.
2. PR을 `develop`에 병합합니다.
3. GitHub Issue Closed와 Linear Done을 확인합니다.
4. Actions의 `notify-completion` 성공과 Slack 메시지의 네 링크를 확인합니다.

알림 작업이 실패하면 Actions 로그에는 비밀값이 아닌 누락된 설정 또는 미완료 상태만 표시됩니다. Secret이 준비되기 전에는 Variable을 생성하지 않거나 `false`로 유지합니다. 자동화가 비활성화된 동안에는 병합을 수행한 작업 세션에서 두 이슈 상태를 확인하고 Slack에 직접 공유합니다.

## Linear 이슈 생성

새 COD 이슈는 `Create Linear issue` 워크플로로 만듭니다. 팀 `COD`와 프로젝트
[부산 IMD 생활취약지역 분석 2026](https://linear.app/codingnanyong/project/부산-imd-생활취약지역-분석-2026-83133e455764)을
함께 지정하며, 프로젝트를 찾지 못하면 이슈를 만들지 않습니다.

```bash
gh workflow run create-linear-issue.yml --ref develop \
  -f title="작업 제목" \
  -f description="목표와 완료조건"
```

워크플로가 `main`에 올라오기 전에는 `--ref develop`이 필요합니다.
