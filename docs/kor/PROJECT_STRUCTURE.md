# 프로젝트 파일 구조

각 폴더는 **한 가지 책임**만 갖는다. 같은 파일을 `src`와 `outputs`에 두지 않는다.

## 한 줄 정의

| 위치 | 의미 | 직접 수정 | 파이프라인이 다시 씀 |
|---|---|---|---|
| `data/raw/` | 수집한 원본. 분석 입력의 출발점 | 수집기만 추가. 손으로 고치지 않음 | 수집기가 새 원본을 넣음 |
| `data/processed/` | 원본을 행정동 단위로 맞춘 분석 입력 | 손으로 고치지 않음 | `processing`이 재생성 |
| `src/busan_imd/` | 수집·가공·분석·산출물 생성 **코드** | Python만 수정 | 해당 없음 |
| `outputs/` | 사람이 보는 표·그림·대시보드 | 화면 파일은 여기만 수정 | 생성 파일은 덮어씀 |
| `docs/` | 방법·출처·체크섬·계획 | 문서와 `docs/data/tables/` CSV | `docs/data/manifests/`는 재생성 |
| `tests/` | 코드와 산출물이 계약을 지키는지 검사 | 테스트만 수정 | 해당 없음 |
| `notebooks/` | 탐색용. 제출 산출물의 원본이 아님 | 노트북 수정 | 해당 없음 |
| `scripts/` | 저장소 루트에서 도는 보조 명령 | 스크립트 수정 | 해당 없음 |

흐름은 항상 같다.

```text
수집(src/collectors) → data/raw
  → 가공(src/processing) → data/processed
      → 분석(src/analysis) → docs/data/manifests + 점수 CSV
      → 시각화(src/infographic) → outputs/infographic/2025
        → 제출초안(src/submission) → outputs/submission/2025
```

## 디렉터리 나무

```text
src/busan_imd/
├─ collectors/     # 외부 자료를 data/raw 와 docs/data/manifests 로 가져옴
├─ sources/        # API 주소·요청·응답 파싱 계약. 수집기가 여기를 씀
├─ core/           # HTTP, 설정, 체크섬 등 공통 유틸
├─ processing/     # data/raw → data/processed (표준화·추정·품질)
├─ analysis/       # 영역점수·종합지수·민감도·군집·정책 후보
├─ infographic/    # 이미 만든 점수를 PDF·지도·대시보드로 내보냄. 화면 파일이 아님
   ├─ config.py
   ├─ application/     # 입력 경로를 모아 생성 순서를 실행
   ├─ domain/          # 동별 개선방향 등 표시용 표 계산
   └─ presentation/    # PDF 렌더, 대시보드 HTML에 지도·점수를 채워 넣음
      └─ dashboard/    # assemble.py 만. HTML/CSS/JS 원본은 여기 없음
└─ submission/     # 재배포 가능한 표와 보고서 초안을 공모전 폴더로 모음

data/
├─ raw/            # 원본 보존. Git 제외
└─ processed/      # 재생성 가능한 분석 입력. Git 제외
   ├─ candidates/  ├─ scores/  ├─ standardized/  └─ bootstrap/

outputs/
├─ eda/            # EDA 중간 표. Git 제외
├─ infographic/2025/                 # 제출·검토용 시각화. Git에 둠
   ├─ static/                        # 1페이지 PDF·SVG·PNG. 파이프라인이 다시 그림
   ├─ tables/                        # 동별 점수·프로필 CSV. 파이프라인이 다시 씀
   └─ interactive/                   # 브라우저 대시보드. 화면 수정은 여기
      ├─ html/                       # 안내·트리·지도 껍데기·근거·정책 조각. 직접 수정
      ├─ css/                        # 레이아웃·오버레이·근거·정책 스타일. 직접 수정
      ├─ js/                         # 지도·근거·정책·부팅 스크립트. 직접 수정
      │  └─ data.js                  # 동별 점수 JSON. 파이프라인이 다시 씀. 직접 고치지 않음
      └─ busan_admin_dong_action_map_2025.html
                                     # html/ 조각을 합치고 지도를 넣은 결과. 이 파일을 연다
                                     # 직접 고치면 다음 생성에서 덮어씀
└─ submission/2025/                  # 공모전 압축 초안. 파이프라인이 다시 모음
   ├─ 01_data-visualization.pdf      # 1페이지 PDF 복사본
   ├─ 02_analysis-report.pdf         # 표지+본문. 본문 10페이지 이하
   ├─ 02_analysis-report.md          # HWPX에 붙여 넣을 본문
   └─ 03_data/                       # 출처 목록·데이터 사전·파생 CSV. 원천 없음

docs/
├─ kor/            # 국문 문서
│  ├─ data/        # 데이터 정책·요청 설명
│  ├─ methodology/ # 점수·정책·인포그래픽·제출 초안 방법
│  └─ releases/    # 버전별 릴리스 설명
├─ eng/            # 영문 대응 문서
├─ data/           # 언어에 묶이지 않는 표와 체크섬
│  ├─ tables/      # 감사표·명세·카탈로그 CSV
│  └─ manifests/   # 입력·출력 체크섬 JSON. 파이프라인이 다시 씀
└─ templates/      # 문서·요청 서식

tests/
├─ unit/           # 네트워크·실제 산출물 없이 로직만 검사
├─ integration/    # 커밋된 원본·manifest·산출물 계약 검사
└─ smoke/          # Docker 이미지에서 패키지 import 검사

notebooks/         # 설명용 탐색. 제출 파일의 원본이 아님
scripts/           # bootstrap, 문서 빌드 등 보조 명령
```

