"""Infer 2025 administrative-dong basic-livelihood counts under district constraints."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler

from busan_imd.core.artifacts import sha256_file, write_json

DATASET_ID = "INC-BLF-INFERRED-2025-001"
DEFAULT_PROFILE_PATH = Path(
    "data/processed/standardized/2025/busan_admin_dong_candidate_profile_2025.csv"
)
DEFAULT_DISTRICT_TOTALS_PATH = Path(
    "data/raw/supplemental/welfare_beneficiaries/welfare_beneficiaries_by_sigungu_2025.csv"
)
DEFAULT_OUTPUT_PATH = Path("data/processed/candidates/2025/basic_livelihood_inferred_2025.csv")
DEFAULT_MANIFEST_PATH = Path("docs/data/manifests/BASIC_LIVELIHOOD_INFERENCE_MANIFEST_2025.json")


@dataclass(frozen=True)
class PatternSource:
    district: str
    path: Path
    name_column: str
    people_columns: tuple[str, ...]
    household_columns: tuple[str, ...]
    reference_period: str
    dataset_id: str
    excluded_names: tuple[str, ...] = ()
    name_remove: str = ""


PATTERN_SOURCES = (
    PatternSource(
        "북구",
        Path("data/raw/audit/3069319.download"),
        "구분",
        ("맞춤형급여인원",),
        ("맞춤형급여 가구",),
        "2025-12-31",
        "INC-BLF-BUKGU-001",
        ("북구",),
    ),
    PatternSource(
        "동구",
        Path("data/raw/audit/15023207.download"),
        "구분",
        ("일반수급자(인원)",),
        ("일반수급자(가구)",),
        "2025-11-18",
        "INC-BLF-DONGGU-001",
        ("소계", "동구"),
    ),
    PatternSource(
        "금정구",
        Path("data/raw/audit/3073078.download"),
        "동명",
        ("일반수급자 수급권자수", "조건부수급자 수급권자수", "특례수급자 수급권자수"),
        ("일반수급자 가구수", "조건부수급자 가구수", "특례수급자 가구수"),
        "2026-05-15",
        "INC-BLF-GEUMJEONG-001",
        ("소계", "금정구(시설)"),
    ),
    PatternSource(
        "남구",
        Path("data/raw/audit/15113711.download"),
        "동",
        ("수급권자수",),
        ("가구수",),
        "2024-12-31",
        "INC-BLF-NAMGU-001",
    ),
    PatternSource(
        "해운대구",
        Path(
            "data/raw/supplemental/basic_livelihood/busan_haeundae_basic_livelihood_2025_08_20.csv"
        ),
        "행정동",
        ("기초생계급여 수급권자수",),
        ("기초생계급여 가구수",),
        "2025-08-20",
        "INC-BLF-HAEUNDAE-2025-001",
        ("해운대구(시설)",),
    ),
    PatternSource(
        "수영구",
        Path("data/raw/audit/15026899.download"),
        "구분",
        ("생계급여 수급자(인원)",),
        ("생계급여 수급자(가구)",),
        "2026-06-30",
        "INC-BLF-SUYEONG-001",
        ("수영구",),
        "제",
    ),
)

MODEL_FEATURES = (
    "elderly_alone_latest_per_1000_population_2025_validation",
    "old_house_share_30plus_2024_lower_bound_pct",
    "households_2025",
    "total_population_2025",
)
MODEL_PATTERN_DATASET_IDS = "|".join(source.dataset_id for source in PATTERN_SOURCES)
MODEL_FEATURE_DATASET_IDS = "|".join(
    (
        "SOC-BUSAN-ELDERLY-ALONE-001",
        "HOU-SGIS-OLD-001",
        "DEM-MOIS-POP-2025-001",
    )
)


def read_csv_fallback(path: Path, **kwargs: Any) -> pd.DataFrame:
    """Read UTF-8 BOM or CP949 public-data CSV files."""
    last_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8-sig", "cp949"):
        try:
            return pd.read_csv(path, encoding=encoding, **kwargs)
        except UnicodeDecodeError as error:
            last_error = error
    assert last_error is not None
    raise last_error


def _number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="raise")


def load_district_totals(path: Path) -> pd.DataFrame:
    """Load exact December 2025 Busan district totals for matched benefits."""
    source = read_csv_fallback(path)
    rows = source[
        (source["사업명"] == "기초생활보장(맞춤형급여)")
        & (source["시도"] == "부산광역시")
        & (source["기준년월"].astype(str).str.replace("-", "") == "202512")
    ].copy()
    rows["people_total"] = _number(rows["수급권자수"]).astype("int64")
    rows["household_total"] = _number(rows["수급가구수"]).astype("int64")
    if len(rows) != 16 or rows["시군구"].duplicated().any():
        raise ValueError(f"Expected 16 unique Busan district totals, received {len(rows)}")
    return rows[["시군구", "people_total", "household_total"]].rename(
        columns={"시군구": "sigungu_name"}
    )


def load_pattern(source: PatternSource) -> pd.DataFrame:
    """Load one district's observed dong distribution without treating it as a total."""
    frame = read_csv_fallback(source.path)
    if source.district == "남구":
        frame = frame[frame["자격"] == "기초생계급여"].copy()
    frame = frame[~frame[source.name_column].astype(str).isin(source.excluded_names)].copy()
    frame["admin_dong_name"] = frame[source.name_column].astype(str).str.strip()
    if source.name_remove:
        frame["admin_dong_name"] = frame["admin_dong_name"].str.replace(
            source.name_remove, "", regex=False
        )
    frame["pattern_people"] = sum(_number(frame[column]) for column in source.people_columns)
    frame["pattern_households"] = sum(_number(frame[column]) for column in source.household_columns)
    if frame["admin_dong_name"].duplicated().any():
        raise ValueError(f"Duplicate dong names in {source.dataset_id}")
    return frame[["admin_dong_name", "pattern_people", "pattern_households"]]


