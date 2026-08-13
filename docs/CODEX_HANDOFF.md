# Codex 작업 인계

마지막 갱신: 2026-08-11 (Asia/Seoul)

## 현재 상태

- 작업 브랜치: `feat/cod-7-project-scaffold`
- 기준 브랜치: `origin/develop`
- 기준 커밋: `8e771cd` (`Merge pull request #6 from codingnanyong/feat/cod-6-docker-jupyter`)
- Linear 프로젝트: `부산 IMD 생활취약지역 분석 2026`
- 현재 이슈: `COD-7 분석 프로젝트 디렉터리와 기본 품질검사 구성` (`In Progress`)
- 저장소에 `AGENTS.md`는 없음
- 로컬 `.env`의 내용은 읽거나 출력하거나 커밋하지 않음

이 문서는 작업 시점의 스냅샷이다. 문서와 실제 Git·Linear·테스트 상태가 다르면 실제 상태를 우선한다.

## 완료된 기반 작업

- COD-5: 저장소 브랜치·PR·릴리스·문서 정책 확정
- COD-6: Docker 기반 Jupyter 지리공간 분석 환경 구성
- COD-8: 공모전 공고·제출서식·평가기준 확정
- COD-9: 부산형 IMD 영역·지표·가중치 명세 작성

COD-6은 `develop`에 병합되었고 Windows Docker Desktop에서 다음을 검증했다.

| 검증 | 결과 |
|---|---|
| `docker compose config --quiet` | 통과 |
| `docker compose build` | `busan-imd-jupyter:dev` 빌드 성공 |
| `docker compose up -d --wait` | Jupyter 서비스 `healthy` |
| 환경 smoke test | `tests/smoke/test_environment.py` 통과 |

## COD-7 진행 내용

- `data/raw`, `data/processed`, `notebooks`, `outputs`, `src/busan_imd`, `tests` 구조 추가
- 원본·가공 데이터와 생성 산출물의 Git 및 Docker build context 제외 정책 확정
- `pyproject.toml`에 Python 3.12용 Ruff·pytest 설정 추가
- `requirements.txt`에 Ruff 버전 고정
- 프로젝트 구조 회귀 테스트 추가
- `src` 레이아웃을 위한 `PYTHONPATH=/workspace/src` 적용
- pull request와 `develop` push에서 실행되는 Python 품질검사 workflow 추가
- 국문·영문 개발환경 문서에 구조와 lint/test 명령 기록

현재 검증 결과:

| 검증 | 결과 |
|---|---|
| `docker compose config --quiet` | 통과 |
| `docker compose build` | 통과 |
| `python -m ruff check .` | 통과 |
| `python -m pytest -v` | 2개 통과 |
| `git diff --check` | 통과 |

## 다음 작업 순서

1. COD-7 변경사항과 문서를 최종 검토한다.
2. 최신 이미지로 Jupyter 서비스를 재생성하고 healthcheck를 확인한다.
3. COD-7 검증 결과를 Linear에 기록한다.
4. 사용자 승인 후 변경사항을 커밋하고 원격 브랜치에 푸시한다.
5. `feat/cod-7-project-scaffold`에서 `develop` 대상 PR을 만들고 `Closes COD-7`을 포함한다.
6. CI 통과 후 squash merge하고 Linear COD-7을 Done으로 동기화한다.
7. 다음 미완료 이슈 `COD-10 영역별 행정동 데이터 가용성 감사`를 시작한다.

## 실행 명령

```bash
docker compose build
docker compose up -d --wait
docker compose ps
docker compose run --rm jupyter python -m ruff check .
docker compose run --rm jupyter python -m pytest -v
```

작업 종료 시:

```bash
docker compose down
```

## 설계 및 안전 원칙

- 분석 환경은 Docker Compose를 기준으로 재현한다.
- 재사용 코드는 `src/busan_imd`, 탐색 작업은 `notebooks`, 검증은 `tests`에 둔다.
- 원본 데이터는 직접 수정하지 않고 가공 데이터는 코드로 재생성할 수 있어야 한다.
- 데이터 출처·기준기간·라이선스·수집방법은 `docs/data`에 기록한다.
- Jupyter 인증이 비활성화되어 있으므로 `127.0.0.1` 포트 바인딩을 유지한다.
- 인증정보, `.env` 내용, 개인 장비별 Codex 설정은 저장소에 기록하지 않는다.
- 구현은 `feat/<linear-id>-<slug>` 브랜치에서 진행하고 `develop` 대상 PR로 병합한다.
- commit, push, PR, merge는 각각 사용자의 명시적 요청 또는 승인 범위에서 수행한다.
