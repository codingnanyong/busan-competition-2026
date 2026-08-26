# Contributing

[한국어](#한국어) | [English](#english)

## 한국어

이 저장소는 부산 행정동 B-IMD 공모전 분석 코드와 문서입니다. 코드 변경은
아래 절차를 따릅니다. 상세 규칙은 [Git 워크플로](docs/kor/GIT_WORKFLOW.md)와
[분석 환경](docs/kor/DEVELOPMENT_ENVIRONMENT.md)을 따릅니다.

### 시작하기

1. 작업을 Linear·GitHub 미러 이슈 한 쌍으로 만듭니다. Linear 생성은
   [연동 운영 가이드](docs/kor/INTEGRATIONS.md)를 따릅니다.
2. `feat/<linear-id>-<slug>` 브랜치에서 구현합니다. 예: `feat/cod-12-data-source-audit`.
3. `develop`과 `main`에는 직접 푸시하지 않습니다.
4. 분석 명령은 저장소 루트에서 Docker로 실행합니다.

```bash
docker compose run --rm jupyter python -m pytest -q
```

### 풀 리퀘스트

- 대상 브랜치는 `develop`입니다. 릴리스만 `develop → main`입니다.
- 제목: `<LINEAR-ID> <type>: <summary>`
- 본문에 `Closes COD-n`과 `Closes #n`을 함께 넣습니다.
- 분석 결과·데이터 계약·화면이 바뀌면 국문·영문 문서를 같은 PR에서 고칩니다.
- CI와 완료조건을 통과한 뒤 squash merge합니다.

커밋하지 않는 것: `.env`, API 키, `data/raw/`, `data/processed/`,
개인이 식별되는 원본. 출처와 체크섬은 `docs/data/`에만 남깁니다.

행동 기준은 [행동 강령](CODE_OF_CONDUCT.md), 취약점 신고는
[보안 정책](SECURITY.md)을 따릅니다.

## English

This repository holds the Busan administrative-dong B-IMD analysis code and
docs. Follow [Git workflow](docs/eng/GIT_WORKFLOW.md) and the
[development environment](docs/eng/DEVELOPMENT_ENVIRONMENT.md).

### Start

1. Create one mirrored Linear/GitHub issue pair. Create Linear issues with the
   [integration operations guide](docs/eng/INTEGRATIONS.md).
2. Work on `feat/<linear-id>-<slug>`. Example: `feat/cod-12-data-source-audit`.
3. Do not push directly to `develop` or `main`.
4. Run Python from the repository root in Docker.

```bash
docker compose run --rm jupyter python -m pytest -q
```

### Pull requests

- Open feature PRs against `develop`. Only release PRs go `develop → main`.
- Title: `<LINEAR-ID> <type>: <summary>`
- Include both `Closes COD-n` and `Closes #n` in the body.
- Update Korean and English docs in the same PR when results, data contracts,
  or the dashboard change.
- Squash merge after CI and acceptance checks pass.

Do not commit `.env`, API keys, `data/raw/`, `data/processed/`, or identifiable
source extracts. Record provenance and checksums under `docs/data/` only.

See the [code of conduct](CODE_OF_CONDUCT.md) and [security policy](SECURITY.md).
