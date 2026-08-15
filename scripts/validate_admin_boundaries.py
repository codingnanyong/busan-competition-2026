"""Validate a downloaded SGIS administrative-dong GeoJSON with GeoPandas."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd
from shapely.validation import explain_validity


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--expected-count", type=int, default=206)
    parser.add_argument("--crs", default="EPSG:5179")
    parser.add_argument("--repair-output", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    boundaries = gpd.read_file(args.path).set_crs(args.crs, allow_override=True)
    checks = {
        "features": len(boundaries),
        "unique_codes": int(boundaries["adm_cd"].nunique()),
        "null_geometries": int(boundaries.geometry.isna().sum()),
        "empty_geometries": int(boundaries.geometry.is_empty.sum()),
        "invalid_geometries": int((~boundaries.geometry.is_valid).sum()),
        "crs": str(boundaries.crs),
    }
    invalid = boundaries.loc[~boundaries.geometry.is_valid, ["adm_cd", "adm_nm", "geometry"]]
    details = []
    if not invalid.empty:
        details = [
            {
                "adm_cd": row.adm_cd,
                "adm_nm": row.adm_nm,
                "reason": explain_validity(row.geometry),
            }
            for row in invalid.itertuples()
        ]
        print(f"invalid geometry details: {details}")
    expected = {
        "features": args.expected_count,
        "unique_codes": args.expected_count,
        "null_geometries": 0,
        "empty_geometries": 0,
        "invalid_geometries": 0,
        "crs": args.crs,
    }
    repaired_checks = None
    repaired_sha256 = None
    if details and args.repair_output:
        repaired = boundaries.copy()
        invalid_mask = ~repaired.geometry.is_valid
        original_areas = repaired.loc[invalid_mask].geometry.area
        repaired.loc[invalid_mask, "geometry"] = repaired.loc[invalid_mask].geometry.make_valid()
        repaired_checks = {
            "features": len(repaired),
            "unique_codes": int(repaired["adm_cd"].nunique()),
            "null_geometries": int(repaired.geometry.isna().sum()),
            "empty_geometries": int(repaired.geometry.is_empty.sum()),
            "invalid_geometries": int((~repaired.geometry.is_valid).sum()),
            "crs": str(repaired.crs),
        }
        if repaired_checks != expected:
            raise ValueError(f"Repaired boundary validation failed: {repaired_checks}")
        args.repair_output.parent.mkdir(parents=True, exist_ok=True)
        repaired.to_file(args.repair_output, driver="GeoJSON")
        repaired_sha256 = hashlib.sha256(args.repair_output.read_bytes()).hexdigest().upper()
        repaired_areas = repaired.loc[invalid_mask].geometry.area
        for detail, before, after in zip(details, original_areas, repaired_areas, strict=True):
            detail["repair"] = "GeoPandas/Shapely make_valid"
            detail["area_before_m2"] = float(before)
            detail["area_after_m2"] = float(after)
            detail["area_change_ratio"] = float((after - before) / before)

    if args.report:
        report = {
            "validated_at": datetime.now(UTC).isoformat(),
            "source_file": args.path.name,
            "source_sha256": hashlib.sha256(args.path.read_bytes()).hexdigest().upper(),
            "source_checks": checks,
            "invalid_geometry_details": details,
            "repair_output": args.repair_output.name if args.repair_output else None,
            "repair_output_sha256": repaired_sha256,
            "repaired_checks": repaired_checks,
        }
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if checks != expected and repaired_checks != expected:
        raise ValueError(f"Boundary validation failed: {checks}")
    print(f"boundary validation passed: {repaired_checks or checks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
