"""Generate reproducible EDA artifacts for the 2025 candidate profile."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd

from busan_imd.core.artifacts import sha256_file, write_json
from busan_imd.standardization import load_boundaries

DEFAULT_PROFILE = Path(
    "data/processed/standardized/2025/busan_admin_dong_candidate_profile_2025.csv"
)
DEFAULT_DICTIONARY = Path("docs/data/DATA_DICTIONARY_2025.csv")
DEFAULT_BOUNDARIES = Path(
    "data/raw/sgis/admin_boundaries/2025/busan_admin_dong_boundaries_2025_valid.geojson"
)
DEFAULT_OUTPUT_DIR = Path("outputs/eda/2025")
DEFAULT_REPORT = Path("docs/data/manifests/EDA_REPORT_2025.json")
SCORING_ROLE = "provisional_scoring_proxy"
HIGH_CORRELATION_THRESHOLD = 0.8


def numeric_indicator_columns(profile: pd.DataFrame) -> list[str]:
    """Return analyzable numeric columns, excluding booleans and identifiers."""
    excluded = {"admin_dong_code"}
    return [
        column
        for column in profile.columns
        if column not in excluded
        and pd.api.types.is_numeric_dtype(profile[column])
        and not pd.api.types.is_bool_dtype(profile[column])
    ]


def summarize_indicators(
    profile: pd.DataFrame, dictionary: pd.DataFrame
) -> pd.DataFrame:
    """Summarize distributions, missingness, zeroes, and IQR outliers."""
    metadata = dictionary.set_index("column_name")
    rows: list[dict[str, Any]] = []
    for column in numeric_indicator_columns(profile):
        values = pd.to_numeric(profile[column], errors="coerce")
        observed = values.dropna()
        q1 = observed.quantile(0.25)
        q3 = observed.quantile(0.75)
        iqr = q3 - q1
        if observed.empty or iqr == 0:
            outlier_count = 0
        else:
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outlier_count = int(((observed < lower) | (observed > upper)).sum())
        spec = metadata.loc[column]
        rows.append(
            {
                "indicator": column,
                "source_dataset_id": spec["source_dataset_id"],
                "analysis_role": spec["analysis_role"],
                "direction": spec["direction"],
                "quality_warning": spec["quality_warning"],
                "observed_count": int(observed.count()),
                "missing_count": int(values.isna().sum()),
                "missing_rate": round(float(values.isna().mean()), 6),
                "unique_count": int(observed.nunique()),
                "zero_count": int((observed == 0).sum()),
                "zero_rate": round(float((observed == 0).mean()), 6),
                "minimum": round(float(observed.min()), 6),
                "q1": round(float(q1), 6),
                "median": round(float(observed.median()), 6),
                "mean": round(float(observed.mean()), 6),
                "q3": round(float(q3), 6),
                "maximum": round(float(observed.max()), 6),
                "standard_deviation": round(float(observed.std(ddof=1)), 6),
                "skewness": round(float(observed.skew()), 6),
                "iqr_outlier_count": outlier_count,
                "iqr_outlier_rate": round(float(outlier_count / len(observed)), 6),
            }
        )
    return pd.DataFrame(rows).sort_values(["analysis_role", "indicator"]).reset_index(drop=True)


def correlation_outputs(
    profile: pd.DataFrame,
    summary: pd.DataFrame,
    threshold: float = HIGH_CORRELATION_THRESHOLD,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return the scoring-candidate correlation matrix and high-correlation pairs."""
    columns = summary.loc[
        (summary["analysis_role"] == SCORING_ROLE) & (summary["unique_count"] > 1),
        "indicator",
    ].tolist()
    matrix = profile[columns].corr(method="pearson", min_periods=3)
    pairs: list[dict[str, Any]] = []
    for left_index, left in enumerate(columns):
        for right in columns[left_index + 1 :]:
            value = matrix.loc[left, right]
            if pd.notna(value) and abs(value) >= threshold:
                pairs.append(
                    {
                        "indicator_a": left,
                        "indicator_b": right,
                        "pearson_correlation": round(float(value), 6),
                        "absolute_correlation": round(abs(float(value)), 6),
                    }
                )
    high = pd.DataFrame(
        pairs,
        columns=[
            "indicator_a",
            "indicator_b",
            "pearson_correlation",
            "absolute_correlation",
        ],
    )
    if not high.empty:
        high = high.sort_values("absolute_correlation", ascending=False).reset_index(drop=True)
    return matrix, high


