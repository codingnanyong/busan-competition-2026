# Docker 기반 분석 환경

이 문서는 부산 IMD 분석에 사용하는 JupyterLab 및 Python 지리공간 분석 환경의 실행·검증 방법을 설명합니다.

## 구성

- Python 3.12
- JupyterLab
- pandas, GeoPandas, scikit-learn, Plotly
- Ruff 기반 lint
- pytest 기반 smoke test와 프로젝트 구조 검사

패키지 버전은 `requirements.txt`에 고정합니다. GeoPandas가 사용하는 Shapely, pyproj 등 하위 패키지는 Linux wheel을 사용하므로 별도 GDAL 개발 도구를 이미지에 설치하지 않습니다.

## 실행

저장소 루트에서 다음 명령을 실행합니다.

```bash
docker compose build
docker compose up -d
docker compose ps
```

브라우저에서 `http://localhost:8888/lab`을 엽니다. 로컬 개발 전용 구성이므로 토큰 인증은 비활성화되어 있습니다. 외부 네트워크에 포트를 공개하지 마십시오.

포트가 이미 사용 중이면 다음처럼 변경합니다.

```bash
JUPYTER_PORT=8890 docker compose up -d
```

PowerShell에서는 다음을 사용합니다.

```powershell
$env:JUPYTER_PORT = "8890"
docker compose up -d
```

## 프로젝트 구조

```text
data/
├─ raw/          # 원본 데이터, 직접 수정 금지
└─ processed/    # 재현 가능한 코드로 생성한 가공 데이터
notebooks/       # 탐색 및 분석 노트북
outputs/         # 생성된 표, 그림, 지도와 제출 후보 산출물
src/busan_imd/   # 재사용 가능한 Python 분석 코드
tests/           # 환경, 구조와 분석 코드 테스트
```

세부 디렉터리 책임은 [프로젝트 파일 구조](PROJECT_STRUCTURE.md), 다른 컴퓨터로의 원본
이전과 macOS 실행은 [macOS 작업환경 이전](MACOS_SETUP.md)을 참고합니다.

`data/raw`, `data/processed`, `outputs`의 실제 파일은 기본적으로 Git과 Docker build context에서 제외합니다. 데이터 출처와 라이선스는 `docs/data`에 기록하고, 재현에 필요한 소형 공개 산출물만 후속 이슈에서 명시적으로 추적합니다.

## 품질검사

수집된 원본을 2025년 기준 206개 행정동 후보 프로파일로 가공하고 검증 보고서를
재생성하려면 다음을 실행합니다.

```bash
docker compose run --rm jupyter python -m busan_imd.standardization
```

세부 규칙과 현재 매칭 결과는 [2025 행정동 데이터 표준화와 검증](data/STANDARDIZATION.md)에
기록합니다.

전체 Python lint와 테스트를 컨테이너에서 실행합니다.

```bash
docker compose run --rm jupyter python -m ruff check .
docker compose run --rm jupyter python -m pytest -v
```

필수 라이브러리 import만 빠르게 확인하려면 다음 smoke test를 실행합니다.

```bash
docker compose run --rm jupyter python -m pytest tests/smoke/test_environment.py -v
```

Ruff와 pytest 설정은 `pyproject.toml`에서 관리하며, pull request와 `develop` push에서도 동일한 검사를 실행합니다.

실행 중인 서비스 상태는 다음 명령으로 확인합니다.

```bash
docker compose ps
docker compose logs jupyter
```

작업을 마치면 컨테이너를 종료합니다.

```bash
docker compose down
```

## 데이터 보존

저장소 전체가 `/workspace`에 bind mount되므로 notebook과 코드 변경은 호스트에 바로 저장됩니다. 원천·가공 데이터와 출력물은 기본적으로 Git 및 Docker build context에서 제외합니다.
