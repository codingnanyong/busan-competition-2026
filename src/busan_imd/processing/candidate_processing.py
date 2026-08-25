"""Process collected 2025 sources and judge their fitness for dong-level IMD use."""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd

from busan_imd.core.artifacts import sha256_file, write_json
from busan_imd.core.config import read_env_file, require_values
from busan_imd.core.http import encoded_secret_url, fetch_json
from busan_imd.processing.standardization import load_boundaries, read_csv_fallback
from busan_imd.sources.sgis import authenticate, request_json

OUTPUT_DIR = Path("data/processed/candidates/2025")
REPORT_PATH = Path("docs/data/manifests/CANDIDATE_PROCESSING_REPORT_2025.json")
SCHOOL_COORDINATES = Path(
    "data/raw/reference/EDU-SCHOOL-NEIS-001/busan_school_coordinates_2025.csv"
)
AIR_STATIONS = Path("data/raw/heis/stations/busan_air_station_coordinates.csv")
SCHOOLINFO_2025_NAME_ALIASES = {
    "계성여자고등학교": "계성여자상업고등학교",
}


@dataclass(frozen=True)
class CandidatePaths:
    boundaries: Path = Path(
        "data/raw/sgis/admin_boundaries/2025/busan_admin_dong_boundaries_2025_valid.geojson"
    )
    population: Path = Path(
        "data/raw/mois/resident_population/2025/busan_resident_population_admin_dong_2025_12.csv"
    )
    living_population: Path = Path(
        "data/raw/supplemental/living_population/busan_living_population_2023_2025.xlsx.download"
    )
    schools: Path = Path("data/raw/reference/EDU-SCHOOL-NEIS-001/busan_school_info.json")
    school_coordinates: Path = SCHOOL_COORDINATES
    school_disclosures: Path = Path(
        "data/raw/reference/EDU-SCHOOLINFO-2025-001/busan_school_disclosures_2025.json"
    )
    air_daily: Path = Path("data/raw/heis/air_daily/2025/busan_heis_air_daily_2025_01_12.csv")
    air_stations: Path = AIR_STATIONS
    route_usage: Path = Path("data/raw/supplemental/bus_route_usage/busan_bus_route_usage_2025.csv")
    village_bus: Path = Path("data/raw/supplemental/village_bus/busan_village_bus_status.json")


