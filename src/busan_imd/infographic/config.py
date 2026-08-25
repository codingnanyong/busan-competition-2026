"""Shared paths and presentation constants for infographic outputs."""

from pathlib import Path

from busan_imd.analysis.composite_index import DEFAULT_OUTPUT as _DEFAULT_COMPOSITE
from busan_imd.analysis.environmental_overlay import DEFAULT_OUTPUT as _DEFAULT_OVERLAY
from busan_imd.analysis.policy_matrix import DEFAULT_OUTPUT as _DEFAULT_POLICY_MATRIX
from busan_imd.analysis.priority_areas import DEFAULT_PRIORITY_OUTPUT as _DEFAULT_PRIORITY_OUTPUT

DEFAULT_COMPOSITE = _DEFAULT_COMPOSITE
DEFAULT_OVERLAY = _DEFAULT_OVERLAY
DEFAULT_POLICY_MATRIX = _DEFAULT_POLICY_MATRIX
DEFAULT_PRIORITY_OUTPUT = _DEFAULT_PRIORITY_OUTPUT

DEFAULT_BOUNDARIES = Path(
    "data/raw/sgis/admin_boundaries/2025/busan_admin_dong_boundaries_2025_valid.geojson"
)
DEFAULT_OUTPUT_DIR = Path("outputs/infographic")
DEFAULT_SVG_OUTPUT = DEFAULT_OUTPUT_DIR / "busan_imd_one_page_2025.svg"
DEFAULT_PDF_OUTPUT = DEFAULT_OUTPUT_DIR / "busan_imd_one_page_2025.pdf"
DEFAULT_PNG_OUTPUT = DEFAULT_OUTPUT_DIR / "busan_imd_one_page_2025.png"
DEFAULT_PROFILE_OUTPUT = DEFAULT_OUTPUT_DIR / "busan_admin_dong_action_profile_2025.csv"
DEFAULT_HTML_OUTPUT = DEFAULT_OUTPUT_DIR / "busan_admin_dong_action_map_2025.html"
DEFAULT_CATEGORY_ASSESSMENT = DEFAULT_OUTPUT_DIR / "busan_admin_dong_category_assessment_2025.csv"
DEFAULT_MAJOR_CATEGORY_ASSESSMENT = (
    DEFAULT_OUTPUT_DIR / "busan_admin_dong_major_category_assessment_2025.csv"
)
DEFAULT_INDICATOR_SCORES = (
    DEFAULT_OUTPUT_DIR / "busan_admin_dong_category_indicator_scores_2025.csv"
)
DEFAULT_POLICY_CATALOG = Path("docs/data/CATEGORY_POLICY_CATALOG_2025.csv")
DEFAULT_REPORT = Path("docs/data/manifests/INFOGRAPHIC_REPORT_2025.json")

EXPECTED_DONG_COUNT = 206
EXPECTED_PRIORITY_COUNT = 21

PALETTE = {
    "ink": "#18323D",
    "muted": "#5D7078",
    "paper": "#F7F4ED",
    "panel": "#FFFFFF",
    "accent": "#D84A3A",
    "blue": "#087E8B",
    "gold": "#D99A25",
    "line": "#D7DED9",
}

DOMAIN_COLUMNS = {
    "education": ("education_score_0_100", "교육"),
    "employment": ("employment_score_0_100", "고용"),
    "health": ("health_score_0_100", "건강"),
    "housing_access": ("housing_access_score_0_100", "주거·접근성"),
    "income": ("income_score_0_100", "소득"),
    "living_environment": ("living_environment_score_0_100", "생활환경"),
}

IMPROVEMENT_ACTIONS = {
    "education": "학습지원·학교 접근성 점검",
    "employment": "주민 고용자료 검증 후 일자리·훈련 연계",
    "health": "의료·건강관리 접근성 점검",
    "housing_access": "주거·교통·생활시설 접근 개선",
    "income": "복지급여 누락 점검·통합사례관리",
    "living_environment": "생활환경·안전·대기질 현장점검",
}

PRESERVATION_DIRECTIONS = {
    "education": "교육 기반 보전·연계 검토",
    "employment": "지역 일자리 기반 보전 검토",
    "health": "건강·의료 접근 기반 보전 검토",
    "housing_access": "주거·교통 접근 기반 보전 검토",
    "income": "경제 안정 기반 보전 검토",
    "living_environment": "생활환경 기반 보전 검토",
}
