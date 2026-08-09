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

cp README.md "$output_dir/Home.md"
cp README.ko.md "$output_dir/KO-Home.md"
cp README.en.md "$output_dir/EN-Home.md"

cp docs/PROJECT_PLAN.md "$output_dir/KO-Project-Plan.md"
cp docs/GIT_WORKFLOW.md "$output_dir/KO-Git-Workflow.md"
cp docs/RELEASE_POLICY.md "$output_dir/KO-Release-Policy.md"
cp docs/ISSUES.md "$output_dir/KO-Linear-Issues.md"
cp docs/data/DATA_CATALOG.md "$output_dir/KO-Data-Catalog.md"
cp docs/data/AVAILABILITY_MATRIX.md "$output_dir/KO-Data-Availability.md"
cp docs/data/DATA_REQUEST_ROADMAP.md "$output_dir/KO-Data-Request-Roadmap.md"
cp docs/methodology/INDICATOR_SPEC.md "$output_dir/KO-Indicator-Spec.md"
cp docs/methodology/LIMITATIONS.md "$output_dir/KO-Limitations.md"
cp docs/methodology/EXPANSION_MODEL.md "$output_dir/KO-Expansion-Model.md"

cp docs/en/PROJECT_PLAN.md "$output_dir/EN-Project-Plan.md"
cp docs/en/GIT_WORKFLOW.md "$output_dir/EN-Git-Workflow.md"
cp docs/en/RELEASE_POLICY.md "$output_dir/EN-Release-Policy.md"
cp docs/en/ISSUES.md "$output_dir/EN-Linear-Issues.md"
cp docs/en/data/DATA_CATALOG.md "$output_dir/EN-Data-Catalog.md"
cp docs/en/data/AVAILABILITY_MATRIX.md "$output_dir/EN-Data-Availability.md"
cp docs/en/data/DATA_REQUEST_ROADMAP.md "$output_dir/EN-Data-Request-Roadmap.md"
cp docs/en/methodology/INDICATOR_SPEC.md "$output_dir/EN-Indicator-Spec.md"
cp docs/en/methodology/LIMITATIONS.md "$output_dir/EN-Limitations.md"
cp docs/en/methodology/EXPANSION_MODEL.md "$output_dir/EN-Expansion-Model.md"

for release_note in docs/releases/v*.md; do
  version="$(basename "$release_note" .md)"
  cp "$release_note" "$output_dir/KO-Release-${version}.md"
done

for release_note in docs/en/releases/v*.md; do
  version="$(basename "$release_note" .md)"
  cp "$release_note" "$output_dir/EN-Release-${version}.md"
done

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
  '- [[Indicator Specification|EN-Indicator-Spec]]' \
  '- [[Limitations|EN-Limitations]]' \
  '- [[Expansion Model|EN-Expansion-Model]]' \
  > "$output_dir/_Sidebar.md"
