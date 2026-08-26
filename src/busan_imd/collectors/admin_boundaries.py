"""Download and validate Busan administrative-dong boundaries from SGIS."""

from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from busan_imd.core.artifacts import sha256_file as sha256
from busan_imd.core.config import read_env_file
from busan_imd.sources.sgis import authenticate, request_json

BOUNDARY_ENDPOINT = "https://sgisapi.mods.go.kr/OpenAPI3/boundary/hadmarea.geojson"
SOURCE_PAGE = (
    "https://sgis.mods.go.kr/developer/html/newOpenApi/api/dataApi/addressBoundary.html"
)
TERMS_PAGE = "https://sgis.mods.go.kr/developer/html/newOpenApi/policy/policy.html"
DEFAULT_YEAR = 2025
BUSAN_CODE = "21"
EXPECTED_DONG_COUNT = 206
CRS = "EPSG:5179"

def fetch_boundaries(access_token: str, year: int) -> dict[str, Any]:
    """Fetch all second-level descendants (administrative dongs) of Busan."""
    return request_json(
        BOUNDARY_ENDPOINT,
        {
            "accessToken": access_token,
            "year": str(year),
            "adm_cd": BUSAN_CODE,
            "low_search": "2",
        },
    )


def validate_boundaries(
    document: dict[str, Any], expected_count: int = EXPECTED_DONG_COUNT
) -> list[dict[str, Any]]:
    """Validate the SGIS response and return features in stable code order."""
    errors: list[str] = []
    if document.get("errCd") != 0:
        errors.append(f"SGIS error: {document.get('errMsg', 'unknown error')}")
    if document.get("type") != "FeatureCollection":
        errors.append("response type is not FeatureCollection")

    features = document.get("features")
    if not isinstance(features, list):
        raise ValueError("SGIS response has no feature list")
    if len(features) != expected_count:
        errors.append(f"expected {expected_count} features, found {len(features)}")

    codes: list[str] = []
    for index, feature in enumerate(features):
        properties = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        code = str(properties.get("adm_cd", ""))
        name = str(properties.get("adm_nm", ""))
        if len(code) != 8 or not code.startswith(BUSAN_CODE) or not code.isdigit():
            errors.append(f"feature {index}: invalid administrative-dong code {code!r}")
        if not name.startswith("부산광역시 "):
            errors.append(f"feature {index}: invalid administrative-dong name {name!r}")
        if geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            errors.append(f"feature {index}: unsupported geometry type")
        if not geometry.get("coordinates"):
            errors.append(f"feature {index}: empty geometry")
        codes.append(code)

    if len(codes) != len(set(codes)):
        errors.append("administrative-dong codes are not unique")
    if errors:
        raise ValueError("\n".join(errors))
    return sorted(features, key=lambda item: item["properties"]["adm_cd"])

def code_rows(features: list[dict[str, Any]], year: int) -> list[dict[str, str | int]]:
    """Build the reference code table from boundary properties."""
    rows: list[dict[str, str | int]] = []
    for feature in features:
        properties = feature["properties"]
        full_name = str(properties["adm_nm"])
        name_parts = full_name.split(maxsplit=2)
        rows.append(
            {
                "reference_year": year,
                "sido_code": BUSAN_CODE,
                "sido_name": name_parts[0],
                "sigungu_code": str(properties["adm_cd"])[:5],
                "sigungu_name": name_parts[1],
                "admin_dong_code": str(properties["adm_cd"]),
                "admin_dong_name": name_parts[2],
                "full_name": full_name,
            }
        )
    return rows


def write_artifacts(
    document: dict[str, Any], features: list[dict[str, Any]], year: int, output_dir: Path
) -> dict[str, Any]:
    """Write raw GeoJSON, a code table, and a provenance manifest."""
    output_dir.mkdir(parents=True, exist_ok=True)
    boundary_path = output_dir / f"busan_admin_dong_boundaries_{year}.geojson"
    codes_path = output_dir / f"busan_admin_dong_codes_{year}.csv"
    manifest_path = output_dir / f"busan_admin_dong_manifest_{year}.json"

    boundary_path.write_text(
        json.dumps(document, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    fieldnames = list(code_rows(features, year)[0])
    with codes_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(code_rows(features, year))

    geometry_types = sorted({feature["geometry"]["type"] for feature in features})
    manifest = {
        "dataset": "Busan administrative-dong codes and boundaries",
        "provider": "Statistics Korea SGIS",
        "source_page": SOURCE_PAGE,
        "api_endpoint": BOUNDARY_ENDPOINT,
        "terms_page": TERMS_PAGE,
        "access_method": "SGIS OpenAPI with consumer key and secret",
        "retrieved_at": datetime.now(UTC).isoformat(),
        "reference_year": year,
        "request_parameters": {"adm_cd": BUSAN_CODE, "low_search": 2, "year": year},
        "coordinate_reference_system": CRS,
        "feature_count": len(features),
        "geometry_types": geometry_types,
        "code_length": 8,
        "response_transaction_id": document.get("trId"),
        "files": {
            boundary_path.name: {"sha256": sha256(boundary_path)},
            codes_path.name: {"sha256": sha256(codes_path)},
        },
        "notes": [
            "The access token and credentials are intentionally excluded.",
            "The GeoJSON coordinates are SGIS UTM-K (EPSG:5179), not longitude/latitude.",
            "Review SGIS terms before redistributing the raw boundary file.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def write_reference_snapshot(
    manifest: dict[str, Any], features: list[dict[str, Any]], year: int, output_dir: Path
) -> None:
    """Write the redistributable code table and provenance snapshot for version control."""
    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    codes_path = tables_dir / f"BUSAN_ADMIN_DONG_CODES_{year}.csv"
    manifest_path = output_dir / "manifests" / f"BUSAN_ADMIN_DONG_MANIFEST_{year}.json"
    rows = code_rows(features, year)
    with codes_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    snapshot = dict(manifest)
    snapshot["repository_artifacts"] = {
        codes_path.name: {"sha256": sha256(codes_path)},
        "raw_boundary_committed": False,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--reference-dir", type=Path)
    args = parser.parse_args()

    env_file = read_env_file(args.env_file)
    consumer_key = os.getenv("SGIS_CONSUMER_KEY") or env_file.get("SGIS_CONSUMER_KEY")
    consumer_secret = os.getenv("SGIS_CONSUMER_SECRET") or env_file.get("SGIS_CONSUMER_SECRET")
    if not consumer_key or not consumer_secret:
        raise ValueError(
            "Set SGIS_CONSUMER_KEY and SGIS_CONSUMER_SECRET in the environment or .env"
        )

    token = authenticate(consumer_key, consumer_secret)
    document = fetch_boundaries(token, args.year)
    features = validate_boundaries(document)
    output_dir = args.output_dir or Path(f"data/raw/sgis/admin_boundaries/{args.year}")
    manifest = write_artifacts(document, features, args.year, output_dir)
    if args.reference_dir:
        write_reference_snapshot(manifest, features, args.year, args.reference_dir)
    print(
        f"validated {manifest['feature_count']} Busan administrative dongs for "
        f"{args.year}; artifacts: {output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