def contiguity_edges(boundaries: gpd.GeoDataFrame) -> list[tuple[int, int]]:
    """Return unique queen-contiguity edges for canonical boundary rows."""
    frame = boundaries.reset_index(drop=True)
    edges: set[tuple[int, int]] = set()
    for left, geometry in enumerate(frame.geometry):
        for right in frame.sindex.query(geometry, predicate="touches"):
            right_index = int(right)
            if left < right_index:
                edges.add((left, right_index))
    return sorted(edges)


def morans_i(values: pd.Series, edges: list[tuple[int, int]]) -> float | None:
    """Calculate global Moran's I over an undirected binary adjacency graph."""
    numeric = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    valid = ~np.isnan(numeric)
    centered = numeric - np.nanmean(numeric)
    denominator = float(np.nansum(np.square(centered)))
    valid_edges = [(left, right) for left, right in edges if valid[left] and valid[right]]
    if denominator == 0 or not valid_edges:
        return None
    numerator = sum(2.0 * centered[left] * centered[right] for left, right in valid_edges)
    weight_sum = 2.0 * len(valid_edges)
    return float(valid.sum() / weight_sum * numerator / denominator)


def spatial_outputs(
    profile: pd.DataFrame,
    boundaries: gpd.GeoDataFrame,
    summary: pd.DataFrame,
) -> tuple[pd.DataFrame, list[tuple[int, int]], list[dict[str, str]]]:
    """Calculate global Moran's I for non-constant scoring candidates."""
    frame = boundaries[["admin_dong_code", "geometry"]].copy()
    frame["admin_dong_code"] = frame["admin_dong_code"].astype(str)
    joined = frame.merge(profile, on="admin_dong_code", how="left", validate="one_to_one")
    edges = contiguity_edges(joined)
    connected = {index for edge in edges for index in edge}
    isolated = joined.loc[
        ~joined.index.isin(connected),
        ["admin_dong_code", "sigungu_name", "admin_dong_name"],
    ].to_dict(orient="records")
    rows: list[dict[str, Any]] = []
    candidates = summary.loc[
        (summary["analysis_role"] == SCORING_ROLE) & (summary["unique_count"] > 1),
        "indicator",
    ]
    for column in candidates:
        value = morans_i(joined[column], edges)
        rows.append(
            {
                "indicator": column,
                "morans_i": round(value, 6) if value is not None else None,
                "observed_count": int(joined[column].notna().sum()),
                "contiguity_edge_count": len(edges),
            }
        )
    spatial = pd.DataFrame(rows).sort_values("morans_i", ascending=False).reset_index(drop=True)
    return spatial, edges, isolated


def district_summary(
    profile: pd.DataFrame, summary: pd.DataFrame
) -> pd.DataFrame:
    """Return long-form district summaries for scoring candidates."""
    candidates = summary.loc[
        summary["analysis_role"] == SCORING_ROLE, "indicator"
    ].tolist()
    rows: list[dict[str, Any]] = []
    for district, group in profile.groupby("sigungu_name", sort=True):
        for column in candidates:
            values = pd.to_numeric(group[column], errors="coerce").dropna()
            if values.empty:
                continue
            rows.append(
                {
                    "sigungu_name": district,
                    "indicator": column,
                    "observed_count": int(values.count()),
                    "mean": round(float(values.mean()), 6),
                    "median": round(float(values.median()), 6),
                    "minimum": round(float(values.min()), 6),
                    "maximum": round(float(values.max()), 6),
                }
            )
    return pd.DataFrame(rows)


