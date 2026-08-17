#!/usr/bin/env bash
set -euo pipefail

output_dir="${1:?usage: build_wiki.sh OUTPUT_DIR}"

case "$output_dir" in
  ""|"/"|"."|"..")
    echo "unsafe output directory: $output_dir" >&2
    exit 1
    ;;
esac

mkdir -p "$output_dir"
find "$output_dir" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +

page_manifest="$output_dir/.wiki-pages.tsv"
: > "$page_manifest"

publish_page() {
  local source_path="$1"
  local page_name="$2"

  cp "$source_path" "$output_dir/$page_name.md"
  printf '%s\t%s\n' "$source_path" "$page_name" >> "$page_manifest"
}

publish_page README.md Home
publish_page README.ko.md KO-Home
publish_page README.en.md EN-Home

publish_page docs/PROJECT_PLAN.md KO-Project-Plan
publish_page docs/GIT_WORKFLOW.md KO-Git-Workflow
publish_page docs/RELEASE_POLICY.md KO-Release-Policy
publish_page docs/ISSUES.md KO-Linear-Issues
publish_page docs/data/DATA_CATALOG.md KO-Data-Catalog
publish_page docs/data/AVAILABILITY_MATRIX.md KO-Data-Availability
publish_page docs/data/DATA_REQUEST_ROADMAP.md KO-Data-Request-Roadmap
publish_page docs/data/EDA_2025.md KO-EDA-2025
publish_page docs/methodology/DOMAIN_SCORES_2025.md KO-Domain-Scores-2025
publish_page docs/methodology/COMPOSITE_INDEX_2025.md KO-Composite-Index-2025
publish_page docs/methodology/INDICATOR_SPEC.md KO-Indicator-Spec
publish_page docs/methodology/LIMITATIONS.md KO-Limitations
publish_page docs/methodology/EXPANSION_MODEL.md KO-Expansion-Model

publish_page docs/en/PROJECT_PLAN.md EN-Project-Plan
publish_page docs/en/GIT_WORKFLOW.md EN-Git-Workflow
publish_page docs/en/RELEASE_POLICY.md EN-Release-Policy
publish_page docs/en/ISSUES.md EN-Linear-Issues
publish_page docs/en/data/DATA_CATALOG.md EN-Data-Catalog
publish_page docs/en/data/AVAILABILITY_MATRIX.md EN-Data-Availability
publish_page docs/en/data/DATA_REQUEST_ROADMAP.md EN-Data-Request-Roadmap
publish_page docs/en/data/EDA_2025.md EN-EDA-2025
publish_page docs/en/methodology/DOMAIN_SCORES_2025.md EN-Domain-Scores-2025
publish_page docs/en/methodology/COMPOSITE_INDEX_2025.md EN-Composite-Index-2025
publish_page docs/en/methodology/INDICATOR_SPEC.md EN-Indicator-Spec
publish_page docs/en/methodology/LIMITATIONS.md EN-Limitations
publish_page docs/en/methodology/EXPANSION_MODEL.md EN-Expansion-Model

for release_note in docs/releases/v*.md; do
  version="$(basename "$release_note" .md)"
  publish_page "$release_note" "KO-Release-${version}"
done

for release_note in docs/en/releases/v*.md; do
  version="$(basename "$release_note" .md)"
  publish_page "$release_note" "EN-Release-${version}"
done

python3 scripts/rewrite_wiki_links.py "$output_dir" "$page_manifest"
rm "$page_manifest"

printf '%s\n' \
  '## 한국어' \
  '- [[홈|KO-Home]]' \
  '- [[프로젝트 계획|KO-Project-Plan]]' \
  '- [[Git 워크플로|KO-Git-Workflow]]' \
  '- [[릴리스 정책|KO-Release-Policy]]' \
  '- [[Linear 이슈|KO-Linear-Issues]]' \
  '- [[데이터 카탈로그|KO-Data-Catalog]]' \
  '- [[데이터 가용성|KO-Data-Availability]]' \
  '- [[필요 데이터 로드맵|KO-Data-Request-Roadmap]]' \
  '- [[2025 후보지표 EDA|KO-EDA-2025]]' \
  '- [[2025 영역 점수|KO-Domain-Scores-2025]]' \
  '- [[2025 종합지수|KO-Composite-Index-2025]]' \
  '- [[지표 명세|KO-Indicator-Spec]]' \
  '- [[한계 및 해석|KO-Limitations]]' \
  '- [[확장 모델|KO-Expansion-Model]]' \
  '' \
  '## English' \
  '- [[Home|EN-Home]]' \
  '- [[Project Plan|EN-Project-Plan]]' \
  '- [[Git Workflow|EN-Git-Workflow]]' \
  '- [[Release Policy|EN-Release-Policy]]' \
  '- [[Linear Issues|EN-Linear-Issues]]' \
  '- [[Data Catalog|EN-Data-Catalog]]' \
  '- [[Data Availability|EN-Data-Availability]]' \
  '- [[Data Request Roadmap|EN-Data-Request-Roadmap]]' \
  '- [[2025 Candidate EDA|EN-EDA-2025]]' \
  '- [[2025 Domain Scores|EN-Domain-Scores-2025]]' \
  '- [[2025 Composite Index|EN-Composite-Index-2025]]' \
  '- [[Indicator Specification|EN-Indicator-Spec]]' \
  '- [[Limitations|EN-Limitations]]' \
  '- [[Expansion Model|EN-Expansion-Model]]' \
  > "$output_dir/_Sidebar.md"
