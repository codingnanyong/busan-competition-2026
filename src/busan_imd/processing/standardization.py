"""Standardize collected candidate data to the 2025 Busan administrative-dong geography."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import wkt

from busan_imd.core.artifacts import sha256_file, write_json

REFERENCE_CRS = "EPSG:5179"
REFERENCE_YEAR = 2025
EXPECTED_DONG_COUNT = 206
DEFAULT_OUTPUT_DIR = Path("data/processed/standardized/2025")
DEFAULT_REPORT_PATH = Path("docs/data/manifests/STANDARDIZATION_REPORT_2025.json")


@dataclass(frozen=True)
class SourcePaths:
    boundaries: Path = Path(
        "data/raw/sgis/admin_boundaries/2025/busan_admin_dong_boundaries_2025_valid.geojson"
    )
    population: Path = Path(
        "data/raw/mois/resident_population/2025/busan_resident_population_admin_dong_2025_12.csv"
    )
    employment: Path = Path("data/raw/collection/EMP-SGIS-001/sgis_company_2024.json")
    housing: Path = Path("data/raw/sgis/housing/2024/busan_admin_dong_old_housing_proxy_2025.csv")
    basic_livelihood: Path = Path(
        "data/processed/candidates/2025/basic_livelihood_inferred_2025.csv"
    )
    elderly: Path = Path(
        "data/raw/supplemental/elderly_alone/busan_elderly_alone_latest_by_admin_dong.csv"
    )
    bus_stops: Path = Path("data/raw/bus_stops/2025/busan_bus_stops_20250121.zip")
    route_stops_current: Path = Path(
        "data/raw/supplemental/bus_service_current/busan_bus_route_stops_current.csv"
    )
    routes_current: Path = Path(
        "data/raw/supplemental/bus_service_current/busan_bus_routes_current.csv"
    )
    route_usage: Path = Path("data/processed/candidates/2025/bus_route_usage_2025.csv")
    bus_boarding_2023: Path = Path(
        "data/raw/supplemental/bus_boarding/busan_bus_boarding_alighting_2023.csv"
    )
    hospitals: Path = Path(
        "data/raw/public_data_portal/healthcare_facilities/HLT-HOSPITAL-001/"
        "busan_hospitals_operating_2025_12_31.csv"
    )
    clinics: Path = Path(
        "data/raw/public_data_portal/healthcare_facilities/HLT-CLINIC-001/"
        "busan_clinics_operating_2025_12_31.csv"
    )
    pharmacies: Path = Path(
        "data/raw/public_data_portal/healthcare_facilities/HLT-PHARMACY-001/"
        "busan_pharmacies_operating_2025_12_31.csv"
    )
    aed: Path = Path("data/raw/collection/HLT-AED-001/response.json")
    cctv: Path = Path(
        "data/raw/supplemental/crime_prevention_cctv/busan_crime_prevention_cctv_2025.csv"
    )
    heat_shelters: Path = Path("data/raw/audit/15152994.download")
    living_population: Path = Path("data/processed/candidates/2025/living_population_2025.csv")
    schools: Path = Path("data/processed/candidates/2025/school_counts_2025.csv")
    air_exposure: Path = Path("data/processed/candidates/2025/air_exposure_idw_2025.csv")


def read_csv_fallback(path: Path, **kwargs: Any) -> pd.DataFrame:
    """Read portal CSVs that may be UTF-8 BOM or CP949 encoded."""
    last_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8-sig", "cp949"):
        try:
            return pd.read_csv(path, encoding=encoding, **kwargs)
        except UnicodeDecodeError as error:
            last_error = error
    assert last_error is not None
    raise last_error


def load_boundaries(path: Path) -> gpd.GeoDataFrame:
    """Load and validate the immutable 2025 canonical geography."""
    boundaries = gpd.read_file(path)
    if boundaries.crs is None:
        raise ValueError("Administrative boundaries have no CRS")
    boundaries = boundaries.to_crs(REFERENCE_CRS)
    boundaries["admin_dong_code"] = boundaries["adm_cd"].astype(str)
    if len(boundaries) != EXPECTED_DONG_COUNT:
        raise ValueError(f"Expected 206 boundaries, received {len(boundaries)}")
    if boundaries["admin_dong_code"].duplicated().any():
        raise ValueError("Administrative boundary codes are not unique")
    if not boundaries["admin_dong_code"].str.fullmatch(r"21\d{6}").all():
        raise ValueError("Administrative boundary codes are not 2025 Busan SGIS codes")
    if boundaries.geometry.isna().any() or boundaries.geometry.is_empty.any():
        raise ValueError("Administrative boundaries contain missing or empty geometry")
    if not boundaries.geometry.is_valid.all():
        raise ValueError("Administrative boundaries contain invalid geometry")
    return boundaries[["admin_dong_code", "adm_nm", "geometry"]].copy()


def validate_code_frame(
    frame: pd.DataFrame,
    boundaries: gpd.GeoDataFrame,
    *,
    dataset_id: str,
    code_column: str,
    expected_complete: bool,
) -> dict[str, Any]:
    """Validate code shape, uniqueness, and membership in the canonical code set."""
    codes = frame[code_column].astype(str)
    reference_codes = set(boundaries["admin_dong_code"])
    duplicates = int(codes.duplicated().sum())
    malformed = int((~codes.str.fullmatch(r"21\d{6}")).sum())
    unmatched_codes = sorted(set(codes) - reference_codes)
    missing_codes = sorted(reference_codes - set(codes))
    if duplicates or malformed or unmatched_codes or (expected_complete and missing_codes):
        raise ValueError(
            f"{dataset_id} code validation failed: duplicates={duplicates}, "
            f"malformed={malformed}, unmatched={unmatched_codes}, missing={missing_codes}"
        )
    return {
        "dataset_id": dataset_id,
        "join_method": "canonical_code",
        "input_records": len(frame),
        "matched_records": len(frame) - len(unmatched_codes),
        "unmatched_records": len(unmatched_codes),
        "duplicate_code_records": duplicates,
        "matched_admin_dongs": len(set(codes) & reference_codes),
        "missing_admin_dongs": len(missing_codes),
        "match_rate": 1.0 if len(frame) else 0.0,
    }


def points_from_xy(
    frame: pd.DataFrame, x_column: str, y_column: str, crs: str
) -> tuple[gpd.GeoDataFrame, int]:
    """Create point geometry while excluding missing or non-finite coordinates."""
    working = frame.copy()
    working[x_column] = pd.to_numeric(working[x_column], errors="coerce")
    working[y_column] = pd.to_numeric(working[y_column], errors="coerce")
    valid = working[x_column].notna() & working[y_column].notna()
    missing_count = int((~valid).sum())
    working = working.loc[valid].copy()
    geometry = gpd.points_from_xy(working[x_column], working[y_column])
    return gpd.GeoDataFrame(working, geometry=geometry, crs=crs), missing_count


def spatial_counts(
    boundaries: gpd.GeoDataFrame,
    points: gpd.GeoDataFrame,
    *,
    dataset_id: str,
    input_records: int,
    coordinate_missing: int,
) -> tuple[pd.Series, dict[str, Any]]:
    """Count points within dongs and report every unmatched or duplicate match."""
    source_crs = str(points.crs)
    points = points.to_crs(boundaries.crs).reset_index(drop=True)
    points["_source_row"] = points.index
    valid = points.geometry.notna() & ~points.geometry.is_empty & points.geometry.is_valid
    coordinate_invalid = int((~valid).sum())
    points = points.loc[valid].copy()
    joined = gpd.sjoin(
        points[["_source_row", "geometry"]],
        boundaries[["admin_dong_code", "geometry"]],
        how="left",
        predicate="within",
    )
    duplicate_matches = int(joined["_source_row"].duplicated().sum())
    matched = joined[joined["admin_dong_code"].notna()].copy()
    matched_source_rows = matched["_source_row"].nunique()
    unmatched = len(points) - matched_source_rows
    counts = matched.groupby("admin_dong_code")["_source_row"].nunique().astype("int64")
    denominator = input_records - coordinate_missing - coordinate_invalid
    report = {
        "dataset_id": dataset_id,
        "join_method": "point_within_2025_admin_dong",
        "source_crs": source_crs,
        "target_crs": str(boundaries.crs),
        "input_records": input_records,
        "coordinate_missing_records": coordinate_missing,
        "coordinate_invalid_records": coordinate_invalid,
        "matched_records": int(matched_source_rows),
        "unmatched_records": int(unmatched),
        "duplicate_point_matches": duplicate_matches,
        "matched_admin_dongs": int(counts.index.nunique()),
        "match_rate": round(matched_source_rows / denominator, 6) if denominator else 0.0,
    }
    return counts, report


def boundary_distance_decay_access(
    boundaries: gpd.GeoDataFrame,
    points: gpd.GeoDataFrame,
    *,
    dataset_id: str,
    cutoff_m: float,
    decay_m: float,
) -> tuple[pd.Series, dict[str, Any]]:
    """Count in-dong facilities fully and nearby out-of-dong facilities with decay."""
    if cutoff_m <= 0 or decay_m <= 0:
        raise ValueError("Distance-decay cutoff and scale must be positive")
    located = points.to_crs(boundaries.crs)
    valid = located.geometry.notna() & ~located.geometry.is_empty & located.geometry.is_valid
    located = located.loc[valid].copy()
    values: dict[str, float] = {}
    for dong in boundaries.itertuples(index=False):
        distances = located.geometry.distance(dong.geometry).to_numpy(dtype=float)
        nearby = distances <= cutoff_m
        values[str(dong.admin_dong_code)] = float(
            np.exp(-distances[nearby] / decay_m).sum()
        )
    result = pd.Series(values, dtype=float)
    report = {
        "dataset_id": dataset_id,
        "join_method": "polygon_distance_with_exponential_decay",
        "input_records": len(points),
        "valid_coordinate_records": len(located),
        "matched_admin_dongs": len(result),
        "match_rate": 1.0 if len(result) else 0.0,
        "cutoff_m": cutoff_m,
        "decay_m": decay_m,
        "inside_polygon_weight": 1.0,
        "decision": "validation_only",
        "limitation": (
            "Straight-line polygon distance includes nearby cross-boundary supply but does not "
            "represent entrances, walking networks, capacity, or facilities outside Busan."
        ),
    }
    return result, report


def _map_current_route_stops(
    boundaries: gpd.GeoDataFrame,
    bus_stops: gpd.GeoDataFrame,
    route_stops: pd.DataFrame,
) -> tuple[gpd.GeoDataFrame, int]:
    """Locate current BIMS route-stop records on the dated 2025 stop inventory."""
    required_stop_columns = {"buslinenum", "nodeid", "arsno"}
    required_inventory_columns = {"bstopid", "arsno", "geometry"}
    if not required_stop_columns <= set(route_stops.columns):
        raise ValueError("Current route stops are missing route, stop, or coordinate fields")
    if not required_inventory_columns <= set(bus_stops.columns):
        raise ValueError("2025 bus-stop inventory is missing stop IDs or geometry")

    def normalized_id(values: pd.Series) -> pd.Series:
        return values.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)

    stops = route_stops.copy()
    stops["buslinenum"] = stops["buslinenum"].astype(str).str.strip()
    stops["nodeid"] = normalized_id(stops["nodeid"])
    stops["arsno"] = normalized_id(stops["arsno"])
    inventory = bus_stops[["bstopid", "arsno", "geometry"]].copy()
    inventory["bstopid"] = normalized_id(inventory["bstopid"])
    inventory["arsno"] = normalized_id(inventory["arsno"])
    if inventory["bstopid"].duplicated().any():
        raise ValueError("2025 bus-stop inventory requires unique bstopid values")
    by_node = inventory.set_index("bstopid")["geometry"]
    by_ars = inventory.drop_duplicates("arsno").set_index("arsno")["geometry"]
    geometry = stops["nodeid"].map(by_node)
    geometry = geometry.where(geometry.notna(), stops["arsno"].map(by_ars))
    coordinate_missing = int(geometry.isna().sum())
    points = gpd.GeoDataFrame(stops, geometry=geometry, crs=bus_stops.crs)
    points = points[points.geometry.notna()].to_crs(boundaries.crs).reset_index(drop=True)
    point_columns = ["buslinenum", "nodeid", "arsno", "geometry"]
    if "bstopnm" in points.columns:
        point_columns.append("bstopnm")
    joined = gpd.sjoin(
        points[point_columns],
        boundaries[["admin_dong_code", "geometry"]],
        how="left",
        predicate="within",
    )
    mapped = joined[joined["admin_dong_code"].notna()].copy()
    mapped = mapped.drop_duplicates(["buslinenum", "nodeid", "admin_dong_code"])
    return mapped, coordinate_missing


def _minutes_since_midnight(value: object) -> float:
    text = str(value).strip()
    if not text or text.lower() == "nan" or ":" not in text:
        return np.nan
    hours, minutes = text.split(":", maxsplit=1)
    return float(int(hours) * 60 + int(minutes))


def route_demand_access(
    boundaries: gpd.GeoDataFrame,
    bus_stops: gpd.GeoDataFrame,
    route_stops: pd.DataFrame,
    route_usage: pd.DataFrame,
    routes_current: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Map 2025 route demand and current service supply through BIMS topology."""
    required_usage_columns = {"route_no", "card_trip_count_2025"}
    if not required_usage_columns <= set(route_usage.columns):
        raise ValueError("2025 route usage is missing route_no or card_trip_count_2025")

    mapped, coordinate_missing = _map_current_route_stops(
        boundaries, bus_stops, route_stops
    )

    usage = route_usage.copy()
    usage["route_no"] = usage["route_no"].astype(str).str.strip()
    usage["card_trip_count_2025"] = pd.to_numeric(
        usage["card_trip_count_2025"], errors="raise"
    )
    if usage["route_no"].duplicated().any() or (usage["card_trip_count_2025"] < 0).any():
        raise ValueError("2025 route usage requires unique routes and non-negative counts")
    matched_route_numbers = set(mapped["buslinenum"]) & set(usage["route_no"])
    route_dong = mapped[mapped["buslinenum"].isin(matched_route_numbers)][
        ["buslinenum", "admin_dong_code"]
    ].drop_duplicates()
    route_dong = route_dong.merge(
        usage[["route_no", "card_trip_count_2025"]],
        left_on="buslinenum",
        right_on="route_no",
        how="left",
        validate="many_to_one",
    )
    route_dong["route_demand_weight"] = np.log1p(route_dong["card_trip_count_2025"])
    composition_columns = {
        "multi_leg_card_trip_count_2025",
        "youth_child_card_trip_count_2025",
    }
    if composition_columns <= set(usage.columns):
        route_dong = route_dong.merge(
            usage[["route_no", *sorted(composition_columns)]],
            on="route_no",
            how="left",
            validate="many_to_one",
        )
    by_dong = (
        route_dong.groupby("admin_dong_code", observed=True)
        .agg(
            matched_bus_routes_2025_current_proxy=("buslinenum", "nunique"),
            demand_weighted_bus_route_access_2025_current_proxy=(
                "route_demand_weight",
                "sum",
            ),
        )
        .reset_index()
    )
    if composition_columns <= set(route_dong.columns):
        composition = route_dong.groupby("admin_dong_code", observed=True).agg(
            reachable_card_trip_count_2025_current_proxy=("card_trip_count_2025", "sum"),
            reachable_multi_leg_card_trip_count_2025_current_proxy=(
                "multi_leg_card_trip_count_2025",
                "sum",
            ),
            reachable_youth_child_card_trip_count_2025_current_proxy=(
                "youth_child_card_trip_count_2025",
                "sum",
            ),
        )
        composition["reachable_multi_leg_trip_share_pct_2025_current_proxy"] = (
            composition["reachable_multi_leg_card_trip_count_2025_current_proxy"]
            / composition["reachable_card_trip_count_2025_current_proxy"]
            * 100
        )
        composition["reachable_youth_child_trip_share_pct_2025_current_proxy"] = (
            composition["reachable_youth_child_card_trip_count_2025_current_proxy"]
            / composition["reachable_card_trip_count_2025_current_proxy"]
            * 100
        )
        by_dong = by_dong.merge(
            composition.reset_index(), on="admin_dong_code", how="left", validate="one_to_one"
        )

    service_route_count = 0
    if routes_current is not None:
        required_service_columns = {
            "buslinenum",
            "firsttime",
            "endtime",
            "headwaynorm",
        }
        if not required_service_columns <= set(routes_current.columns):
            raise ValueError("Current route service data is missing time or headway fields")
        service = routes_current[list(required_service_columns)].copy()
        service["buslinenum"] = service["buslinenum"].astype(str).str.strip()
        service["headwaynorm"] = pd.to_numeric(service["headwaynorm"], errors="coerce")
        service["first_minutes"] = service["firsttime"].map(_minutes_since_midnight)
        service["end_minutes"] = service["endtime"].map(_minutes_since_midnight)
        service["operating_span_minutes"] = service["end_minutes"] - service["first_minutes"]
        service.loc[service["operating_span_minutes"] < 0, "operating_span_minutes"] += 1_440
        service["adjusted_end_minutes"] = (
            service["first_minutes"] + service["operating_span_minutes"]
        )
        valid_service = (
            service["headwaynorm"].gt(0)
            & service["operating_span_minutes"].gt(0)
        )
        service["estimated_daily_service_opportunities_current"] = np.where(
            valid_service,
            service["operating_span_minutes"] / service["headwaynorm"],
            np.nan,
        )
        early_overlap = (
            np.minimum(service["adjusted_end_minutes"], 240)
            - np.maximum(service["first_minutes"], 0)
        ).clip(lower=0)
        late_overlap = (
            np.minimum(service["adjusted_end_minutes"], 1_680)
            - np.maximum(service["first_minutes"], 1_320)
        ).clip(lower=0)
        service["late_service_span_minutes"] = early_overlap + late_overlap
        service["estimated_late_service_opportunities_current"] = np.where(
            valid_service,
            service["late_service_span_minutes"] / service["headwaynorm"],
            np.nan,
        )
        service_route_count = int(valid_service.sum())
        service_dong = mapped[["buslinenum", "admin_dong_code"]].drop_duplicates().merge(
            service[
                [
                    "buslinenum",
                    "estimated_daily_service_opportunities_current",
                    "estimated_late_service_opportunities_current",
                ]
            ],
            on="buslinenum",
            how="left",
            validate="many_to_one",
        )
        service_by_dong = service_dong.groupby("admin_dong_code", observed=True).agg(
            current_routes_with_service_schedule=(
                "estimated_daily_service_opportunities_current",
                "count",
            ),
            scheduled_bus_service_opportunities_current_proxy=(
                "estimated_daily_service_opportunities_current",
                "sum",
            ),
            late_bus_service_opportunities_current_proxy=(
                "estimated_late_service_opportunities_current",
                "sum",
            ),
        )
        service_by_dong["late_bus_service_share_pct_current_proxy"] = (
            service_by_dong["late_bus_service_opportunities_current_proxy"]
            / service_by_dong["scheduled_bus_service_opportunities_current_proxy"].replace(
                0, np.nan
            )
            * 100
        )
        by_dong = by_dong.merge(
            service_by_dong.reset_index(),
            on="admin_dong_code",
            how="left",
            validate="one_to_one",
        )
    report = {
        "dataset_id": "TRN-BUSAN-ROUTE-USAGE-2025-001+TRN-BUSAN-BIMS-CURRENT-001",
        "join_method": "exact_route_number_then_current_stop_point_within_2025_admin_dong",
        "route_usage_records": len(usage),
        "current_route_count": int(route_stops["buslinenum"].nunique()),
        "matched_route_count": len(matched_route_numbers),
        "route_match_rate": round(len(matched_route_numbers) / len(usage), 6),
        "match_rate": round(len(matched_route_numbers) / len(usage), 6),
        "current_route_stop_records": len(route_stops),
        "unmatched_2025_stop_id_records": coordinate_missing,
        "mapped_route_stop_records": int(
            mapped[["buslinenum", "nodeid"]].drop_duplicates().shape[0]
        ),
        "matched_admin_dongs": int(by_dong["admin_dong_code"].nunique()),
        "demand_transform": "sum of log1p(2025 annual card trips) over unique matched routes",
        "current_routes_with_usable_service_schedule": service_route_count,
        "service_transform": (
            "sum of operating-span minutes divided by normal headway over unique current routes"
            if routes_current is not None
            else "not_requested"
        ),
        "late_service_window": "22:00-04:00 scheduled-span overlap divided by normal headway",
        "decision": "supplemental_category_indicator",
        "limitation": (
            "2025 route demand is located with a current BIMS route topology snapshot; it "
            "measures demand-weighted route reach; service opportunities use the current "
            "published normal headway rather than a dated 2025 timetable or observed departures."
        ),
    }
    return by_dong, report


