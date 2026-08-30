# 2025 제출 재현성 검증

확인일: 2026-08-31 (KST). COD-25.

## 범위

깨끗한 Git 초안과 접수용 ZIP을 검수한다. 원천 번들을 다시 받아 점수를 다시 계산하는
작업은 아니다. 전체 재생성은 raw-data bundle을 복원한 뒤
`scripts/rebuild_processed.py`를 따른다.

## 통과한 검사

| 항목 | 결과 |
|---|---|
| 시각화 PDF | 1페이지 |
| 초안 보고서 PDF | 표지 포함 8페이지, 본문 7페이지 |
| 출처 목록 | 42건. provider, URL, 수집방법, 기준일, 라이선스, 채택 |
| 파생표 | 동별 프로필·카테고리·지표 CSV 4종 |
| 원천 파일 | ZIP·Git 초안에 없음. `03_data/README.txt`에 이유 기록 |
| 비밀값 | 제출 폴더 텍스트에 API 키·consumer_secret 없음 |
| 공식 HWPX | Git에 없음. Hangul 작성본은 접수용 ZIP에만 있음 |

검사 명령:

```bash
docker compose run --rm jupyter python -m pytest -q
python -c "from busan_imd.submission.verify import verify_committed_package; print(verify_committed_package())"
```

## 라이선스

재배포 조건이 미확정이거나 확인 전인 원천(SGIS, HEIS, KOROAD 등)은 압축파일에 넣지
않았다. 제공기관·원문 URL·수집방법·기준일·라이선스는 `03_data/source-catalog`에 있다.

## 접수본과 Git 초안

| 산출물 | Git 초안 | 접수용 ZIP |
|---|---|---|
| 1페이지 시각화 | 있음 | 있음 |
| 파이프라인 보고서 PDF | 있음 | 없음. Hangul PDF를 씀 |
| Hangul HWPX/PDF | 없음 | 있음 |
| 브라우저 대시보드 | `outputs/infographic/2025/interactive/` | `04_interactive/` |
| 원천 tar.gz | 없음. Drive `raw-data/2025/` | 없음 |

## 해석

숫자는 커밋된 2025 점수와 같다. 공식 통계·개인 판정·예산 배분 기준으로 쓰지 않는다.
