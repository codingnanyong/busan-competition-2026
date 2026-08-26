"""Collect the current Busan bus route service inventory for validation."""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from busan_imd.core.artifacts import sha256_file, write_json
from busan_imd.core.config import read_env_file, require_values
from busan_imd.core.http import encoded_secret_url, fetch_bytes
from busan_imd.core.provenance import ensure_secret_free

ENDPOINT = "https://apis.data.go.kr/6260000/BusanBIMS/busInfo"
ROUTE_STOPS_ENDPOINT = "https://apis.data.go.kr/6260000/BusanBIMS/busInfoByRouteId"
SOURCE_PAGE = "https://www.data.go.kr/data/15092750/openapi.do"
OUTPUT_ROOT = Path("data/raw/supplemental/bus_service_current")
RAW_PATH = OUTPUT_ROOT / "busan_bus_routes_current.xml"
CSV_PATH = OUTPUT_ROOT / "busan_bus_routes_current.csv"
ROUTE_STOPS_CSV_PATH = OUTPUT_ROOT / "busan_bus_route_stops_current.csv"
MANIFEST_PATH = Path("docs/data/manifests/BUS_SERVICE_CURRENT_MANIFEST.json")


def parse_routes(payload: bytes) -> pd.DataFrame:
    """Validate and normalize a Busan BIMS route-service response."""
    root = ET.fromstring(payload)
    if root.findtext("./header/resultCode") != "00":
        raise ValueError(f"Busan BIMS error: {root.findtext('./header/resultMsg')}")
    rows = [
        {child.tag: child.text or "" for child in item}
        for item in root.findall("./body/items/item")
    ]
    frame = pd.DataFrame(rows)
    required = {
        "lineid",
        "buslinenum",
        "bustype",
        "startpoint",
        "endpoint",
        "firsttime",
        "endtime",
        "headwaynorm",
        "headwaypeak",
        "headwayholi",
    }
    if frame.empty or not required <= set(frame.columns):
        raise ValueError("Busan BIMS route response is missing required fields")
    if frame["lineid"].duplicated().any() or frame["lineid"].eq("").any():
        raise ValueError("Busan BIMS route IDs must be complete and unique")
    for column in ("headway", "headwaynorm", "headwaypeak", "headwayholi"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.sort_values(["buslinenum", "lineid"]).reset_index(drop=True)


def parse_route_stops(payload: bytes, line_id: str, route_no: str) -> pd.DataFrame:
    """Normalize the current ordered stop inventory for one BIMS route."""
    root = ET.fromstring(payload)
    if root.findtext("./header/resultCode") != "00":
        raise ValueError(f"Busan BIMS route-stop error: {root.findtext('./header/resultMsg')}")
    rows = [
        {child.tag: child.text or "" for child in item}
        for item in root.findall("./body/items/item")
    ]
    if not rows:
        return pd.DataFrame(
            columns=[
                "lineid",
                "buslinenum",
                "bstopidx",
                "bstopnm",
                "nodeid",
                "arsno",
                "direction",
                "rpoint",
            ]
        )
    frame = pd.DataFrame(rows)
    required = {"bstopidx", "bstopnm", "nodeid"}
    if not required <= set(frame.columns):
        missing = sorted(required - set(frame.columns))
        available = sorted(frame.columns)
        raise ValueError(
            f"Busan BIMS route-stop response is missing {missing}; available={available}"
        )
    frame.insert(0, "lineid", str(line_id))
    frame.insert(1, "buslinenum", str(route_no))
    for column in ("arsno", "direction", "rpoint"):
        if column not in frame:
            frame[column] = ""
    frame["bstopidx"] = pd.to_numeric(frame["bstopidx"], errors="raise").astype(int)
    columns = [
        "lineid",
        "buslinenum",
        "bstopidx",
        "bstopnm",
        "nodeid",
        "arsno",
        "direction",
        "rpoint",
    ]
    return frame[columns].sort_values("bstopidx").reset_index(drop=True)


def collect(
    service_key: str,
    raw_path: Path = RAW_PATH,
    csv_path: Path = CSV_PATH,
    manifest_path: Path = MANIFEST_PATH,
    fetcher: Callable[[str], bytes] = fetch_bytes,
    route_stops_csv_path: Path = ROUTE_STOPS_CSV_PATH,
) -> dict[str, Any]:
    """Collect current service and route-stop metadata for supplemental use."""
    url = encoded_secret_url(
        ENDPOINT,
        "serviceKey",
        service_key,
        {"pageNo": "1", "numOfRows": "1000"},
    )
    payload = fetcher(url)
    frame = parse_routes(payload)
    stop_frames: list[pd.DataFrame] = []
    for route in frame.itertuples(index=False):
        stop_url = encoded_secret_url(
            ROUTE_STOPS_ENDPOINT,
            "serviceKey",
            service_key,
            {"lineid": str(route.lineid)},
        )
        stop_frames.append(
            parse_route_stops(
                fetcher(stop_url),
                line_id=str(route.lineid),
                route_no=str(route.buslinenum),
            )
        )
    route_stops = pd.concat(stop_frames, ignore_index=True)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(payload)
    frame.to_csv(csv_path, index=False, encoding="utf-8-sig", lineterminator="\n")
    route_stops.to_csv(
        route_stops_csv_path,
        index=False,
        encoding="utf-8-sig",
        lineterminator="\n",
    )
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    manifest = {
        "schema_version": 1,
        "dataset_id": "TRN-BUSAN-BIMS-CURRENT-001",
        "provider": "Busan Metropolitan City",
        "source_page": SOURCE_PAGE,
        "endpoint": ENDPOINT,
        "access_method": "Public Data Portal service key",
        "reference_period": generated_at,
        "period_type": "current_inventory_snapshot",
        "retrieved_at": generated_at,
        "analysis_role": "supplemental_category_indicator",
        "cutoff_status": "outside_2025_primary_period",
        "spatial_unit": "bus route",
        "license": "no restriction",
        "route_count": len(frame),
        "route_stop_record_count": len(route_stops),
        "routes_with_stop_records": int(route_stops["lineid"].nunique()),
        "route_stops_with_node_ids": int(route_stops["nodeid"].astype(str).ne("").sum()),
        "routes_with_normal_headway": int(frame["headwaynorm"].notna().sum()),
        "routes_with_first_and_last_time": int(
            (frame["firsttime"].ne("") & frame["endtime"].ne("")).sum()
        ),
        "raw_path": raw_path.as_posix(),
        "raw_sha256": sha256_file(raw_path),
        "csv_path": csv_path.as_posix(),
        "csv_sha256": sha256_file(csv_path),
        "route_stops_endpoint": ROUTE_STOPS_ENDPOINT,
        "route_stops_csv_path": route_stops_csv_path.as_posix(),
        "route_stops_csv_sha256": sha256_file(route_stops_csv_path),
        "notes": (
            "Current route topology, headways, and operating spans support a mixed-date "
            "supplemental accessibility proxy when joined to 2025 route usage. The API does "
            "not expose a record-level 2025 route snapshot, so this must remain separate from "
            "the primary 2025 deprivation score."
        ),
    }
    ensure_secret_free(manifest)
    write_json(manifest_path, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--raw", type=Path, default=RAW_PATH)
    parser.add_argument("--csv", type=Path, default=CSV_PATH)
    parser.add_argument("--route-stops-csv", type=Path, default=ROUTE_STOPS_CSV_PATH)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    args = parser.parse_args()
    config = read_env_file(args.env_file)
    require_values(config, ("DATA_GO_KR_SERVICE_KEY",), args.env_file)
    report = collect(
        config["DATA_GO_KR_SERVICE_KEY"],
        args.raw,
        args.csv,
        args.manifest,
        route_stops_csv_path=args.route_stops_csv,
    )
    print(
        f"collected {report['route_count']} current bus routes and "
        f"{report['route_stop_record_count']} route-stop records; manifest: {args.manifest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
