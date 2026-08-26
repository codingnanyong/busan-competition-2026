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
AGE_PROTECTED_DOWNLOAD = Path(
    "data/raw/busan_data_wave/consumer_sales/2025/"
    "busan_admin_dong_consumer_sales_by_age_download.xlsx"
)
HOUR_PROTECTED_DOWNLOAD = Path(
    "data/raw/busan_data_wave/consumer_sales/2025/"
    "busan_admin_dong_consumer_sales_by_hour_download.xlsx"
)
DEFAULT_INPUT = Path(
    "data/raw/busan_data_wave/consumer_sales/2025/"
    "busan_admin_dong_consumer_sales_by_industry_2023_2025_parsed.csv"
)
DEFAULT_AGE_INPUT = Path(
    "data/raw/busan_data_wave/consumer_sales/2025/"
    "busan_admin_dong_consumer_sales_by_age_2023_2025_parsed.csv"
)
DEFAULT_HOUR_INPUT = Path(
    "data/raw/busan_data_wave/consumer_sales/2025/"
    "busan_admin_dong_consumer_sales_by_hour_2023_2025_parsed.csv"
)
DEFAULT_REFERENCE = Path("docs/data/tables/BUSAN_ADMIN_DONG_CODES_2025.csv")
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


def _map_admin_dongs(
    data: pd.DataFrame, reference: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, str]]]:
    """Map portal names to canonical codes and recover one unnamed residual code."""
    ref = reference[["sigungu_name", "admin_dong_name", "admin_dong_code"]].copy()
    ref["admin_dong_code"] = ref["admin_dong_code"].astype(str)
    ref["portal_name"] = ref["sigungu_name"].astype(str) + " " + ref["admin_dong_name"].astype(str)
    mapping = dict(zip(ref["portal_name"], ref["admin_dong_code"], strict=True))
    data = data.copy()
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
    return data, ref, recovered


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

    data, ref, recovered = _map_admin_dongs(data, reference)

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