def _model_columns(profile: pd.DataFrame) -> pd.DataFrame:
    values = pd.DataFrame(index=profile.index)
    values["elderly_rate"] = pd.to_numeric(profile[MODEL_FEATURES[0]], errors="coerce")
    values["old_house_share"] = pd.to_numeric(profile[MODEL_FEATURES[1]], errors="coerce")
    households = pd.to_numeric(profile[MODEL_FEATURES[2]], errors="raise")
    population = pd.to_numeric(profile[MODEL_FEATURES[3]], errors="raise")
    values["single_person_pressure"] = households / population * 1_000
    return values.fillna(values.median())


def fit_relative_risk_model(
    profile: pd.DataFrame, patterns: pd.DataFrame
) -> tuple[np.ndarray, dict[str, Any]]:
    """Fit within-district relative recipient rates and predict all dongs."""
    features = _model_columns(profile)
    feature_names = list(features.columns)
    model_frame = pd.concat(
        [profile[["admin_dong_code", "sigungu_name", "total_population_2025"]], features],
        axis=1,
    )
    training = model_frame.merge(
        patterns[["admin_dong_code", "pattern_people"]],
        on="admin_dong_code",
        how="inner",
        validate="one_to_one",
    )
    if len(training) < 50:
        raise ValueError(f"Insufficient pattern coverage for inference: {len(training)} dongs")
    rates = training["pattern_people"] / training["total_population_2025"] * 1_000
    log_rates = np.log(rates.clip(lower=0.01))
    target = log_rates - log_rates.groupby(training["sigungu_name"]).transform("mean")

    scaler = StandardScaler()
    x_train = scaler.fit_transform(training[feature_names])
    model = Ridge(alpha=2.0)
    model.fit(x_train, target)
    fitted = model.predict(x_train)
    predicted = model.predict(scaler.transform(features[feature_names]))
    risk = np.exp(predicted)
    return risk, {
        "model": "ridge regression on within-district centered log recipient rate",
        "ridge_alpha": 2.0,
        "training_admin_dongs": len(training),
        "training_districts": sorted(training["sigungu_name"].unique()),
        "features": feature_names,
        "coefficients": {
            name: round(float(value), 8)
            for name, value in zip(feature_names, model.coef_, strict=True)
        },
        "training_r2": round(float(r2_score(target, fitted)), 6),
    }