def historical_stop_demand_validation(
    boundaries: gpd.GeoDataFrame,
    bus_stops: gpd.GeoDataFrame,
    route_stops: pd.DataFrame,
    boarding: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Locate 2023 route-stop demand by strict route and stop-name agreement."""
    required = {"노선번호", "정류장명", "승차합계", "하차합계"}
    if not required <= set(boarding.columns):
        raise ValueError("2023 boarding data is missing route, stop, boarding, or alighting fields")
    if "bstopnm" not in route_stops.columns:
        raise ValueError("Current BIMS route stops require bstopnm for historical validation")
    mapped, _ = _map_current_route_stops(boundaries, bus_stops, route_stops)
    locations = mapped[["buslinenum", "bstopnm", "admin_dong_code"]].drop_duplicates()
    location_counts = locations.groupby(["buslinenum", "bstopnm"])[
        "admin_dong_code"
    ].nunique()
    unique_keys = location_counts[location_counts == 1].index
    locations = locations.set_index(["buslinenum", "bstopnm"]).loc[unique_keys].reset_index()

    demand = boarding.copy()
    demand["노선번호"] = demand["노선번호"].astype(str).str.strip()
    demand["정류장명"] = demand["정류장명"].astype(str).str.strip()
    demand = demand.merge(
        locations,
        left_on=["노선번호", "정류장명"],
        right_on=["buslinenum", "bstopnm"],
        how="left",
        validate="many_to_one",
    )
    numeric_columns = ["승차합계", "하차합계"] + [
        column
        for column in demand.columns
        if ("승차건수" in column or "하차건수" in column or column.endswith("승차합계"))
        and column not in {"승차합계", "하차합계"}
    ]
    demand[numeric_columns] = demand[numeric_columns].apply(pd.to_numeric, errors="coerce")
    demand = demand.copy()
    peak_prefixes = ("오전7시", "오전8시", "오후5시", "오후6시")
    late_prefixes = ("오후10시", "오후11시", "오전12시", "오전1시", "오전2시", "오전3시")
    time_columns = [column for column in numeric_columns if column not in {"승차합계", "하차합계"}]
    demand["peak_boarding_alighting"] = demand[
        [column for column in time_columns if column.startswith(peak_prefixes)]
    ].sum(axis=1)
    demand["late_boarding_alighting"] = demand[
        [column for column in time_columns if column.startswith(late_prefixes)]
    ].sum(axis=1)
    matched = demand[demand["admin_dong_code"].notna()].copy()
    matched["boarding_alighting"] = matched["승차합계"] + matched["하차합계"]
    by_dong = matched.groupby("admin_dong_code", observed=True).agg(
        bus_boarding_2023_validation=("승차합계", "sum"),
        bus_alighting_2023_validation=("하차합계", "sum"),
        bus_boarding_alighting_2023_validation=("boarding_alighting", "sum"),
        peak_bus_demand_2023_validation=("peak_boarding_alighting", "sum"),
        late_bus_demand_2023_validation=("late_boarding_alighting", "sum"),
    )
    denominator = by_dong["bus_boarding_alighting_2023_validation"].replace(0, np.nan)
    by_dong["peak_bus_demand_share_pct_2023_validation"] = (
        by_dong["peak_bus_demand_2023_validation"] / denominator * 100
    )
    by_dong["late_bus_demand_share_pct_2023_validation"] = (
        by_dong["late_bus_demand_2023_validation"] / denominator * 100
    )
    report = {
        "dataset_id": "TRN-BUSAN-BOARDING-2023-001+TRN-BUSAN-BIMS-CURRENT-001",
        "join_method": "exact_route_number_and_stop_name_to_unique_current_dong",
        "input_records": len(boarding),
        "matched_records": len(matched),
        "unmatched_records": len(boarding) - len(matched),
        "match_rate": round(len(matched) / len(boarding), 6),
        "matched_admin_dongs": int(by_dong.index.nunique()),
        "decision": "validation_only",
        "limitation": (
            "2023 route-stop demand is matched to current BIMS names and 2025 stop locations; "
            "it validates temporal demand patterns but is excluded from 2025 scoring."
        ),
    }
    return by_dong.reset_index(), report


def attach_source_metadata(report: dict[str, Any], path: Path) -> dict[str, Any]:
    """Attach a reproducible, secret-free source reference to a dataset report."""
    report["source_path"] = path.as_posix()
    report["source_sha256"] = sha256_file(path)
    return report


def attach_combined_source_metadata(
    report: dict[str, Any], paths: list[Path]
) -> dict[str, Any]:
    """Attach one digest covering every contributing source file."""
    unique_paths = list(dict.fromkeys(paths))
    report["source_path"] = ";".join(path.as_posix() for path in unique_paths)
    report["source_paths"] = [path.as_posix() for path in unique_paths]
    digest = hashlib.sha256()
    for path in sorted(unique_paths, key=lambda item: item.as_posix()):
        digest.update(path.as_posix().encode())
        digest.update(sha256_file(path).encode())
    report["source_sha256"] = digest.hexdigest().upper()
    return report


def load_aed_points(path: Path) -> tuple[gpd.GeoDataFrame, int, int]:
    """Parse WKT points from the Busan AED response."""
    document = json.loads(path.read_text(encoding="utf-8"))
    items = document["response"]["body"]["items"]["item"]
    if isinstance(items, dict):
        items = [items]
    frame = pd.DataFrame(items)
    geometries = []
    missing = 0
    invalid = 0
    for value in frame["geom"]:
        if not str(value).strip():
            geometries.append(None)
            missing += 1
            continue
        try:
            geometry = wkt.loads(str(value))
        except Exception:  # noqa: BLE001 - provider WKT is audited and counted
            geometry = None
            invalid += 1
        geometries.append(geometry)
    points = gpd.GeoDataFrame(frame, geometry=geometries, crs="EPSG:4326")
    return points, missing, invalid


def _attach_counts(profile: pd.DataFrame, counts: pd.Series, column: str) -> None:
    mapped = profile["admin_dong_code"].map(counts)
    profile[column] = mapped.fillna(0).astype("int64")
    profile[f"{column}_per_10000_population"] = (
        profile[column] / profile["total_population_2025"] * 10_000
    ).round(6)


def build_standardized_profile(
    paths: SourcePaths | None = None,
    *,
    include_basic_livelihood: bool = True,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build a 206-row candidate profile and a transparent validation report."""
    paths = paths or SourcePaths()
    boundaries = load_boundaries(paths.boundaries)
    reports: list[dict[str, Any]] = []

    population = read_csv_fallback(paths.population, dtype=str)
    reports.append(
        attach_source_metadata(
            validate_code_frame(
                population,
                boundaries,
                dataset_id="DEM-MOIS-POP-2025-001",
                code_column="sgis_admin_dong_code",
                expected_complete=True,
            ),
            paths.population,
        )
    )
    numeric_population = [
        "total_population",
        "households",
        "male_population",
        "female_population",
    ]
    for column in numeric_population:
        population[column] = pd.to_numeric(population[column], errors="raise")
        if (population[column] < 0).any():
            raise ValueError(f"Population column contains negative values: {column}")
    profile = population[
        [
            "sgis_admin_dong_code",
            "sido_name",
            "sigungu_name",
            "admin_dong_name",
            "total_population",
            "households",
            "male_population",
            "female_population",
        ]
    ].rename(
        columns={
            "sgis_admin_dong_code": "admin_dong_code",
            "total_population": "total_population_2025",
            "households": "households_2025",
            "male_population": "male_population_2025",
            "female_population": "female_population_2025",
        }
    )

    employment_document = json.loads(paths.employment.read_text(encoding="utf-8"))
    employment = pd.DataFrame(employment_document["result"])
    reports.append(
        attach_source_metadata(
            validate_code_frame(
                employment,
                boundaries,
                dataset_id="EMP-SGIS-001",
                code_column="adm_cd",
                expected_complete=True,
            ),
            paths.employment,
        )
    )
    employment["corp_cnt"] = pd.to_numeric(employment["corp_cnt"], errors="raise")
    employment["tot_worker"] = pd.to_numeric(employment["tot_worker"], errors="raise")
    profile = profile.merge(
        employment[["adm_cd", "corp_cnt", "tot_worker"]].rename(
            columns={
                "adm_cd": "admin_dong_code",
                "corp_cnt": "establishments_2024",
                "tot_worker": "workplace_workers_2024",
            }
        ),
        on="admin_dong_code",
        how="left",
        validate="one_to_one",
    )

    housing = read_csv_fallback(paths.housing, dtype={"adm_cd": str})
    reports.append(
        attach_source_metadata(
            validate_code_frame(
                housing,
                boundaries,
                dataset_id="HOU-SGIS-OLD-001",
                code_column="adm_cd",
                expected_complete=True,
            ),
            paths.housing,
        )
    )
    housing_columns = [
        "total_house_count_2024",
        "old_house_count_30plus_2024_lower_bound",
        "old_house_share_30plus_2024_lower_bound_pct",
        "suppressed_age_cells",
        "absent_age_cells_imputed_zero",
    ]
    for column in housing_columns:
        housing[column] = pd.to_numeric(housing[column], errors="raise")
    profile = profile.merge(
        housing[["adm_cd", *housing_columns]].rename(columns={"adm_cd": "admin_dong_code"}),
        on="admin_dong_code",
        how="left",
        validate="one_to_one",
    )

    elderly = read_csv_fallback(paths.elderly, dtype=str)
    reports.append(
        attach_source_metadata(
            validate_code_frame(
                elderly,
                boundaries,
                dataset_id="SOC-BUSAN-ELDERLY-ALONE-001",
                code_column="sgis_admin_dong_code",
                expected_complete=True,
            ),
            paths.elderly,
        )
    )
    elderly["elderly_alone_total"] = pd.to_numeric(elderly["elderly_alone_total"], errors="coerce")
    profile = profile.merge(
        elderly[["sgis_admin_dong_code", "elderly_alone_total", "reference_date"]].rename(
            columns={
                "sgis_admin_dong_code": "admin_dong_code",
                "elderly_alone_total": "elderly_alone_latest_count",
                "reference_date": "elderly_alone_reference_date",
            }
        ),
        on="admin_dong_code",
        how="left",
        validate="one_to_one",
    )
    profile["elderly_alone_latest_per_1000_population_2025_validation"] = (
        profile["elderly_alone_latest_count"] / profile["total_population_2025"] * 1_000
    ).round(6)

    bus_stops = gpd.read_file(f"zip://{paths.bus_stops.resolve().as_posix()}")
    bus_counts, report = spatial_counts(
        boundaries,
        bus_stops,
        dataset_id="HOU-BUSSTOP-001",
        input_records=len(bus_stops),
        coordinate_missing=int(bus_stops.geometry.isna().sum()),
    )
    reports.append(attach_source_metadata(report, paths.bus_stops))
    _attach_counts(profile, bus_counts, "bus_stop_count_2025")
    bus_decay, report = boundary_distance_decay_access(
        boundaries,
        bus_stops,
        dataset_id="HOU-BUSSTOP-001-BOUNDARY-CONTEXT",
        cutoff_m=1_000,
        decay_m=500,
    )
    reports.append(attach_source_metadata(report, paths.bus_stops))
    profile["boundary_adjusted_bus_stop_access_1000m_2025_context"] = (
        profile["admin_dong_code"].map(bus_decay).astype(float)
    )

    route_stops = read_csv_fallback(paths.route_stops_current, dtype=str)
    routes_current = read_csv_fallback(paths.routes_current, dtype=str)
    route_usage = read_csv_fallback(paths.route_usage, dtype={"route_no": str})
    route_access, report = route_demand_access(
        boundaries,
        bus_stops,
        route_stops,
        route_usage,
        routes_current,
    )
    report["source_path"] = paths.route_stops_current.as_posix()
    report["source_sha256"] = sha256_file(paths.route_stops_current)
    report["route_usage_source_path"] = paths.route_usage.as_posix()
    report["route_usage_source_sha256"] = sha256_file(paths.route_usage)
    report["route_service_source_path"] = paths.routes_current.as_posix()
    report["route_service_source_sha256"] = sha256_file(paths.routes_current)
    reports.append(report)
    profile = profile.merge(
        route_access,
        on="admin_dong_code",
        how="left",
        validate="one_to_one",
    )
    profile["matched_bus_routes_2025_current_proxy"] = (
        profile["matched_bus_routes_2025_current_proxy"].fillna(0).astype("int64")
    )
    profile["demand_weighted_bus_route_access_2025_current_proxy"] = profile[
        "demand_weighted_bus_route_access_2025_current_proxy"
    ].fillna(0.0)
    route_zero_columns = [
        "current_routes_with_service_schedule",
        "scheduled_bus_service_opportunities_current_proxy",
        "late_bus_service_opportunities_current_proxy",
        "reachable_card_trip_count_2025_current_proxy",
        "reachable_multi_leg_card_trip_count_2025_current_proxy",
        "reachable_youth_child_card_trip_count_2025_current_proxy",
    ]
    for column in route_zero_columns:
        profile[column] = pd.to_numeric(profile[column], errors="coerce").fillna(0.0)

    boarding = read_csv_fallback(
        paths.bus_boarding_2023,
        dtype={"노선번호": str, "정류장코드": str},
    )
    boarding_context, report = historical_stop_demand_validation(
        boundaries,
        bus_stops,
        route_stops,
        boarding,
    )
    reports.append(attach_source_metadata(report, paths.bus_boarding_2023))
    profile = profile.merge(
        boarding_context,
        on="admin_dong_code",
        how="left",
        validate="one_to_one",
    )
    for column in boarding_context.columns.drop("admin_dong_code"):
        profile[column] = pd.to_numeric(profile[column], errors="coerce")

    healthcare_sources = (
        ("HLT-HOSPITAL-001", paths.hospitals, "hospital_count_2025_candidate"),
        ("HLT-CLINIC-001", paths.clinics, "clinic_count_2025_candidate"),
        ("HLT-PHARMACY-001", paths.pharmacies, "pharmacy_count_2025_candidate"),
    )
    healthcare_point_frames: list[gpd.GeoDataFrame] = []
    for dataset_id, path, output_column in healthcare_sources:
        frame = read_csv_fallback(path)
        points, missing = points_from_xy(frame, "CRD_INFO_X", "CRD_INFO_Y", "EPSG:5174")
        counts, report = spatial_counts(
            boundaries,
            points,
            dataset_id=dataset_id,
            input_records=len(frame),
            coordinate_missing=missing,
        )
        reports.append(attach_source_metadata(report, path))
        _attach_counts(profile, counts, output_column)
        healthcare_point_frames.append(points.to_crs(boundaries.crs))

    healthcare_points = gpd.GeoDataFrame(
        pd.concat(healthcare_point_frames, ignore_index=True),
        geometry="geometry",
        crs=boundaries.crs,
    )
    healthcare_decay, report = boundary_distance_decay_access(
        boundaries,
        healthcare_points,
        dataset_id="HLT-HEALTHCARE-BOUNDARY-CONTEXT",
        cutoff_m=2_000,
        decay_m=1_000,
    )
    reports.append(
        attach_combined_source_metadata(
            report, [path for _, path, _ in healthcare_sources]
        )
    )
    profile["boundary_adjusted_healthcare_access_2000m_2025_context"] = (
        profile["admin_dong_code"].map(healthcare_decay).astype(float)
    )

    aed_points, aed_missing, aed_parse_invalid = load_aed_points(paths.aed)
    aed_counts, report = spatial_counts(
        boundaries,
        aed_points,
        dataset_id="HLT-AED-001",
        input_records=len(aed_points),
        coordinate_missing=aed_missing,
    )
    report["wkt_parse_invalid_records"] = aed_parse_invalid
    reports.append(attach_source_metadata(report, paths.aed))
    _attach_counts(profile, aed_counts, "aed_count_current_unverified")

    cctv = read_csv_fallback(paths.cctv)
    cctv_points, missing = points_from_xy(cctv, "경도", "위도", "EPSG:4326")
    cctv_counts, report = spatial_counts(
        boundaries,
        cctv_points,
        dataset_id="SAF-BUSAN-CCTV-001",
        input_records=len(cctv),
        coordinate_missing=missing,
    )
    reports.append(attach_source_metadata(report, paths.cctv))
    _attach_counts(profile, cctv_counts, "crime_prevention_cctv_count_2025")

    heat = read_csv_fallback(paths.heat_shelters)
    heat_points, missing = points_from_xy(heat, "x좌표", "y좌표", "EPSG:4326")
    heat_counts, report = spatial_counts(
        boundaries,
        heat_points,
        dataset_id="ENV-HEAT-SHELTER-001",
        input_records=len(heat),
        coordinate_missing=missing,
    )
    reports.append(attach_source_metadata(report, paths.heat_shelters))
    _attach_counts(profile, heat_counts, "heat_shelter_count_2025")
    heat_decay, report = boundary_distance_decay_access(
        boundaries,
        heat_points,
        dataset_id="ENV-HEAT-SHELTER-BOUNDARY-CONTEXT",
        cutoff_m=1_000,
        decay_m=500,
    )
    reports.append(attach_source_metadata(report, paths.heat_shelters))
    profile["boundary_adjusted_heat_shelter_access_1000m_2025_context"] = (
        profile["admin_dong_code"].map(heat_decay).astype(float)
    )

    processed_sources: list[tuple[str, Path, list[str]]] = []
    if include_basic_livelihood:
        processed_sources.append(
            (
                "INC-BLF-INFERRED-2025-001",
                paths.basic_livelihood,
                [
                    "basic_livelihood_recipients_2025_inferred",
                    "basic_livelihood_households_2025_inferred",
                    "basic_livelihood_recipients_per_1000_population_2025_inferred",
                    "allocation_method",
                    "pattern_source_dataset_id",
                    "pattern_source_period",
                    "district_total_source_dataset_id",
                    "inference_pattern_source_dataset_ids",
                    "inference_feature_source_dataset_ids",
                    "inference_basis",
                    "inference_quality_tier",
                    "is_inferred",
                    "value_status",
                ],
            )
        )
    processed_sources.extend(
        [
            (
                "DEM-BUSAN-LIVING-001",
                paths.living_population,
                [
                    "observed_months_2025",
                    "avg_daily_residential_living_population_2025",
                    "avg_daily_workplace_living_population_2025",
                    "avg_daily_visitor_living_population_2025",
                    "avg_daily_total_living_population_2025",
                    "avg_daily_senior_living_population_2025",
                    "avg_daily_under_20_living_population_2025",
                    "avg_daily_under_30_living_population_2025",
                    "senior_living_population_share_pct_2025",
                    "under_20_living_population_share_pct_2025",
                    "under_30_living_population_share_pct_2025",
                    "daytime_to_residential_living_population_ratio_2025",
                ],
            ),
            (
                "EDU-SCHOOL-001",
                paths.schools,
                [
                    "elementary",
                    "middle",
                    "high",
                    "school_count_2025",
                    "nearest_core_school_distance_m_2025",
                    "core_schools_within_2000m_2025",
                    "core_school_teachers_within_2000m_2025",
                    "core_school_students_within_2000m_2025",
                ],
            ),
            (
                "ENV-AIR-HEIS-DAILY-2025-001",
                paths.air_exposure,
                [
                    "air_idw_station_count",
                    "nearest_air_station_distance_m",
                    "annual_pm25_ug_m3_idw_2025",
                    "annual_pm10_ug_m3_idw_2025",
                    "annual_so2_ppm_idw_2025",
                    "annual_o3_ppm_idw_2025",
                    "annual_no2_ppm_idw_2025",
                    "annual_co_ppm_idw_2025",
                ],
            ),
        ]
    )
    for dataset_id, path, columns in processed_sources:
        candidate = read_csv_fallback(path, dtype={"admin_dong_code": str})
        reports.append(
            attach_source_metadata(
                validate_code_frame(
                    candidate,
                    boundaries,
                    dataset_id=dataset_id,
                    code_column="admin_dong_code",
                    expected_complete=True,
                ),
                path,
            )
        )
        profile = profile.merge(
            candidate[["admin_dong_code", *columns]],
            on="admin_dong_code",
            how="left",
            validate="one_to_one",
        )

    total_living = profile["avg_daily_total_living_population_2025"].replace(0, np.nan)
    senior_living = profile["avg_daily_senior_living_population_2025"].replace(0, np.nan)
    under_20_living = profile["avg_daily_under_20_living_population_2025"].replace(0, np.nan)
    profile["bus_service_opportunities_per_1000_total_living_population_context"] = (
        profile["scheduled_bus_service_opportunities_current_proxy"] / total_living * 1_000
    )
    profile["bus_service_opportunities_per_1000_senior_living_population_context"] = (
        profile["scheduled_bus_service_opportunities_current_proxy"] / senior_living * 1_000
    )
    profile["core_school_teachers_per_1000_under_20_living_population_2025_context"] = (
        profile["core_school_teachers_within_2000m_2025"] / under_20_living * 1_000
    )
    healthcare_count = profile[
        [
            "hospital_count_2025_candidate",
            "clinic_count_2025_candidate",
            "pharmacy_count_2025_candidate",
        ]
    ].sum(axis=1)
    profile["healthcare_facilities_per_1000_senior_living_population_2025_context"] = (
        healthcare_count / senior_living * 1_000
    )
    profile["heat_shelters_per_1000_senior_living_population_2025_context"] = (
        profile["heat_shelter_count_2025"] / senior_living * 1_000
    )
    reports.append(
        attach_source_metadata(
            {
                "dataset_id": "DEM-BUSAN-LIVING-001+SERVICE-SUPPLY-CONTEXT",
                "join_method": "canonical_dong_supply_divided_by_annual_mean_living_population",
                "input_records": len(profile),
                "matched_records": len(profile),
                "matched_admin_dongs": len(profile),
                "match_rate": 1.0,
                "decision": "validation_only",
                "limitation": (
                    "Telecom living population is a service-demand context denominator, not a "
                    "resident deprivation population or observed facility utilization measure."
                ),
            },
            paths.living_population,
        )
    )

    valid_late = profile[
        [
            "late_bus_demand_share_pct_2023_validation",
            "late_bus_service_share_pct_current_proxy",
        ]
    ].notna().all(axis=1)
    late_demand_rank = profile.loc[
        valid_late, "late_bus_demand_share_pct_2023_validation"
    ].rank(method="average", pct=True)
    low_service_rank = (-profile.loc[
        valid_late, "late_bus_service_share_pct_current_proxy"
    ]).rank(method="average", pct=True)
    profile["late_bus_demand_service_mismatch_percentile_2023_current_validation"] = np.nan
    profile.loc[
        valid_late,
        "late_bus_demand_service_mismatch_percentile_2023_current_validation",
    ] = (late_demand_rank + low_service_rank) / 2 * 100
    reports.append(
        attach_combined_source_metadata(
            {
                "dataset_id": "TRN-BUSAN-BOARDING-2023-001+TRN-BUSAN-BIMS-CURRENT-001-MISMATCH",
                "join_method": "mean_of_high_late_demand_and_low_late_service_percentile_ranks",
                "input_records": len(profile),
                "matched_records": int(valid_late.sum()),
                "matched_admin_dongs": int(valid_late.sum()),
                "match_rate": round(float(valid_late.mean()), 6),
                "decision": "validation_only",
                "limitation": (
                    "The mismatch combines 2023 observed stop demand with a current scheduled "
                    "service proxy and cannot establish a 2025 service deficit."
                ),
            },
            [paths.bus_boarding_2023, paths.routes_current],
        )
    )

    profile = profile.sort_values("admin_dong_code").reset_index(drop=True)
    count_columns = [
        column
        for column in profile.columns
        if column.endswith("_count_2025") or column.endswith("_count_2025_candidate")
    ]
    profile_checks = {
        "unique_admin_dong_codes": not profile["admin_dong_code"].duplicated().any(),
        "total_population_2025": int(profile["total_population_2025"].sum()),
        "zero_population_admin_dongs": int((profile["total_population_2025"] == 0).sum()),
        "sex_total_mismatch_admin_dongs": int(
            (
                profile["male_population_2025"] + profile["female_population_2025"]
                != profile["total_population_2025"]
            ).sum()
        ),
        "count_column_totals": {column: int(profile[column].sum()) for column in count_columns},
    }
    if not profile_checks["unique_admin_dong_codes"]:
        raise ValueError("Standardized profile contains duplicate administrative-dong codes")
    if profile_checks["zero_population_admin_dongs"]:
        raise ValueError("Population denominator contains zero-population administrative dongs")
    if profile_checks["sex_total_mismatch_admin_dongs"]:
        raise ValueError("Population sex totals do not reconcile with total population")
    missing_by_column = {column: int(profile[column].isna().sum()) for column in profile.columns}
    report_document: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "reference_year": REFERENCE_YEAR,
        "reference_crs": REFERENCE_CRS,
        "canonical_admin_dong_count": len(boundaries),
        "canonical_boundary_path": paths.boundaries.as_posix(),
        "canonical_boundary_sha256": sha256_file(paths.boundaries),
        "profile_record_count": len(profile),
        "profile_checks": profile_checks,
        "missing_by_column": missing_by_column,
        "datasets": reports,
        "zero_is_observed_count_only": True,
        "missing_value_policy": (
            "Missing source values remain null. Zero is filled only for a successfully spatially "
            "joined point inventory when no points occur within a canonical dong."
        ),
        "analysis_roles": {
            "primary_denominator": ["DEM-MOIS-POP-2025-001"],
            "provisional_scoring_proxy": [
                "EMP-SGIS-001",
                "HOU-SGIS-OLD-001",
                *(["INC-BLF-INFERRED-2025-001"] if include_basic_livelihood else []),
                "HLT-HOSPITAL-001",
                "HLT-CLINIC-001",
                "HLT-PHARMACY-001",
                "HOU-BUSSTOP-001",
                "SAF-BUSAN-CCTV-001",
                "ENV-HEAT-SHELTER-001",
                "EDU-SCHOOL-001",
                "EDU-SCHOOLINFO-2025-001",
                "ENV-AIR-HEIS-DAILY-2025-001",
            ],
            "supplemental_category_indicator": [
                "TRN-BUSAN-ROUTE-USAGE-2025-001",
                "TRN-BUSAN-BIMS-CURRENT-001",
            ],
            "validation_only": [
                "SOC-BUSAN-ELDERLY-ALONE-001",
                "HLT-AED-001",
                "DEM-BUSAN-LIVING-001",
            ],
        },
    }
    return profile, report_document


def write_outputs(
    profile: pd.DataFrame,
    report: dict[str, Any],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> dict[str, Any]:
    """Write the reproducible profile and committed secret-free validation report."""
    output_dir.mkdir(parents=True, exist_ok=True)
    profile_path = output_dir / "busan_admin_dong_candidate_profile_2025.csv"
    profile.to_csv(profile_path, index=False, encoding="utf-8-sig")
    report = dict(report)
    report["profile_path"] = profile_path.as_posix()
    report["profile_sha256"] = sha256_file(profile_path)
    write_json(report_path, report)
    write_json(output_dir / "standardization_report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args()
    profile, report = build_standardized_profile()
    report = write_outputs(profile, report, args.output_dir, args.report)
    minimum_rate = min(dataset["match_rate"] for dataset in report["datasets"])
    print(
        f"standardized {len(profile)} administrative dongs; "
        f"minimum source match rate={minimum_rate:.2%}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
