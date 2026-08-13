# 프로젝트 파일 구조

코드, 원본, 출처 기록과 분석 산출물의 책임을 다음과 같이 분리한다.

```text
src/busan_imd/
├─ collectors/   # 데이터셋 단위 실행 진입점; 원본·정규화 CSV·manifest 생성
├─ sources/      # 외부 API URL, 요청 파라미터와 응답 파싱 계약
├─ core/         # HTTP, 설정, 체크섬, 출처 검증 공통 코드
├─ data_catalog.py
└─ standardization.py  # 2025 행정동 공통키·공간결합·단위 표준화
tests/
├─ unit/         # 네트워크와 실제 파일에 의존하지 않는 로직 검사
├─ integration/  # 로컬 원본과 커밋된 manifest의 일관성 검사
└─ smoke/        # Docker 분석환경 패키지 import 검사
data/
├─ raw/          # 변경하지 않는 수집 원본; Git 제외
└─ processed/    # 코드로 재생성하는 분석 입력; Git 제외
docs/data/
├─ manifests/    # 출처·기간·건수·체크섬을 담은 추적 가능한 JSON
└─ *.md, *.csv   # 정책, 감사표, 요청 양식과 기준지리 표
notebooks/       # 탐색 및 설명용 분석
outputs/         # 지도·표·보고서와 전송용 데이터 bundle; Git 제외
scripts/         # 운영체제에 독립적인 보조 명령과 문서 빌드 도구
```

수집기는 외부 서비스별 차이를 직접 구현하지 않고 가능한 한 `sources/` 계약을 사용한다.
인증키는 `.env`에서만 읽는다. `data/raw`는 API 응답과 직접 다운로드 파일을 그대로 보존하고,
수정·통합 결과는 후속 분석 단계에서 `data/processed`에 만든다.

## 실행 규칙

모든 Python 명령은 저장소 루트에서 Docker로 실행한다. 이 방식은 Windows와 macOS에서 같다.

```bash
docker compose run --rm jupyter python -m busan_imd.collectors.fire_incidents
docker compose run --rm jupyter python -m busan_imd.standardization
docker compose run --rm jupyter python -m pytest -q
```

수집기 이름과 원본 위치는 [원본 데이터 수집 문서](data/RAW_DATA_COLLECTION.md), 필요한
자료와 분석 채택 여부는 [데이터 감사표](data/DATASET_AUDIT.csv)를 단일 기준으로 사용한다.
