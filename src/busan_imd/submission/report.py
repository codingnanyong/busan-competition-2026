"""Korean contest-report draft: official-template sections as markdown and PDF."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.font_manager import FontProperties, findSystemFonts

from busan_imd.submission.config import MAX_BODY_PAGES

COVER = {
    "contest": "2026 Big Data 활용 대회",
    "track": "Track 1 빅데이터 분석 및 시각화",
    "title": "부산 행정동 생활취약지역 탐색 진단",
    "subtitle": "공개자료 기반 실험적 B-IMD 2025 기준선",
    "status": "제출물 초안 · 접수번호 미기재",
    "note": "표지. 본문은 표지 제외 10페이지 이하.",
}

REQUIRED_SECTION_TITLES = (
    "1. 분석개요",
    "2. 활용 데이터",
    "3. 분석방법",
    "4. 분석결과",
    "5. 활용방안",
    "6. 기대효과와 참고문헌",
)

PAGES: tuple[dict[str, object], ...] = (
    {
        "heading": "1. 분석개요",
        "blocks": (
            (
                "p",
                "부산 206개 행정동의 상대적 생활취약성을 측정하고, 취약 원인을 설명하며, "
                "현장 검증용 정책 후보를 연결하는 것이 목적이다. 영국 IMD의 영역 구조를 "
                "참고하되 부산 공개자료로 재구성한 실험적 기준선이며, 공식 통계·개인 자격 "
                "판정·법정 예산배분 기준이 아니다.",
            ),
            (
                "p",
                "필요성. 구·군 평균은 동 내부 차이를 가리고, 단일 지표는 복합 박탈을 설명하지 "
                "못한다. 공개 API와 파일로 재현 가능한 동 단위 선별 도구가 필요하다.",
            ),
            (
                "p",
                "도구와 과정. Python 3.12, GeoPandas, scikit-learn을 Docker에서 실행한다. "
                "수집→행정동 표준화→영역 점수→종합지수→민감도→우선지역 기여도→탐색 유형→"
                "환경 오버레이→정책 매트릭스→1페이지 시각화·대시보드 순이다. 원본 개인정보와 "
                "재배포 금지 원천데이터는 제출 압축파일에 넣지 않는다.",
            ),
            (
                "p",
                "핵심 결과. 종합점수 범위는 20.96~82.82, 중앙값 51.05이다. 1분위(상대 취약 "
                "상위 약 10%)는 21개 동이다. 1~3위는 사상구 모라3동, 동구 초량6동, 해운대구 "
                "반여3동이다. 동일가중 민감도에서 1분위 21개 중 18개가 유지된다.",
            ),
        ),
    },
    {
        "heading": "2. 활용 데이터",
        "blocks": (
            (
                "p",
                "감사 목록 42개 데이터셋은 모두 출처를 남기되, 점수 후보·추정 입력·검증·제외를 "
                "구분한다. 포함 게이트는 전 부산 동일 정의, 문서화된 분자·분모·방향, 결측과 "
                "0의 구분, 재현 가능한 공간 매핑, 관측 종료일 2026-07-31 이하이다. 구 단위 "
                "값을 동에 반복하거나 결측을 0으로 채워 통과시키지 않는다.",
            ),
            (
                "table",
                (
                    ("영역", "주 자료", "등급", "점수 역할"),
                    (
                        "공간·분모",
                        "SGIS 2025 행정동 206, 주민등록 인구·가구",
                        "A/B",
                        "기준지리·분모",
                    ),
                    ("소득", "구·군 맞춤형급여 총계+부분 동 분포 추정", "C", "조건부 대리"),
                    ("고용", "SGIS 2024 사업체·종사자", "C", "일자리 기회 대리"),
                    ("교육", "학교알리미 2025+NEIS 좌표", "B", "거리·공급 대리"),
                    ("건강", "2025 병원·의원·약국 운영 후보", "B", "시설 접근 대리"),
                    ("주거", "SGIS 2024 30년 이상 주택 하한", "B", "시차 대리"),
                    ("교통", "2025 정류장+노선이용+현재 BIMS 배차", "B", "공급·보조 20%+20%"),
                    ("안전", "CCTV 위치, 다발지점 48곳", "B/C", "예방 대리·부분관측"),
                    ("환경", "HEIS 2025 PM2.5 IDW, 무더위쉼터", "B", "노출·대응 대리"),
                ),
            ),
            (
                "p",
                "점수에 넣지 않은 자료. 생활인구·소비매출·도시공원·AED는 화면 참고, 소방 "
                "일일요약·경찰서 5대범죄·구·군 사고통계는 총량 검증, 영도·수영 빈집·사상 "
                "침수·2026 대기는 전역·기준일 불일치로 제외한다. 개인정보 수집·이용 동의서는 "
                "이 분석이 개인 식별자를 수집하지 않으므로 접수 시 공식 서식에만 서명한다.",
            ),
        ),
    },
    {
        "heading": "3. 분석방법",
        "blocks": (
            (
                "p",
                "전처리. 법정동·주소·좌표를 2025 행정동 코드에 결합하고 매핑률·미매핑 수를 "
                "공개한다. 버스정류장 8,522개 중 7,940개를 204개 동에 결합하고 경계 밖 582건을 "
                "민감도 대상으로 남긴다. 소득은 16개 구·군 2025-12 관측 총계를 고정한 뒤, 6개 "
                "구는 공개 동 분포, 10개 구는 상대위험 모형으로 배분한다. 동 값은 관측이 아니다.",
            ),
            (
                "p",
                "정규화와 종합점수. 지표는 취약 방향을 통일한 0~100 부산 내부 백분위다. 영국 "
                "IoD 2025 영역 가중치를 참고하되, 행정동 직접 사건지표가 없는 안전 영역은 "
                "보류하고 나머지 6개 영역 가중치 합 0.906을 1로 재정규화한다(소득·고용 각 "
                "24.83%, 교육·건강 각 14.90%, 주거·생활환경 각 10.26%). 순위 1과 10분위 1이 "
                "가장 취약하다.",
            ),
            (
                "p",
                "카테고리 평가는 종합지수를 대체하지 않는다. 4개 생활여건 영역, 10개 세부 "
                "항목, 19개 지표로 정책 게이트를 만들고, 세부 점수 70점 이상일 때만 해당 항목의 "
                "정책 수단을 검토 후보로 연다. 대중교통은 정류장 공급 60%, 수요가중 노선 접근 "
                "20%, 현재 배차 서비스 기회 20%다. 배차 필드가 없는 동은 0이 아니라 결측이다.",
            ),
            (
                "p",
                "검증. 동일가중·영역 생략 민감도, 우선지역 기여도 분해, 실루엣 0.28의 2개 "
                "탐색 유형, PM을 사회점수에서 뺀 이중부담 오버레이를 사용한다. 시각화는 "
                "Matplotlib 1페이지 PDF와 독립형 HTML 대시보드다.",
            ),
        ),
    },
    {
        "heading": "4. 분석결과",
        "blocks": (
            (
                "table",
                (
                    ("순위", "구", "행정동", "B-IMD", "대표 영역"),
                    ("1", "사상구", "모라3동", "82.82", "소득"),
                    ("2", "동구", "초량6동", "80.26", "고용"),
                    ("3", "해운대구", "반여3동", "79.70", "고용"),
                    ("4", "동구", "수정4동", "77.22", "고용"),
                    ("5", "북구", "덕천3동", "76.36", "고용"),
                    ("6", "사하구", "감천2동", "76.32", "고용"),
                    ("7", "동구", "수정5동", "74.58", "고용"),
                    ("8", "동구", "수정1동", "73.72", "고용"),
                    ("9", "서구", "초장동", "73.66", "고용"),
                    ("10", "해운대구", "반여2동", "73.44", "소득"),
                ),
            ),
            (
                "p",
                "1분위 21개 동의 대표 영역은 고용 12, 소득 9이다. 고용은 거주자 실업이 아니라 "
                "사업장 종사자 공급 대리이고, 소득은 기초생활 추정 대리다. 대표 원인은 단순 "
                "기여점수가 아니라 부산 중앙값 대비 가중 초과점수가 가장 큰 영역이다.",
            ),
            (
                "p",
                "탐색 유형. 품질 게이트를 통과한 2개 군집은 교육·생활환경 상대형 5개 동과 "
                "고용·소득형 16개 동이다. 전자의 생활환경 평균 초과점수는 음수라 생활환경 "
                "일반정책은 자동 추천하지 않는다. 미세먼지 독립 이중부담은 가락동, 모라3동, "
                "수정4동, 수정1동 4곳이다.",
            ),
        ),
    },
    {
        "heading": "4. 분석결과 (이어서) · 검증과 한계",
        "blocks": (
            (
                "p",
                "동일가중 시나리오의 순위 스피어만 상관은 0.936, 1분위 겹침은 21개 중 18개"
                "(85.7%)다. 소득 또는 고용 영역을 통째로 빼면 1분위 겹침이 57~67%로 떨어져, "
                "현재 순위가 두 대리지표에 민감함을 보여 준다. 이는 해당 영역이 결측이라는 "
                "주장이 아니라 스트레스 검사다.",
            ),
            (
                "p",
                "한계. (1) 대리는 실제 소득·실업·범죄·질병이 아니다. (2) 안전 직접 사건지표 "
                "부재로 종합지수는 6영역이다. (3) 대중교통 보조지표는 2025 이용량과 현재 "
                "노선망의 혼합시점이다. (4) 대기질은 32개 측정소 IDW이며 최근접 거리 최대 "
                "7.47km다. (5) 생태학적 오류: 취약 동의 모든 주민이 취약하지 않다.",
            ),
            (
                "p",
                "금지 해석. 개인·가구 복지 자격 판정, 법정 낙후지역·자동 예산배분, 구 단위 "
                "값의 동 반복, 대리를 범죄율·실업률로 명명, 방법·입력이 다른 릴리스의 순위 "
                "단순 증감 비교.",
            ),
            (
                "p",
                "보완. 206동 동일 정의 2025-12 기초생활 관측, 거주지 고용·실업, 동별 범죄·"
                "전체 사고·화재, 건강결과·교육성과, 전역 빈집·과밀, 2025 당시 실제 운행횟수가 "
                "오면 대리를 교체한다. 건축물대장 API는 법정동 결합 수집기가 없어 이번 초안에 "
                "넣지 않았다.",
            ),
        ),
    },
    {
        "heading": "5. 활용방안",
        "blocks": (
            (
                "p",
                "적용 부문. 부산시·구군 복지, 일자리, 교육, 보건, 환경 담당이 현장 점검 대상을 "
                "고를 때 쓰는 탐색 도구다. 1페이지 PDF는 서류 제출용, HTML 대시보드는 동을 "
                "클릭해 19개 지표·추정 사유·70점 정책 게이트를 확인하는 운영 화면이다.",
            ),
            (
                "table",
                (
                    ("유형", "대상", "정책 후보", "난이도"),
                    ("교육 상대형", "5개 동", "방과후 학습·학교 접근 점검", "중"),
                    ("교육 상대형", "가락동", "미세먼지 모니터링·민감계층 보호", "상"),
                    ("고용·소득형", "16개 동", "생활권 일자리·직업훈련 연계", "중"),
                    ("고용·소득형", "16개 동", "복지급여 누락 점검·사례관리", "중"),
                    ("고용·소득형", "모라3·수정4·수정1", "미세먼지 모니터링·민감계층 보호", "상"),
                ),
            ),
            (
                "p",
                "실행 원칙. 정책 카드는 분석 신호가 아니라 검증 후 비교할 수단이다. 카테고리 "
                "70점 미만 동에는 같은 패키지를 적용하지 않는다. 특화 산업·관광 방향은 상권·"
                "생활SOC 자료가 없어 확정하지 않고, 상대 저취약 영역만 보전 검토 후보로 둔다.",
            ),
        ),
    },
    {
        "heading": "6. 기대효과와 참고문헌",
        "blocks": (
            (
                "p",
                "정량. 206개 동을 같은 코드로 비교하고 1분위 21개를 선별한다. 동일가중에서도 "
                "18개가 유지되어 최상위 선별의 방향은 안정적이다. 감사 42개 자료마다 점수·검증·"
                "제외 역할을 명시해 중복 투입과 잘못된 공간 할당을 줄인다.",
            ),
            (
                "p",
                "정성. 추정·대리·보간 여부를 동별로 공개하므로, 기관 전수가 오는 즉시 교체 "
                "지점을 알 수 있다. 대시보드는 종합순위와 카테고리 평가를 합산하지 않아 정책 "
                "오용을 줄인다.",
            ),
            (
                "p",
                "참고문헌. Ministry of Housing, Communities and Local Government, English "
                "Indices of Deprivation 2025. 공공데이터포털·SGIS·HEIS·KOROAD·학교알리미 원문 "
                "URL과 기준일은 docs/data/tables/DATASET_AUDIT.csv에 기록한다. 재현 명령: "
                "docker compose run --rm jupyter python scripts/rebuild_processed.py",
            ),
            (
                "p",
                "오픈랩·Big-데이터 웨이브 가점 증빙은 해당 프로그램 참여 여부가 확정되면 "
                "별도 첨부한다. 본 초안은 참여를 단정하지 않는다.",
            ),
        ),
    },
)


def noto_family() -> str:
    candidates = [path for path in findSystemFonts() if "NotoSansCJK-Regular" in path]
    if not candidates:
        raise RuntimeError(
            "Noto Sans CJK is required to render the Korean report PDF; "
            "use the project Docker image or install NotoSansCJK-Regular"
        )
    mpl.font_manager.fontManager.addfont(candidates[0])
    return FontProperties(fname=candidates[0]).get_name()


def wrap_korean(text: str, width: int = 42) -> list[str]:
    lines: list[str] = []
    remaining = text.strip()
    while remaining:
        if len(remaining) <= width:
            lines.append(remaining)
            break
        cut = remaining.rfind(" ", 0, width + 1)
        if cut < width // 2:
            cut = width
        lines.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    return lines


def markdown_report() -> str:
    lines = [
        f"# {COVER['title']}",
        "",
        f"- {COVER['contest']} / {COVER['track']}",
        f"- {COVER['subtitle']}",
        f"- {COVER['status']}",
        "",
        "공식 서식의 표지·동의서는 접수 시 `docs/templates/` 원본에 작성한다. "
        "아래 본문을 복사한다.",
        "",
    ]
    for page in PAGES:
        lines.append(f"## {page['heading']}")
        lines.append("")
        for kind, payload in page["blocks"]:
            if kind == "p":
                lines.append(str(payload))
                lines.append("")
            else:
                rows = payload
                header = " | ".join(rows[0])
                sep = " | ".join("---" for _ in rows[0])
                lines.append(f"| {header} |")
                lines.append(f"| {sep} |")
                for row in rows[1:]:
                    lines.append("| " + " | ".join(row) + " |")
                lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_markdown(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown_report(), encoding="utf-8", newline="\n")


def _draw_cover(fig, family: str) -> None:
    fig.text(0.12, 0.72, COVER["contest"], fontsize=13, fontfamily=family, color="#334155")
    fig.text(0.12, 0.66, COVER["track"], fontsize=11, fontfamily=family, color="#475569")
    fig.text(0.12, 0.52, COVER["title"], fontsize=22, fontfamily=family, fontweight="bold")
    fig.text(0.12, 0.44, COVER["subtitle"], fontsize=13, fontfamily=family, color="#0f172a")
    fig.text(0.12, 0.28, COVER["status"], fontsize=10, fontfamily=family, color="#64748b")
    fig.text(0.12, 0.16, COVER["note"], fontsize=9, fontfamily=family, color="#94a3b8")


def _draw_page(fig, page: dict[str, object], family: str, page_no: int, body_count: int) -> None:
    fig.text(
        0.08,
        0.94,
        str(page["heading"]),
        fontsize=13,
        fontfamily=family,
        fontweight="bold",
        color="#0f172a",
    )
    y = 0.88
    for kind, payload in page["blocks"]:
        if kind == "p":
            for line in wrap_korean(str(payload), 46):
                fig.text(0.08, y, line, fontsize=9.2, fontfamily=family, color="#1e293b")
                y -= 0.032
            y -= 0.012
            continue
        rows = payload
        col_x = [0.08, 0.18, 0.36, 0.62, 0.78]
        if len(rows[0]) == 4:
            col_x = [0.08, 0.28, 0.52, 0.78]
        for r_i, row in enumerate(rows):
            weight = "bold" if r_i == 0 else "normal"
            color = "#0f172a" if r_i == 0 else "#334155"
            for c_i, cell in enumerate(row):
                fig.text(
                    col_x[c_i],
                    y,
                    cell,
                    fontsize=7.6,
                    fontfamily=family,
                    fontweight=weight,
                    color=color,
                )
            y -= 0.028
        y -= 0.016
    fig.text(
        0.08,
        0.045,
        f"본문 {page_no}/{body_count} · 실험적 상대평가 · 공식 통계 아님",
        fontsize=8,
        fontfamily=family,
        color="#94a3b8",
    )


def write_pdf(path: Path) -> dict[str, int | str]:
    family = noto_family()
    path.parent.mkdir(parents=True, exist_ok=True)
    mpl.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42})
    body_count = len(PAGES)
    if body_count > MAX_BODY_PAGES:
        raise ValueError(f"report body has {body_count} pages; maximum is {MAX_BODY_PAGES}")
    fixed_date = datetime(2025, 12, 31, tzinfo=UTC)
    metadata = {
        "Title": COVER["title"],
        "Author": "busan-competition-2026",
        "CreationDate": fixed_date,
        "ModDate": fixed_date,
    }
    with PdfPages(path, metadata=metadata) as pdf:
        fig = plt.figure(figsize=(8.27, 11.69), facecolor="white")
        _draw_cover(fig, family)
        pdf.savefig(fig)
        plt.close(fig)
        for index, page in enumerate(PAGES, start=1):
            fig = plt.figure(figsize=(8.27, 11.69), facecolor="white")
            _draw_page(fig, page, family, index, body_count)
            pdf.savefig(fig)
            plt.close(fig)
    return {
        "cover_pages": 1,
        "body_pages": body_count,
        "total_pages": body_count + 1,
        "font_family": family,
    }
