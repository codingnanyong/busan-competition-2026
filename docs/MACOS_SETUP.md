# macOS 작업환경 이전

현재 Docker 구성은 Linux 컨테이너에서 실행되므로 Windows 전용이 아니다. Intel Mac과
Apple Silicon Mac 모두 동일한 `compose.yaml`과 `Dockerfile`을 사용한다. 호스트에 Python,
GDAL 또는 GeoPandas를 별도로 설치할 필요는 없다.

## 1. 코드 받기

Docker Desktop과 Git을 설치한 뒤 macOS 터미널에서 실행한다.

```bash
git clone https://github.com/codingnanyong/busan-competition-2026.git
cd busan-competition-2026
cp .env.example .env
docker compose build
docker compose run --rm jupyter python -m pytest -q
docker compose up -d
```

`.env`에 기존 API 키를 직접 입력하되 Git에 추가하지 않는다. Docker build context에서도
`.env`는 제외되어 이미지에 들어가지 않는다.

## 2. 원본 데이터 옮기기

`data/raw`는 출처별 원본이라 Git에서 제외된다. 따라서 Git clone만으로는 Windows에서
수집한 원본이 Mac에 내려오지 않는다. 다음 중 하나를 선택한다.

### 기존 원본을 그대로 이전

Windows 저장소 루트에서 다음 명령으로 압축한다.

```powershell
docker compose run --rm jupyter python scripts/data_bundle.py export
```

생성된 `outputs/busan-imd-raw-data.tar.gz`와 `.sha256` 파일을 Mac으로 옮긴 후 저장소
루트에서 복원한다.

```bash
docker compose run --rm jupyter python scripts/data_bundle.py import \
  outputs/busan-imd-raw-data.tar.gz
```

복원 대상에 기존 파일이 있으면 기본적으로 중단한다. 의도적으로 덮을 때만 `--replace`를
붙인다.

### 공개 API에서 재수집

`.env`를 채운 다음 필요한 `collectors` 모듈을 실행한다. 단, MOIS 주민등록인구처럼 웹에서
수동 다운로드한 원본은 API로 자동 복구되지 않으므로 bundle 이전이 필요하다.

## 3. macOS 확인 사항

- Docker Desktop의 파일 공유 권한에서 저장소 폴더 접근을 허용한다.
- Apple Silicon에서도 기본 multi-architecture Python 이미지를 사용하므로 `platform`을
  강제로 지정하지 않는다.
- 포트 충돌 시 `JUPYTER_PORT=8890 docker compose up -d`처럼 변경한다.
- 코드와 notebook은 bind mount되어 Mac 파일시스템에 즉시 저장된다.
