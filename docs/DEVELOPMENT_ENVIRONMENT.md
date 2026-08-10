# Docker 기반 분석 환경

이 문서는 부산 IMD 분석에 사용하는 JupyterLab 및 Python 지리공간 분석 환경의 실행·검증 방법을 설명합니다.

## 구성

- Python 3.12
- JupyterLab
- pandas, GeoPandas, scikit-learn, Plotly
- pytest 기반 smoke test

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

## 검증

필수 라이브러리 import와 간단한 GeoDataFrame/Plotly 생성을 함께 확인합니다.

```bash
docker compose run --rm jupyter python -m pytest tests/test_environment.py -v
```

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

저장소 전체가 `/workspace`에 bind mount되므로 notebook과 코드 변경은 호스트에 바로 저장됩니다. 원천·가공 데이터와 출력물은 기본적으로 Docker build context에서 제외하며, 각 디렉터리의 Git 추적 정책은 후속 프로젝트 구조 이슈에서 확정합니다.