def largest_remainder(weights: pd.Series, total: int) -> pd.Series:
    """Allocate an integer total proportionally while preserving the exact sum."""
    weights = pd.to_numeric(weights, errors="raise").astype(float)
    if (weights < 0).any() or not np.isfinite(weights).all() or weights.sum() <= 0:
        raise ValueError("Allocation weights must be finite, non-negative, and non-zero")
    quota = weights / weights.sum() * int(total)
    allocated = np.floor(quota).astype("int64")
    remainder = int(total) - int(allocated.sum())
    order = (quota - allocated).sort_values(ascending=False, kind="stable").index[:remainder]
    allocated.loc[order] += 1
    return allocated


def infer(
    profile_path: Path = DEFAULT_PROFILE_PATH,
    district_totals_path: Path = DEFAULT_DISTRICT_TOTALS_PATH,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Create a 206-dong inferred profile constrained to exact 2025 district totals."""
    profile = read_csv_fallback(profile_path, dtype={"admin_dong_code": str})
    if len(profile) != 206 or profile["admin_dong_code"].duplicated().any():
        raise ValueError("Inference profile must contain 206 unique administrative dongs")
    totals = load_district_totals(district_totals_path)

    pattern_frames: list[pd.DataFrame] = []
    pattern_metadata: list[dict[str, Any]] = []
    for source in PATTERN_SOURCES:
        pattern = load_pattern(source)
        canonical = profile.loc[
            profile["sigungu_name"] == source.district,
            ["admin_dong_code", "admin_dong_name"],
        ]
        matched = canonical.merge(pattern, on="admin_dong_name", how="left", validate="one_to_one")
        if matched[["pattern_people", "pattern_households"]].isna().any().any():
            missing = matched.loc[matched["pattern_people"].isna(), "admin_dong_name"].tolist()
            raise ValueError(f"{source.dataset_id} missing canonical dongs: {missing}")
        matched["sigungu_name"] = source.district
        matched["pattern_source_dataset_id"] = source.dataset_id
        matched["pattern_source_period"] = source.reference_period
        pattern_frames.append(matched)
        pattern_metadata.append(
            {
                "dataset_id": source.dataset_id,
                "district": source.district,
                "reference_period": source.reference_period,
                "path": source.path.as_posix(),
                "sha256": sha256_file(source.path),
                "matched_admin_dongs": len(matched),
                "pattern_definition": (
                    "matched-benefit or general-recipient distribution"
                    if source.district in {"북구", "동구", "금정구"}
                    else "livelihood-benefit-only distribution"
                ),
            }
        )
    patterns = pd.concat(pattern_frames, ignore_index=True)
    risk, model_metadata = fit_relative_risk_model(profile, patterns)

    output = profile[
        [
            "admin_dong_code",
            "sigungu_name",
            "admin_dong_name",
            "total_population_2025",
            "households_2025",
        ]
    ].copy()
    output["_model_risk"] = risk
    output = output.merge(
        patterns[
            [
                "admin_dong_code",
                "pattern_people",
                "pattern_households",
                "pattern_source_dataset_id",
                "pattern_source_period",
            ]
        ],
        on="admin_dong_code",
        how="left",
        validate="one_to_one",
    ).merge(totals, on="sigungu_name", how="left", validate="many_to_one")
    if output[["people_total", "household_total"]].isna().any().any():
        raise ValueError("A canonical district has no exact December 2025 total")

    output["basic_livelihood_recipients_2025_inferred"] = 0
    output["basic_livelihood_households_2025_inferred"] = 0
    output["allocation_method"] = ""
    for _district, index in output.groupby("sigungu_name", sort=False).groups.items():
        rows = output.loc[index]
        has_pattern = rows["pattern_people"].notna().all()
        people_weights = (
            rows["pattern_people"]
            if has_pattern
            else rows["total_population_2025"] * rows["_model_risk"]
        )
        household_weights = (
            rows["pattern_households"]
            if has_pattern
            else rows["households_2025"] * rows["_model_risk"]
        )
        output.loc[index, "basic_livelihood_recipients_2025_inferred"] = largest_remainder(
            people_weights, int(rows["people_total"].iloc[0])
        ).to_numpy()
        output.loc[index, "basic_livelihood_households_2025_inferred"] = largest_remainder(
            household_weights, int(rows["household_total"].iloc[0])
        ).to_numpy()
        output.loc[index, "allocation_method"] = (
            "observed_dong_pattern_rescaled_to_2025_district_total"
            if has_pattern
            else "ridge_relative_risk_rescaled_to_2025_district_total"
        )

    output["basic_livelihood_recipients_per_1000_population_2025_inferred"] = (
        output["basic_livelihood_recipients_2025_inferred"]
        / output["total_population_2025"]
        * 1_000
    ).round(6)
    output["is_inferred"] = True
    output["value_status"] = "inferred_not_observed"
    output["district_total_reference_period"] = "2025-12"
    output["district_total_source_dataset_id"] = "INC-WELFARE-SIGUNGU-2025-001"
    model_rows = output["pattern_source_dataset_id"].isna()
    output["inference_pattern_source_dataset_ids"] = output["pattern_source_dataset_id"]
    output.loc[model_rows, "inference_pattern_source_dataset_ids"] = MODEL_PATTERN_DATASET_IDS
    output["inference_feature_source_dataset_ids"] = "not_used"
    output.loc[model_rows, "inference_feature_source_dataset_ids"] = MODEL_FEATURE_DATASET_IDS
    output["inference_basis"] = "observed_dong_pattern_plus_observed_2025_district_total"
    output.loc[model_rows, "inference_basis"] = (
        "ridge_relative_risk_plus_observed_2025_district_total"
    )
    output["inference_quality_tier"] = "C1_observed_pattern_rescaled"
    output.loc[model_rows, "inference_quality_tier"] = "C2_model_pattern_rescaled"
    output.loc[model_rows, "pattern_source_dataset_id"] = DATASET_ID
    output.loc[output["pattern_source_period"].isna(), "pattern_source_period"] = "model_based"

    reconciled = output.groupby("sigungu_name", as_index=False).agg(
        inferred_people=("basic_livelihood_recipients_2025_inferred", "sum"),
        inferred_households=("basic_livelihood_households_2025_inferred", "sum"),
        people_total=("people_total", "first"),
        household_total=("household_total", "first"),
    )
    if not (reconciled["inferred_people"] == reconciled["people_total"]).all():
        raise ValueError("Inferred recipient counts do not reconcile to district totals")
    if not (reconciled["inferred_households"] == reconciled["household_total"]).all():
        raise ValueError("Inferred household counts do not reconcile to district totals")
    recipients_exceed_population = (
        output["basic_livelihood_recipients_2025_inferred"] > output["total_population_2025"]
    )
    if recipients_exceed_population.any():
        raise ValueError("An inferred recipient count exceeds the dong population")

    columns = [
        "admin_dong_code",
        "sigungu_name",
        "admin_dong_name",
        "total_population_2025",
        "households_2025",
        "basic_livelihood_recipients_2025_inferred",
        "basic_livelihood_households_2025_inferred",
        "basic_livelihood_recipients_per_1000_population_2025_inferred",
        "allocation_method",
        "pattern_source_dataset_id",
        "pattern_source_period",
        "district_total_reference_period",
        "district_total_source_dataset_id",
        "inference_pattern_source_dataset_ids",
        "inference_feature_source_dataset_ids",
        "inference_basis",
        "inference_quality_tier",
        "is_inferred",
        "value_status",
    ]
    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "dataset_id": DATASET_ID,
        "primary_reference_year": 2025,
        "reference_period": "2025-12",
        "analysis_role": "provisional_scoring_proxy",
        "spatial_unit": "administrative dong",
        "record_count": len(output),
        "district_count": len(reconciled),
        "district_totals_are_observed": True,
        "admin_dong_values_are_inferred": True,
        "observed_pattern_districts": sorted(patterns["sigungu_name"].unique()),
        "model_pattern_districts": sorted(
            set(output["sigungu_name"]) - set(patterns["sigungu_name"])
        ),
        "observed_pattern_admin_dongs": len(patterns),
        "district_people_total": int(totals["people_total"].sum()),
        "district_household_total": int(totals["household_total"].sum()),
        "district_totals_source": {
            "dataset_id": "INC-WELFARE-SIGUNGU-2025-001",
            "path": district_totals_path.as_posix(),
            "sha256": sha256_file(district_totals_path),
        },
        "profile_source": {
            "path": profile_path.as_posix(),
            "sha256": sha256_file(profile_path),
        },
        "pattern_sources": pattern_metadata,
        "model": model_metadata,
        "lineage": {
            "district_total_dataset_id": "INC-WELFARE-SIGUNGU-2025-001",
            "model_pattern_dataset_ids": [source.dataset_id for source in PATTERN_SOURCES],
            "model_feature_dataset_ids": {
                "elderly_rate": "SOC-BUSAN-ELDERLY-ALONE-001",
                "old_house_share": "HOU-SGIS-OLD-001",
                "single_person_pressure": "DEM-MOIS-POP-2025-001",
            },
            "row_level_lineage_columns": [
                "district_total_source_dataset_id",
                "inference_pattern_source_dataset_ids",
                "inference_feature_source_dataset_ids",
                "inference_basis",
                "inference_quality_tier",
                "value_status",
            ],
        },
        "integerization": "largest remainder within each district",
        "limitations": (
            "Only the 16 district totals are observed December 2025 matched-benefit counts. "
            "All 206 administrative-dong values are inferred. Six districts use disclosed "
            "dong patterns from varying reference dates or benefit subsets; ten districts use "
            "a ridge relative-risk model. The values must not be represented as observed counts "
            "and require sensitivity analysis before final IMD publication."
        ),
    }
    return output[columns].sort_values("admin_dong_code").reset_index(drop=True), manifest


def validate_manifest(manifest: dict[str, Any], root: Path = Path(".")) -> None:
    """Validate the inference disclosure, coverage, and optional output checksum."""
    if manifest.get("dataset_id") != DATASET_ID:
        raise ValueError("Unexpected basic-livelihood inference dataset id")
    if manifest.get("record_count") != 206 or manifest.get("district_count") != 16:
        raise ValueError("Basic-livelihood inference must cover 206 dongs and 16 districts")
    if manifest.get("district_totals_are_observed") is not True:
        raise ValueError("District totals must be identified as observed")
    if manifest.get("admin_dong_values_are_inferred") is not True:
        raise ValueError("Dong values must be explicitly identified as inferred")
    output_path = root / str(manifest.get("output_path", ""))
    if output_path.is_file() and sha256_file(output_path) != manifest.get("output_sha256"):
        raise ValueError(f"Basic-livelihood output checksum mismatch: {output_path}")


def write_outputs(
    output: pd.DataFrame,
    manifest: dict[str, Any],
    output_path: Path = DEFAULT_OUTPUT_PATH,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> dict[str, Any]:
    """Write the inferred candidate and its committed, secret-free manifest."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False, encoding="utf-8-sig")
    document = dict(manifest)
    document["output_path"] = output_path.as_posix()
    document["output_sha256"] = sha256_file(output_path)
    validate_manifest(document)
    write_json(manifest_path, document)
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE_PATH)
    parser.add_argument("--district-totals", type=Path, default=DEFAULT_DISTRICT_TOTALS_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    args = parser.parse_args()
    output, manifest = infer(args.profile, args.district_totals)
    document = write_outputs(output, manifest, args.output, args.manifest)
    print(
        "inferred basic-livelihood counts: "
        f"{document['record_count']} dongs / {document['district_people_total']} people"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
