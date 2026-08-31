# 2025 공모전 제출물 초안

## 범위

COD-24는 공모전 최종 압축파일의 **기계 작성 초안**을 만든다. 대상은 Track 1 제출 패키지
가운데 1페이지 시각화, 분석보고서 PDF, 재배포 가능한 활용데이터다. 공식 분석보고서
HWPX는 Hangul에서 서식 원본에 본문을 옮겨 작성한다. 이 단계는 빈 서식 파일을 제출
보고서로 복사하지 않는다.

초안 지위는 `submission_draft`다. Git에 올리는 기계 초안과 접수용 ZIP은 다르다.
접수용 ZIP은 `outputs/contest-upload/2025/`와 Drive `output`에 두며, Hangul 작성
HWPX·공식 PDF·1페이지 시각화·파생표·브라우저 대시보드를 담는다. 접수번호는 비운다.
동의서는 ZIP 밖 PDF로 따로 올린다. 재현성·페이지 수·라이선스 제외 검수는
[2025 제출 재현성 검증](REPRODUCIBILITY_QA_2025.md)에 기록한다. COD-26은
v1.0.0 태그와 Release·Wiki를 맡는다. 발표 대본·데모·질의응답은
[2025 발표평가 패키지](PRESENTATION_2025.md)에 있다.

## 패키지

| 파일 | 역할 |
|---|---|
| [`01_data-visualization.pdf`](../../../outputs/submission/2025/01_data-visualization.pdf) | COD-23 1페이지 PDF 복사본. 정확히 1장 |
| [`02_analysis-report.pdf`](../../../outputs/submission/2025/02_analysis-report.pdf) | 파이프라인 초안 PDF. 접수용이 아님 |
| `02_analysis-report-official.pdf` | Hangul에서보낸 공식 보고서 PDF. Git에 올리지 않음 |
| `02_analysis-report.hwpx` | Hangul 작성본. Git 초안에는 두지 않음 |
| [`02_analysis-report.md`](../../../outputs/submission/2025/02_analysis-report.md) | 서식에 붙여 넣었던 국문 본문 |
| [`03_data/source-catalog.csv`](../../../outputs/submission/2025/03_data/source-catalog.csv) | 감사 42개 자료의 출처·기준일·라이선스·채택. XLSX는 파이프라인이 로컬에서 다시 만든다 |
| `03_data/README.txt` | 원천을 ZIP에 넣지 않는 이유와 재수집 안내 |
| `04_interactive/` | 접수용 ZIP에만 복사. `outputs/infographic/2025/interactive/`와 같다 |
| [`03_data/data-dictionary.csv`](../../../outputs/submission/2025/03_data/data-dictionary.csv) | 분석 컬럼 사전 |
| `03_data/*.csv` | 동별 프로필·카테고리 평가 파생 표 |
| [`README.md`](../../../outputs/submission/2025/README.md) | Hangul 붙여넣기 안내 |
| [SUBMISSION_DRAFT_REPORT_2025.json](../../data/manifests/SUBMISSION_DRAFT_REPORT_2025.json) | 페이지 수·체크섬·HWPX 상태 |

`data/raw`와 재배포가 금지된 원천, 개인 식별자는 넣지 않는다. 1페이지 시각화의 설계는
[2025 1페이지 인포그래픽](INFOGRAPHIC_2025.md)을 따른다. 브라우저 대시보드는 같은
문서의 HTML 경로를 접수용 ZIP `04_interactive/`로 복사한다.

## 실행

Noto Sans CJK가 있는 Docker 이미지에서 저장소 루트로 실행한다.

```bash
docker compose run --rm jupyter python -m busan_imd.submission
```

전체 가공 파이프라인의 마지막 단계에서도 같은 패키지를 다시 만든다.

```bash
docker compose run --rm jupyter python scripts/rebuild_processed.py
```

## 보고서 구성

본문은 공식 서식 목차에 맞춰 다음 제목을 쓴다.

1. 분석개요: 목적, 필요성, 도구·과정, 핵심 결과
2. 활용 데이터: 포함 게이트, 영역별 주 자료, 점수 제외·검증 자료
3. 분석방법: 전처리, 정규화·가중치, 카테고리 평가, 검증
4. 분석결과: 상위 10개 동, 탐색 유형, 민감도, 한계와 금지 해석
5. 활용방안: 적용 부문과 유형별 정책 후보
6. 기대효과와 참고문헌: 정량·정성 효과, 재현 명령

표지는 페이지 제한에서 제외한다. 동의서와 접수번호는 제출 시 서식 원본에 작성한다.

## HWPX 작성

1. [`docs/templates/2026-big-data-competition-submission-template.hwpx`](../../templates/2026-big-data-competition-submission-template.hwpx)
   를 작업 복사본으로 만든다. 저장소의 서식 원본은 수정하지 않는다.
2. Hangul에서 연 뒤 `02_analysis-report.md` 본문을 대응 목차로 옮긴다.
3. 표지 항목을 채우되 접수번호는 비운다.
4. 개인정보 동의서는 접수 시 서명한다. 이 분석은 개인 식별자를 수집하지 않는다.
5. HWPX와 PDF의 제목·표·페이지 구성이 같은지 COD-25에서 대조한다.

## 해석 한계

초안 숫자는 커밋된 2025 점수·인포그래픽과 같다. 대리지표, 6영역 종합지수, 생태학적
오류, 금지 해석은 [한계 및 해석](LIMITATIONS.md)과 본문 4장을 따른다. 빈 HWPX 서식을
제출 보고서로 간주하지 않는다.
