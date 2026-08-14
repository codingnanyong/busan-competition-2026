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
```

`.env`에 기존 API 키를 직접 입력하되 Git에 추가하지 않는다. Docker build context에서도
`.env`는 제외되어 이미지에 들어가지 않는다.

## 2. Google Drive에서 2025 원본 복원

`data/raw`는 출처별 원본이라 Git에서 제외된다. 2025 분석에 사용한 고정 원본은 다음
Google Drive 폴더에서 관리한다.

- `내 드라이브/Developer/Project/busan-competition-2026/raw-data/2025`
- [Google Drive 프로젝트 원본 폴더](https://drive.google.com/drive/folders/14zP8Kjoz669QiX-TFET5YEMNWgeFgq1V)

Google Drive for desktop에서 위 폴더를 동기화한 뒤 번들 절대 경로를 `.env`에 지정한다.

```dotenv
BUSAN_IMD_RAW_BUNDLE=/Users/<사용자>/Library/CloudStorage/GoogleDrive-<계정>/My Drive/Developer/Project/busan-competition-2026/raw-data/2025/busan-imd-raw-data-2025.tar.gz
```

경로를 지정하지 않아도 표준 macOS Google Drive 동기화 경로는 자동 탐색한다. 복원과
가공은 다음 한 명령으로 실행한다.

```bash
docker compose run --rm jupyter python -m scripts.bootstrap_data prepare
```

기존 `data/raw`를 의도적으로 교체할 때만 `--replace`를 추가한다.

### Windows에서 원본 번들 갱신

Windows 저장소 루트에서 다음 명령으로 압축한다.

```powershell
docker compose run --rm jupyter python scripts/data_bundle.py export
```

생성된 `outputs/busan-imd-raw-data.tar.gz`와 `.sha256` 파일은 체크섬을 확인한 뒤 Google
Drive의 위 경로에 `busan-imd-raw-data-2025.tar.gz` 이름으로 보관한다.

### API와 공개 페이지에서 재수집

`.env`를 채운 다음 2025 또는 명시된 과거 기준기간을 다시 조회할 수 있는 소스만 자동
수집한다.

```bash
docker compose run --rm jupyter python -m scripts.bootstrap_data collect-network
docker compose run --rm jupyter python -m scripts.bootstrap_data rebuild
```

전체 네트워크 원본을 강제로 다시 받을 때는 `collect-network --refresh`를 사용한다. API가
현재 상태만 반환하는 AED·버스정류소·도시공원·마을버스·독거노인은 이 명령에서 의도적으로
제외한다. 다시 호출하면 2025 스냅샷이 아니라 실행일 현재 값이 되기 때문이다.

`git clone`만으로는 분석 데이터가 복구되지 않는다. raw bundle을 가져오거나 모든 수동
원본을 다시 받아야 하며, 그 뒤 `scripts/rebuild_processed.py`가 운영체제 공통 순서로
`data/processed`와 품질 리포트를 재생성한다. 소비매출의 분석용 CSV 복사본도 raw bundle에
포함되므로 Windows Excel이 없는 Mac에서 다시 변환할 필요가 없다.

데이터셋별 API 재수집 여부와 Drive 보존 이유는
[2025 데이터 이전 정책](data/DATA_PORTABILITY.md)에 기록한다.

## 3. macOS 확인 사항

- Docker Desktop의 파일 공유 권한에서 저장소와 Google Drive 동기화 폴더 접근을 허용한다.
- Apple Silicon에서도 기본 multi-architecture Python 이미지를 사용하므로 `platform`을
  강제로 지정하지 않는다.
- 포트 충돌 시 `JUPYTER_PORT=8890 docker compose up -d`처럼 변경한다.
- 코드와 notebook은 bind mount되어 Mac 파일시스템에 즉시 저장된다.