def prepare_compositions(
    age_frame: pd.DataFrame,
    hour_frame: pd.DataFrame,
    reference: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Build unscored age and time-band transaction-composition context."""

    def prepare_dimension(
        frame: pd.DataFrame, dimension: str
    ) -> tuple[pd.DataFrame, list[dict[str, str]]]:
        required = {"기준년월", "행정동코드", "행정동명", dimension, "평균이용건수"}
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"Consumer-sales composition is missing columns: {sorted(missing)}")
        data = frame.copy()
        data["기준년월"] = data["기준년월"].astype(str).str.replace(r"\.0$", "", regex=True)
        data = data[data["기준년월"].str.fullmatch(r"2025(0[1-9]|1[0-2])")].copy()
        data["행정동코드"] = data["행정동코드"].astype(str).str.replace(r"\.0$", "", regex=True)
        data["행정동명"] = data["행정동명"].fillna("").astype(str).str.strip()
        data["평균이용건수"] = pd.to_numeric(data["평균이용건수"], errors="raise")
        if data.empty or (data["평균이용건수"] < 0).any():
            raise ValueError("Consumer-sales composition has no valid non-negative 2025 rows")
        if data.duplicated(["기준년월", "행정동코드", dimension]).any():
            raise ValueError("Consumer-sales composition has duplicate monthly dimension rows")
        data, _, recovered = _map_admin_dongs(data, reference)
        data["days"] = pd.to_datetime(data["기준년월"] + "01", format="%Y%m%d").dt.days_in_month
        data["weighted_transactions"] = data["평균이용건수"] * data["days"]
        return data, recovered

    age, age_recovered = prepare_dimension(age_frame, "연령대")
    hour, hour_recovered = prepare_dimension(hour_frame, "시간대")
    age["under_30"] = age["연령대"].isin(["20대미만", "20대"])
    age["senior"] = age["연령대"].eq("60대이상")
    hour["hour"] = pd.to_numeric(hour["시간대"].str.extract(r"(\d{2})", expand=False))
    if hour["hour"].isna().any() or not hour["hour"].between(0, 23).all():
        raise ValueError("Consumer-sales hour bands must be 00시 through 23시")
    hour["late_night"] = hour["hour"].isin([22, 23, 0, 1, 2, 3, 4, 5])
    hour["daytime"] = hour["hour"].between(9, 17)
    hour_month_counts = hour.groupby(["admin_dong_code", "기준년월"]).size()
    hour_band_complete = hour_month_counts.eq(24).groupby("admin_dong_code").all()
    hour_missing_band_records = int((24 - hour_month_counts).clip(lower=0).sum())

    def shares(data: pd.DataFrame, flags: dict[str, str], months_column: str) -> pd.DataFrame:
        total = data.groupby("admin_dong_code")["weighted_transactions"].sum()
        result = pd.DataFrame(index=total.index)
        for flag, output in flags.items():
            selected = data[data[flag]].groupby("admin_dong_code")["weighted_transactions"].sum()
            result[output] = selected.reindex(total.index, fill_value=0) / total * 100
        result[months_column] = data.groupby("admin_dong_code")["기준년월"].nunique()
        return result.reset_index()

    age_summary = shares(
        age,
        {
            "under_30": "consumer_sales_under_30_transaction_share_pct_2025",
            "senior": "consumer_sales_senior_transaction_share_pct_2025",
        },
        "consumer_sales_age_observed_months_2025",
    )
    hour_summary = shares(
        hour,
        {
            "late_night": "consumer_sales_late_night_transaction_share_pct_2025",
            "daytime": "consumer_sales_daytime_transaction_share_pct_2025",
        },
        "consumer_sales_hour_observed_months_2025",
    )
    result = age_summary.merge(
        hour_summary, on="admin_dong_code", how="outer", validate="one_to_one"
    )
    result["consumer_sales_hour_band_complete_2025"] = (
        result["admin_dong_code"].map(hour_band_complete).fillna(False)
    )
    incomplete_hour_bands = ~result["consumer_sales_hour_band_complete_2025"]
    hour_share_columns = [
        "consumer_sales_late_night_transaction_share_pct_2025",
        "consumer_sales_daytime_transaction_share_pct_2025",
    ]
    result.loc[incomplete_hour_bands, hour_share_columns] = pd.NA
    required_complete = result.columns.difference(hour_share_columns)
    if len(result) != len(reference) or result[required_complete].isna().any().any():
        raise ValueError("Consumer-sales compositions require complete canonical-dong coverage")
    checks: dict[str, object] = {
        "age_source_rows_2025": len(age),
        "hour_source_rows_2025": len(hour),
        "composition_admin_dong_count": len(result),
        "age_complete_admin_dongs": int(
            (result["consumer_sales_age_observed_months_2025"] == 12).sum()
        ),
        "hour_complete_admin_dongs": int(
            (result["consumer_sales_hour_observed_months_2025"] == 12).sum()
        ),
        "hour_complete_band_admin_dongs": int(
            result["consumer_sales_hour_band_complete_2025"].sum()
        ),
        "hour_missing_band_records": hour_missing_band_records,
        "age_recovered_names": age_recovered,
        "hour_recovered_names": hour_recovered,
    }
    return result, checks


def run(
    input_path: Path = DEFAULT_INPUT,
    age_input_path: Path = DEFAULT_AGE_INPUT,
    hour_input_path: Path = DEFAULT_HOUR_INPUT,
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
    age_frame = pd.read_csv(age_input_path, encoding="utf-8-sig")
    hour_frame = pd.read_csv(hour_input_path, encoding="utf-8-sig")
    compositions, composition_checks = prepare_compositions(age_frame, hour_frame, reference)
    summary = summary.merge(
        compositions, on="admin_dong_code", how="left", validate="one_to_one"
    )
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
            "deprivation score. One dong has 11 observed months; two dongs have incomplete "
            "hour bands. Missing periods and bands are not zero-filled."
        ),
        "aggregation": "day-weighted mean of monthly average-daily values",
        "protected_download_path": PROTECTED_DOWNLOAD.as_posix(),
        "protected_download_sha256": sha256_file(PROTECTED_DOWNLOAD),
        "conversion_note": (
            "The three portal downloads were protected by non-OOXML wrappers. Their parsed "
            "industry, age, and hour files are value-preserving Excel CSV exports; protected "
            "originals are retained."
        ),
        "input_path": input_path.as_posix(),
        "input_sha256": sha256_file(input_path),
        "age_protected_download_path": AGE_PROTECTED_DOWNLOAD.as_posix(),
        "age_protected_download_sha256": sha256_file(AGE_PROTECTED_DOWNLOAD),
        "age_input_path": age_input_path.as_posix(),
        "age_input_sha256": sha256_file(age_input_path),
        "hour_protected_download_path": HOUR_PROTECTED_DOWNLOAD.as_posix(),
        "hour_protected_download_sha256": sha256_file(HOUR_PROTECTED_DOWNLOAD),
        "hour_input_path": hour_input_path.as_posix(),
        "hour_input_sha256": sha256_file(hour_input_path),
        "output_path": output_path.as_posix(),
        "output_sha256": sha256_file(output_path),
        "category_output_path": category_output_path.as_posix(),
        "category_output_sha256": sha256_file(category_output_path),
        **checks,
        **composition_checks,
    }
    write_json(manifest_path, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--age-input", type=Path, default=DEFAULT_AGE_INPUT)
    parser.add_argument("--hour-input", type=Path, default=DEFAULT_HOUR_INPUT)
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--category-output", type=Path, default=DEFAULT_CATEGORY_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    run(
        args.input,
        args.age_input,
        args.hour_input,
        args.reference,
        args.output,
        args.category_output,
        args.manifest,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
