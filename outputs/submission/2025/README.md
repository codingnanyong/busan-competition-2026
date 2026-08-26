# 2025 제출물 초안

공식 압축 구성에 맞춘 초안이다. 접수번호와 최종 파일명은 제출 직전에 참가 신청 폼을
다시 확인한다.

- `01_data-visualization.pdf`: 1페이지 인포그래픽. 파이프라인이 복사한다.
- `02_analysis-report.pdf`: 표지와 본문. 본문은 10페이지 이하.
- `02_analysis-report.md`: 공식 HWPX 서식에 붙여 넣을 본문.
- `03_data/`: 재배포 가능한 파생 표와 출처 목록(XLSX·CSV). `data/raw` 원천은 넣지 않는다.

HWPX는 `docs/templates/2026-big-data-competition-submission-template.hwpx`를 복사한 뒤
`02_analysis-report.md`를 서식 목차에 옮긴다. 이 초안은 Hangul 파일을 자동 작성하지
않으며, 빈 서식을 제출 보고서로 두지 않는다.

```bash
docker compose run --rm jupyter python -m busan_imd.submission
```
