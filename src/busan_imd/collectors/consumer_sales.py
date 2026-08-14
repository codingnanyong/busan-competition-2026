"""Prepare 2025 Busan administrative-dong consumer-sales validation indicators."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from busan_imd.core.artifacts import sha256_file, write_json

PROTECTED_DOWNLOAD = Path(
    "data/raw/busan_data_wave/consumer_sales/2025/"
    "busan_admin_dong_consumer_sales_by_industry_2023_2025.xlsx"
)
DEFAULT_INPUT = Path(
    "data/raw/busan_data_wave/consumer_sales/2025/"
    "busan_admin_dong_consumer_sales_by_industry_2023_2025_parsed.csv"
)
DEFAULT_REFERENCE = Path("docs/data/BUSAN_ADMIN_DONG_CODES_2025.csv")
DEFAULT_OUTPUT = Path("data/processed/candidates/2025/consumer_sales_2025.csv")
DEFAULT_CATEGORY_OUTPUT = Path(
    "data/processed/candidates/2025/consumer_sales_by_category_2025.csv"
)
DEFAULT_MANIFEST = Path("docs/data/manifests/CONSUMER_SALES_MANIFEST_2025.json")
REQUIRED_COLUMNS = {
    "기준년월",
    "행정동코드",
    "행정동명",
    "업종대분류",
    "평균이용금액",
    "평균이용건수",
}


def prepare(
    frame: pd.DataFrame, reference: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """Map portal codes to canonical SGIS codes and aggregate monthly daily averages."""
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"Consumer-sales workbook is missing columns: {sorted(missing)}")
    data = frame.copy()
    data["기준년월"] = data["기준년월"].astype(str).str.replace(r"\.0$", "", regex=True)
    data = data[data["기준년월"].str.fullmatch(r"2025(0[1-9]|1[0-2])")].copy()
    if data.empty:
        raise ValueError("Consumer-sales workbook contains no 2025 rows")
    data["행정동코드"] = data["행정동코드"].astype(str).str.replace(r"\.0$", "", regex=True)
    data["행정동명"] = data["행정동명"].fillna("").astype(str).str.strip()
    for column in ("평균이용금액", "평균이용건수"):
        data[column] = pd.to_numeric(data[column], errors="raise")
        if (data[column] < 0).any():
            raise ValueError(f"Consumer-sales workbook has negative values in {column}")
    duplicates = int(data.duplicated(["기준년월", "행정동코드", "업종대분류"]).sum())
    if duplicates:
        raise ValueError(f"Consumer-sales workbook has {duplicates} duplicate monthly rows")

    ref = reference[["sigungu_name", "admin_dong_name", "admin_dong_code"]].copy()
    ref["admin_dong_code"] = ref["admin_dong_code"].astype(str)
    ref["portal_name"] = ref["sigungu_name"].astype(str) + " " + ref["admin_dong_name"].astype(str)
    mapping = dict(zip(ref["portal_name"], ref["admin_dong_code"], strict=True))
    data["admin_dong_code"] = data["행정동명"].map(mapping)

    recovered: list[dict[str, str]] = []
    for portal_code in data.loc[data["admin_dong_code"].isna(), "행정동코드"].unique():
        named = data.loc[data["행정동코드"] == portal_code, "행정동명"].replace("", pd.NA).dropna()
        if not named.empty:
            raise ValueError(f"Unmatched consumer-sales administrative dong: {named.iloc[0]}")
        used = set(data["admin_dong_code"].dropna())
        candidates = ref.loc[~ref["admin_dong_code"].isin(used)]
        if len(candidates) != 1:
            raise ValueError(f"Cannot unambiguously recover unnamed portal code {portal_code}")
        recovered_code = str(candidates.iloc[0]["admin_dong_code"])
        recovered_name = str(candidates.iloc[0]["portal_name"])
        data.loc[data["행정동코드"] == portal_code, "admin_dong_code"] = recovered_code
        recovered.append(
            {"portal_code": portal_code, "canonical_code": recovered_code, "name": recovered_name}
        )

    data["days"] = pd.to_datetime(data["기준년월"] + "01", format="%Y%m%d").dt.days_in_month
    monthly = (
        data.groupby(["admin_dong_code", "기준년월"], as_index=False)
        .agg(
            avg_daily_amount=("평균이용금액", "sum"),
            avg_daily_transactions=("평균이용건수", "sum"),
            days=("days", "first"),
        )
    )

    def aggregate(group: pd.DataFrame) -> pd.Series:
        observed_days = int(group["days"].sum())
        return pd.Series(
            {
                "consumer_sales_avg_daily_amount_2025": (
                    group["avg_daily_amount"] * group["days"]
                ).sum()
                / observed_days,
                "consumer_sales_avg_daily_transactions_2025": (
                    group["avg_daily_transactions"] * group["days"]
                ).sum()
                / observed_days,
                "consumer_sales_observed_months_2025": int(group["기준년월"].nunique()),
                "consumer_sales_observed_days_2025": observed_days,
            }
        )

    summary = monthly.groupby("admin_dong_code", as_index=False).apply(
        aggregate, include_groups=False
    )
    summary["consumer_sales_complete_2025"] = (
        summary["consumer_sales_observed_months_2025"] == 12
    )
    summary = ref[["admin_dong_code", "admin_dong_name"]].merge(
        summary, on="admin_dong_code", how="left", validate="one_to_one"
    )
    if summary["consumer_sales_observed_months_2025"].isna().any():
        raise ValueError("Consumer-sales data does not cover all 206 canonical dongs")

    category = (
        data.groupby(["admin_dong_code", "업종대분류"], as_index=False)
        .apply(
            lambda group: pd.Series(
                {
                    "consumer_sales_avg_daily_amount_2025": (
                        group["평균이용금액"] * group["days"]
                    ).sum()
                    / group["days"].sum(),
                    "consumer_sales_avg_daily_transactions_2025": (
                        group["평균이용건수"] * group["days"]
                    ).sum()
                    / group["days"].sum(),
                    "observed_months_2025": int(group["기준년월"].nunique()),
                }
            ),
            include_groups=False,
        )
        .rename(columns={"업종대분류": "industry_category"})
    )
    checks: dict[str, object] = {
        "source_rows_2025": len(data),
        "admin_dong_count": int(summary["admin_dong_code"].nunique()),
        "industry_category_count": int(data["업종대분류"].nunique()),
        "complete_admin_dongs": int(summary["consumer_sales_complete_2025"].sum()),
        "incomplete_admin_dongs": int((~summary["consumer_sales_complete_2025"]).sum()),
        "recovered_names": recovered,
    }
    return summary, category, checks


def run(
    input_path: Path = DEFAULT_INPUT,
    reference_path: Path = DEFAULT_REFERENCE,
    output_path: Path = DEFAULT_OUTPUT,
    category_output_path: Path = DEFAULT_CATEGORY_OUTPUT,
    manifest_path: Path = DEFAULT_MANIFEST,
) -> dict[str, object]:
    frame = (
        pd.read_csv(input_path, encoding="utf-8-sig")
        if input_path.suffix.lower() == ".csv"
        else pd.read_excel(input_path)
    )
    reference = pd.read_csv(reference_path, dtype=str)
    summary, category, checks = prepare(frame, reference)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_path, index=False, encoding="utf-8-sig")
    category.to_csv(category_output_path, index=False, encoding="utf-8-sig")
    manifest: dict[str, object] = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "dataset_id": "ECO-BUSAN-CONSUMER-SALES-2025-001",
        "provider": "Busan Metropolitan City (Busan Data Wave)",
        "reference_period": "2025-01/2025-12",
        "period_type": "annual",
        "spatial_unit": "administrative dong (merchant location)",
        "analysis_role": "validation",
        "eligible_for_primary_analysis": False,
        "limitations": (
            "Card consumption is observed at merchant locations, not residents' household "
            "income. It is retained as economic-activity context and is not a direct income "
            "deprivation score. One dong has 11 observed months and is not zero-filled."
        ),
        "aggregation": "day-weighted mean of monthly average-daily values",
        "protected_download_path": PROTECTED_DOWNLOAD.as_posix(),
        "protected_download_sha256": sha256_file(PROTECTED_DOWNLOAD),
        "conversion_note": (
            "The portal download was protected by a non-OOXML wrapper. The parsed workbook "
            "is a value-preserving Excel CSV export; the protected original is retained."
        ),
        "input_path": input_path.as_posix(),
        "input_sha256": sha256_file(input_path),
        "output_path": output_path.as_posix(),
        "output_sha256": sha256_file(output_path),
        "category_output_path": category_output_path.as_posix(),
        "category_output_sha256": sha256_file(category_output_path),
        **checks,
    }
    write_json(manifest_path, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--category-output", type=Path, default=DEFAULT_CATEGORY_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    run(args.input, args.reference, args.output, args.category_output, args.manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