def build(
    profile: pd.DataFrame,
    dictionary: pd.DataFrame,
    boundaries: gpd.GeoDataFrame,
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    """Build EDA tables and a compact validation report."""
    if len(profile) != 206 or profile["admin_dong_code"].duplicated().any():
        raise ValueError("EDA requires 206 unique administrative-dong rows")
    if set(profile["admin_dong_code"].astype(str)) != set(
        boundaries["admin_dong_code"].astype(str)
    ):
        raise ValueError("Profile and boundary administrative-dong codes do not match")
    summary = summarize_indicators(profile, dictionary)
    correlations, high_correlations = correlation_outputs(profile, summary)
    spatial, edges, isolated = spatial_outputs(profile, boundaries, summary)
    districts = district_summary(profile, summary)
    constant = summary.loc[summary["unique_count"] <= 1, "indicator"].tolist()
    missing = summary.loc[summary["missing_count"] > 0, ["indicator", "missing_count"]]
    report: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "reference_year": 2025,
        "profile_record_count": len(profile),
        "profile_column_count": len(profile.columns),
        "numeric_indicator_count": len(summary),
        "scoring_candidate_numeric_count": int(
            (summary["analysis_role"] == SCORING_ROLE).sum()
        ),
        "constant_numeric_columns": constant,
        "columns_with_missing_values": dict(missing.itertuples(index=False, name=None)),
        "iqr_outlier_count": int(summary["iqr_outlier_count"].sum()),
        "high_correlation_threshold": HIGH_CORRELATION_THRESHOLD,
        "high_correlation_pair_count": len(high_correlations),
        "contiguity_edge_count": len(edges),
        "isolated_admin_dong_count": len(isolated),
        "isolated_admin_dongs": isolated,
        "spatial_indicator_count": len(spatial),
    }
    return {
        "indicator_summary": summary,
        "correlation_matrix": correlations,
        "high_correlations": high_correlations,
        "spatial_autocorrelation": spatial,
        "district_summary": districts,
    }, report


def run(
    profile_path: Path = DEFAULT_PROFILE,
    dictionary_path: Path = DEFAULT_DICTIONARY,
    boundaries_path: Path = DEFAULT_BOUNDARIES,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    """Read canonical inputs and write reproducible EDA artifacts."""
    profile = pd.read_csv(profile_path, dtype={"admin_dong_code": str})
    dictionary = pd.read_csv(dictionary_path)
    boundaries = load_boundaries(boundaries_path)[["admin_dong_code", "geometry"]]
    tables, report = build(profile, dictionary, boundaries)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths: dict[str, str] = {}
    output_hashes: dict[str, str] = {}
    for name, table in tables.items():
        path = output_dir / f"{name}.csv"
        table.to_csv(path, index=name == "correlation_matrix", encoding="utf-8-sig")
        output_paths[name] = path.as_posix()
        output_hashes[name] = sha256_file(path)
    report.update(
        {
            "profile_path": profile_path.as_posix(),
            "profile_sha256": sha256_file(profile_path),
            "dictionary_path": dictionary_path.as_posix(),
            "dictionary_sha256": sha256_file(dictionary_path),
            "boundaries_path": boundaries_path.as_posix(),
            "boundaries_sha256": sha256_file(boundaries_path),
            "output_paths": output_paths,
            "output_sha256": output_hashes,
        }
    )
    write_json(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--dictionary", type=Path, default=DEFAULT_DICTIONARY)
    parser.add_argument("--boundaries", type=Path, default=DEFAULT_BOUNDARIES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run(
        args.profile,
        args.dictionary,
        args.boundaries,
        args.output_dir,
        args.report,
    )
    print(
        f"analyzed {report['profile_record_count']} administrative dongs and "
        f"{report['numeric_indicator_count']} numeric indicators"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