def collect_school_coordinates(
    consumer_key: str, consumer_secret: str, school_path: Path, output_path: Path
) -> dict[str, Any]:
    """Geocode cutoff-eligible NEIS schools with the official SGIS address API."""
    rows = json.loads(school_path.read_text(encoding="utf-8"))["schoolInfo"]
    eligible = [
        row for row in rows if not row.get("FOND_YMD") or str(row["FOND_YMD"]) <= "20251231"
    ]
    token = authenticate(consumer_key, consumer_secret)

    def geocode(row: dict[str, Any]) -> dict[str, Any]:
        address = str(row.get("ORG_RDNMA") or "").strip()
        result: dict[str, Any] = {
            "school_code": str(row.get("SD_SCHUL_CODE") or "").strip(),
            "school_name": row.get("SCHUL_NM"),
            "school_type": row.get("SCHUL_KND_SC_NM"),
            "road_address": address,
            "foundation_date": row.get("FOND_YMD"),
            "longitude": None,
            "latitude": None,
            "sgis_admin_dong_code": None,
            "sgis_admin_dong_name": None,
            "matching": None,
            "geocode_status": "missing_address",
        }
        if not address:
            return result
        document = request_json(
            "https://sgisapi.mods.go.kr/OpenAPI3/addr/geocodewgs84.json",
            {
                "accessToken": token,
                "address": address,
                "pagenum": "0",
                "resultcount": "1",
            },
        )
        candidates = document.get("result", {}).get("resultdata", [])
        if document.get("errCd") != 0 or not candidates:
            result["geocode_status"] = "not_found"
            return result
        candidate = candidates[0]
        result.update(
            {
                "longitude": candidate.get("x"),
                "latitude": candidate.get("y"),
                "sgis_admin_dong_code": candidate.get("adm_cd"),
                "sgis_admin_dong_name": candidate.get("adm_nm"),
                "matching": document.get("result", {}).get("matching"),
                "geocode_status": "matched",
            }
        )
        return result

    geocoded: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(geocode, row) for row in eligible]
        for future in as_completed(futures):
            geocoded.append(future.result())
    frame = pd.DataFrame(geocoded).sort_values(["school_type", "school_name"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False, encoding="utf-8-sig")
    return {
        "requested_records": len(eligible),
        "matched_records": int((frame["geocode_status"] == "matched").sum()),
        "not_found_records": int((frame["geocode_status"] != "matched").sum()),
        "output_path": output_path.as_posix(),
        "output_sha256": sha256_file(output_path),
    }


def collect_air_station_coordinates(service_key: str, output_path: Path) -> dict[str, Any]:
    """Collect official AirKorea coordinates for Busan monitoring stations."""
    endpoint = "https://apis.data.go.kr/B552584/MsrstnInfoInqireSvc/getMsrstnList"
    url = encoded_secret_url(
        endpoint,
        "serviceKey",
        service_key,
        {"returnType": "json", "numOfRows": "100", "pageNo": "1", "addr": "부산"},
    )
    document = fetch_json(url)
    header = document["response"]["header"]
    if str(header.get("resultCode")) != "00":
        raise ValueError(f"AirKorea station API error: {header}")
    rows = document["response"]["body"]["items"]
    frame = pd.DataFrame(rows).rename(
        columns={
            "stationName": "station_name",
            "addr": "address",
            "dmX": "latitude",
            "dmY": "longitude",
            "mangName": "network_type",
            "year": "operation_start_year",
            "item": "pollutants",
        }
    )
    keep = [
        "station_name",
        "address",
        "latitude",
        "longitude",
        "network_type",
        "operation_start_year",
        "pollutants",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame[keep].to_csv(output_path, index=False, encoding="utf-8-sig")
    return {
        "record_count": len(frame),
        "output_path": output_path.as_posix(),
        "output_sha256": sha256_file(output_path),
    }


def process_living_population(paths: CandidatePaths) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Aggregate 2025 monthly age rows to annual average daily dong populations."""
    raw = pd.read_excel(paths.living_population, engine="openpyxl")
    raw["기준년월"] = raw["기준년월"].astype(str)
    raw["행정동코드"] = raw["행정동코드"].astype(str)
    raw = raw[raw["기준년월"].str.startswith("2025")].copy()
    numeric = ["평균주거인구수", "평균직장인구수", "평균방문인구수"]
    raw[numeric] = raw[numeric].apply(pd.to_numeric, errors="coerce")
    monthly = raw.groupby(["기준년월", "행정동코드"], as_index=False)[numeric].sum(min_count=1)
    months = monthly.groupby("행정동코드")["기준년월"].nunique()
    annual = monthly.groupby("행정동코드", as_index=False)[numeric].mean()
    population = read_csv_fallback(paths.population, dtype=str)
    code_map = population[["mois_admin_dong_code", "sgis_admin_dong_code"]].copy()
    annual["행정동코드"] = annual["행정동코드"].astype(str)
    annual = annual.merge(
        code_map,
        left_on="행정동코드",
        right_on="mois_admin_dong_code",
        how="left",
        validate="one_to_one",
    )
    annual["observed_months_2025"] = annual["행정동코드"].map(months)
    annual = annual.rename(
        columns={
            "sgis_admin_dong_code": "admin_dong_code",
            "평균주거인구수": "avg_daily_residential_living_population_2025",
            "평균직장인구수": "avg_daily_workplace_living_population_2025",
            "평균방문인구수": "avg_daily_visitor_living_population_2025",
        }
    )
    columns = [
        "admin_dong_code",
        "observed_months_2025",
        "avg_daily_residential_living_population_2025",
        "avg_daily_workplace_living_population_2025",
        "avg_daily_visitor_living_population_2025",
    ]
    result = annual[columns].sort_values("admin_dong_code").reset_index(drop=True)
    return result, {
        "dataset_id": "DEM-BUSAN-LIVING-001",
        "input_2025_records": len(raw),
        "output_records": len(result),
        "complete_12_month_dongs": int((result["observed_months_2025"] == 12).sum()),
        "unmatched_admin_codes": int(result["admin_dong_code"].isna().sum()),
        "decision": "validation-only",
        "reason": (
            "Complete dong coverage, but telecom living population is a service-demand "
            "context measure rather than deprivation itself."
        ),
    }


def _school_district_from_address(value: object) -> str:
    match = re.search(r"부산광역시\s+(\S+구|기장군)", str(value))
    return "" if match is None else match.group(1)


def load_school_disclosures(path: Path) -> pd.DataFrame:
    """Join the compatible 2025 SchoolInfo enrollment and active-teacher records."""
    document = json.loads(path.read_text(encoding="utf-8"))
    students = pd.DataFrame(document["student_movement"])
    teachers = pd.DataFrame(document["teachers"])
    for frame, value_column in ((students, "STDNT_SUM"), (teachers, "COL_S")):
        if frame["SCHUL_CODE"].duplicated().any():
            raise ValueError("SchoolInfo school codes must be unique within each disclosure")
        frame[value_column] = pd.to_numeric(frame[value_column], errors="raise")
    students = students[students["PBAN_EXCP_YN"].fillna("N") != "Y"].copy()
    teachers = teachers[teachers["PBAN_EXCP_YN"].fillna("N") != "Y"].copy()
    disclosures = students[
        ["SCHUL_CODE", "SCHUL_NM", "_sgg_code", "_school_kind_code", "STDNT_SUM"]
    ].merge(
        teachers[["SCHUL_CODE", "COL_S"]],
        on="SCHUL_CODE",
        how="inner",
        validate="one_to_one",
    )
    disclosures = disclosures.rename(
        columns={
            "SCHUL_NM": "school_name",
            "STDNT_SUM": "student_count_2025",
            "COL_S": "active_teacher_count_2025",
        }
    )
    disclosures["school_name"] = disclosures["school_name"].astype(str).str.strip()
    disclosures["district_name"] = disclosures["_sgg_code"].map(
        {
            "26110": "중구",
            "26140": "서구",
            "26170": "동구",
            "26200": "영도구",
            "26230": "부산진구",
            "26260": "동래구",
            "26290": "남구",
            "26320": "북구",
            "26350": "해운대구",
            "26380": "사하구",
            "26410": "금정구",
            "26440": "강서구",
            "26470": "연제구",
            "26500": "수영구",
            "26530": "사상구",
            "26710": "기장군",
        }
    )
    if disclosures["district_name"].isna().any():
        raise ValueError("SchoolInfo includes an unknown Busan district code")
    if (disclosures[["student_count_2025", "active_teacher_count_2025"]] < 0).any().any():
        raise ValueError("SchoolInfo counts cannot be negative")
    return disclosures


def process_schools(paths: CandidatePaths) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Create complete dong school counts and centroid access distances."""
    frame = read_csv_fallback(paths.school_coordinates, dtype=str)
    matched = frame[frame["geocode_status"] == "matched"].copy()
    boundaries = load_boundaries(paths.boundaries)
    canonical = set(boundaries["admin_dong_code"])
    matched["admin_dong_code"] = matched["sgis_admin_dong_code"].astype(str)
    matched.loc[~matched["admin_dong_code"].isin(canonical), "admin_dong_code"] = None
    usable_types = matched[matched["school_type"].isin(["초등학교", "중학교", "고등학교"])].copy()
    usable_types["school_name"] = usable_types["school_name"].astype(str).str.strip()
    usable_types["disclosure_school_name"] = usable_types["school_name"].replace(
        SCHOOLINFO_2025_NAME_ALIASES
    )
    usable_types["district_name"] = usable_types["road_address"].map(_school_district_from_address)
    disclosures = load_school_disclosures(paths.school_disclosures)
    usable_types = usable_types.merge(
        disclosures[
            [
                "school_name",
                "district_name",
                "student_count_2025",
                "active_teacher_count_2025",
            ]
        ],
        left_on=["disclosure_school_name", "district_name"],
        right_on=["school_name", "district_name"],
        how="left",
        validate="one_to_one",
        suffixes=("", "_schoolinfo"),
    )
    current_register_core_school_count = len(usable_types)
    usable_types = usable_types[usable_types["active_teacher_count_2025"].notna()].copy()
    pivot = (
        usable_types.pivot_table(
            index="admin_dong_code", columns="school_type", values="school_code", aggfunc="count"
        )
        .rename(columns={"초등학교": "elementary", "중학교": "middle", "고등학교": "high"})
        .fillna(0)
    )
    for column in ("elementary", "middle", "high"):
        if column not in pivot:
            pivot[column] = 0
    pivot = pivot[["elementary", "middle", "high"]].astype(int)
    pivot["school_count_2025"] = pivot.sum(axis=1)
    counts = boundaries[["admin_dong_code"]].merge(
        pivot.reset_index(), on="admin_dong_code", how="left", validate="one_to_one"
    )
    count_columns = ["elementary", "middle", "high", "school_count_2025"]
    counts[count_columns] = counts[count_columns].fillna(0).astype(int)
    point_source = usable_types.copy()
    point_source["longitude"] = pd.to_numeric(point_source["longitude"], errors="coerce")
    point_source["latitude"] = pd.to_numeric(point_source["latitude"], errors="coerce")
    point_source = point_source.dropna(subset=["longitude", "latitude"])
    points = gpd.GeoDataFrame(
        point_source,
        geometry=gpd.points_from_xy(point_source["longitude"], point_source["latitude"]),
        crs="EPSG:4326",
    ).to_crs("EPSG:5179")
    centroids = boundaries.copy()
    centroids["geometry"] = centroids.geometry.centroid
    access_rows: list[dict[str, Any]] = []
    for dong in centroids.itertuples():
        distances = points.geometry.distance(dong.geometry)
        access_rows.append(
            {
                "admin_dong_code": dong.admin_dong_code,
                "nearest_core_school_distance_m_2025": round(float(distances.min()), 3),
                "core_schools_within_2000m_2025": int((distances <= 2_000).sum()),
                "core_school_teachers_within_2000m_2025": int(
                    points.loc[distances <= 2_000, "active_teacher_count_2025"].sum()
                ),
            }
        )
    result = counts.merge(
        pd.DataFrame(access_rows), on="admin_dong_code", how="left", validate="one_to_one"
    ).sort_values("admin_dong_code")
    return result, {
        "dataset_ids": ["EDU-SCHOOL-001", "EDU-SCHOOLINFO-2025-001"],
        "school_register_source": paths.schools.as_posix(),
        "school_disclosure_source": paths.school_disclosures.as_posix(),
        "school_disclosure_sha256": sha256_file(paths.school_disclosures),
        "input_records": len(frame),
        "geocoded_records": len(matched),
        "current_register_core_school_records": current_register_core_school_count,
        "core_school_records": len(usable_types),
        "schoolinfo_disclosure_records": len(disclosures),
        "schoolinfo_matched_core_school_records": int(
            usable_types["active_teacher_count_2025"].notna().sum()
        ),
        "schoolinfo_unmatched_core_school_records": (
            current_register_core_school_count - len(usable_types)
        ),
        "active_teacher_count_2025": int(usable_types["active_teacher_count_2025"].sum()),
        "facility_present_admin_dongs": int((result["school_count_2025"] > 0).sum()),
        "output_records": len(result),
        "maximum_nearest_core_school_distance_m": round(
            float(result["nearest_core_school_distance_m_2025"].max()), 3
        ),
        "decision": "provisional-scoring-proxy",
        "reason": (
            "Official coordinates and 2025 active-teacher disclosures strengthen facility "
            "access and supply measurement; the 2 km allocation remains a spatial proxy and "
            "does not measure resident educational outcomes."
        ),
    }


def _normal_station_name(value: str) -> str:
    return str(value).replace("(도로변)", "").strip()


def process_air_quality(paths: CandidatePaths) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Create annual station means and four-nearest-station IDW dong exposure estimates."""
    daily = read_csv_fallback(paths.air_daily)
    stations = read_csv_fallback(paths.air_stations)
    daily["match_name"] = daily["station_name"].map(_normal_station_name)
    stations["match_name"] = stations["station_name"].map(_normal_station_name)
    pollutants = ["pm25_ug_m3", "pm10_ug_m3", "so2_ppm", "o3_ppm", "no2_ppm", "co_ppm"]
    daily[pollutants] = daily[pollutants].apply(pd.to_numeric, errors="coerce")
    station_annual = daily.groupby(["station_code", "match_name"], as_index=False)[
        pollutants
    ].mean()
    station_annual["observed_days"] = (
        daily.groupby("station_code")["measurement_status"]
        .apply(lambda values: int((values == "observed").sum()))
        .values
    )
    joined = station_annual.merge(
        stations[["match_name", "latitude", "longitude"]],
        on="match_name",
        how="left",
        validate="many_to_one",
    )
    joined["latitude"] = pd.to_numeric(joined["latitude"], errors="coerce")
    joined["longitude"] = pd.to_numeric(joined["longitude"], errors="coerce")
    located = joined.dropna(subset=["latitude", "longitude"]).copy()
    station_points = gpd.GeoDataFrame(
        located,
        geometry=gpd.points_from_xy(located["longitude"], located["latitude"]),
        crs="EPSG:4326",
    ).to_crs("EPSG:5179")
    boundaries = load_boundaries(paths.boundaries)
    centroids = boundaries.copy()
    centroids["geometry"] = centroids.geometry.centroid
    rows: list[dict[str, Any]] = []
    for dong in centroids.itertuples():
        distances = station_points.geometry.distance(dong.geometry).to_numpy()
        nearest = np.argsort(distances)[:4]
        nearest_distances = np.maximum(distances[nearest], 1.0)
        weights = 1.0 / np.square(nearest_distances)
        record: dict[str, Any] = {
            "admin_dong_code": dong.admin_dong_code,
            "air_idw_station_count": len(nearest),
            "nearest_air_station_distance_m": round(float(nearest_distances.min()), 3),
        }
        for pollutant in pollutants:
            values = station_points.iloc[nearest][pollutant].to_numpy(dtype=float)
            valid = ~np.isnan(values)
            record[f"annual_{pollutant}_idw_2025"] = (
                round(float(np.average(values[valid], weights=weights[valid])), 6)
                if valid.any()
                else None
            )
        rows.append(record)
    result = pd.DataFrame(rows).sort_values("admin_dong_code")
    return result, {
        "dataset_id": "ENV-AIR-HEIS-DAILY-2025-001",
        "daily_records": len(daily),
        "heis_station_count": len(station_annual),
        "coordinate_matched_stations": len(located),
        "output_records": len(result),
        "maximum_nearest_station_distance_m": round(
            float(result["nearest_air_station_distance_m"].max()), 3
        ),
        "interpolation": "inverse-distance-squared weighting of four nearest station annual means",
        "decision": "provisional-scoring-proxy",
        "reason": (
            "Full-year pollutant observations and official station coordinates support "
            "reproducible exposure estimates; interpolation uncertainty must be disclosed."
        ),
    }


def process_transport(paths: CandidatePaths) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Normalize route demand and aggregate village-bus supply at its valid district unit."""
    usage = read_csv_fallback(paths.route_usage)
    usage = usage.rename(columns={"노선": "route_no", "교통카드건수합계": "card_trip_count_2025"})
    detail = [column for column in usage if column.startswith("건수(")]
    usage[detail + ["card_trip_count_2025"]] = usage[detail + ["card_trip_count_2025"]].apply(
        pd.to_numeric, errors="coerce"
    )
    usage["recalculated_card_trip_count_2025"] = usage[detail].sum(axis=1)
    route_output = usage[
        ["route_no", "card_trip_count_2025", "recalculated_card_trip_count_2025"]
    ].sort_values("route_no")
    village_document = json.loads(paths.village_bus.read_text(encoding="utf-8"))
    items = village_document["response"]["body"]["items"]["item"]
    village = pd.DataFrame(items)
    for column in ("num_of_vehicles", "num_of_spare_vehicles", "bus_interval"):
        village[column] = pd.to_numeric(village[column], errors="coerce")
    district_output = village.groupby("gugun", as_index=False).agg(
        village_bus_route_count=("route_no", "nunique"),
        village_bus_vehicles=("num_of_vehicles", "sum"),
        median_village_bus_interval_minutes=("bus_interval", "median"),
        reference_date_min=("reference_date", "min"),
        reference_date_max=("reference_date", "max"),
    )
    reconciliation_failures = int(
        (route_output["card_trip_count_2025"] != route_output["recalculated_card_trip_count_2025"])
        .fillna(True)
        .sum()
    )
    report = {
        "dataset_ids": ["TRN-BUSAN-ROUTE-USAGE-2025-001", "TRN-BUSAN-VILLAGE-BUS-001"],
        "route_usage_records": len(route_output),
        "route_usage_reconciliation_failures": reconciliation_failures,
        "village_bus_records": len(village),
        "district_output_records": len(district_output),
        "decision": "validation-only",
        "reason": (
            "Route demand lacks stop geography and village-bus supply is only attributable "
            "to districts; neither can be allocated to 206 dongs without inventing data."
        ),
    }
    return route_output, district_output, report


def write_frame(frame: pd.DataFrame, path: Path) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    return {"path": path.as_posix(), "records": len(frame), "sha256": sha256_file(path)}


def process_all(paths: CandidatePaths, output_dir: Path, report_path: Path) -> dict[str, Any]:
    """Process all already-collected candidates and emit a fitness report."""
    living, living_report = process_living_population(paths)
    schools, school_report = process_schools(paths)
    air, air_report = process_air_quality(paths)
    route, village, transport_report = process_transport(paths)
    artifacts = {
        "living_population": write_frame(living, output_dir / "living_population_2025.csv"),
        "school_access": write_frame(schools, output_dir / "school_counts_2025.csv"),
        "air_exposure": write_frame(air, output_dir / "air_exposure_idw_2025.csv"),
        "route_usage": write_frame(route, output_dir / "bus_route_usage_2025.csv"),
        "village_bus_district": write_frame(
            village, output_dir / "village_bus_by_district_2025.csv"
        ),
    }
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "reference_year": 2025,
        "canonical_admin_dong_count": 206,
        "assessments": [living_report, school_report, air_report, transport_report],
        "artifacts": artifacts,
    }
    write_json(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    parser.add_argument("--collect-coordinates", action="store_true")
    args = parser.parse_args()
    paths = CandidatePaths()
    if args.collect_coordinates:
        config = read_env_file(args.env_file)
        require_values(
            config,
            ("SGIS_CONSUMER_KEY", "SGIS_CONSUMER_SECRET", "DATA_GO_KR_SERVICE_KEY"),
            args.env_file,
        )
        school_report = collect_school_coordinates(
            config["SGIS_CONSUMER_KEY"],
            config["SGIS_CONSUMER_SECRET"],
            paths.schools,
            paths.school_coordinates,
        )
        air_report = collect_air_station_coordinates(
            config["DATA_GO_KR_SERVICE_KEY"], paths.air_stations
        )
        print(f"coordinate collection: schools={school_report}, air={air_report}")
    report = process_all(paths, args.output_dir, args.report)
    print(f"processed {len(report['artifacts'])} candidate artifacts; report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