## 대시보드만 따로

화면을 바꾸려면 `outputs/infographic/2025/interactive/`만 고친다.

| 파일 | 의미 | 수정 |
|---|---|---|
| `html/guide.html` | 이용 방법·점수 산정 안내 | 직접 |
| `html/tree.html` | 왼쪽 평가항목 트리 껍데기 | 직접 |
| `html/map.html` | 지도·오버레이 버튼 껍데기 | 직접 |
| `html/detail.html` | 오른쪽 근거 패널 초기 문구 | 직접 |
| `html/policy_panel.html` | 하단 정책 패널 초기 문구 | 직접 |
| `html/document.html` | 위 조각을 끼워 넣는 문서 뼈대 | 직접 |
| `css/*.css` | 화면 모양 | 직접 |
| `js/map.js` `evidence.js` `policy.js` `overlays.js` `boot.js` | 클릭·색·정책 판단 | 직접 |
| `js/data.js` | 206개 동 점수 데이터 | `python -m busan_imd.infographic` |
| `busan_admin_dong_action_map_2025.html` | 브라우저에서 여는 완성본 | 생성. 열기만 함 |

`src/busan_imd/infographic/`은 이 폴더에 **데이터를 채우는 코드**다. 문구·색·레이아웃 원본을 두지 않는다.

## 실행

모든 Python 명령은 저장소 루트에서 Docker로 실행한다.

```bash
docker compose run --rm jupyter python -m busan_imd.collectors.fire_incidents
docker compose run --rm jupyter python -m busan_imd.processing.standardization
docker compose run --rm jupyter python -m scripts.bootstrap_data prepare
docker compose run --rm jupyter python scripts/rebuild_processed.py
docker compose run --rm jupyter python -m busan_imd.infographic
docker compose run --rm jupyter python -m busan_imd.submission
docker compose run --rm jupyter python -m pytest -q
```

수집기 이름과 원본 위치는 [원본 데이터 수집](data/RAW_DATA_COLLECTION.md), 채택 여부는
[데이터 감사표](../data/tables/DATASET_AUDIT.csv)를 따른다. Mac 이전은
[데이터 이전 정책](data/DATA_PORTABILITY.md)을 따른다.

수집기는 가능한 한 `sources/` 계약을 쓰고, 인증키는 `.env`에서만 읽는다.
`from busan_imd.infographic import run`과 `python -m busan_imd.infographic`은 내부 폴더가
바뀌어도 그대로 둔다. `python -m busan_imd.submission`도 같다.
