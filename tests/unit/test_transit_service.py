"""Unit tests for current Busan route-service collection."""

from pathlib import Path

from busan_imd.collectors.transit_service import collect, parse_route_stops, parse_routes

PAYLOAD = b"""<?xml version="1.0" encoding="UTF-8"?>
<response><header><resultCode>00</resultCode><resultMsg>NORMAL</resultMsg></header>
<body><items><item><lineid>1</lineid><buslinenum>10</buslinenum>
<bustype>normal</bustype><startpoint>A</startpoint><endpoint>B</endpoint>
<firsttime>05:00</firsttime><endtime>23:00</endtime><headway>12</headway>
<headwaynorm>15</headwaynorm><headwaypeak>10</headwaypeak>
<headwayholi>20</headwayholi></item></items></body></response>"""

STOP_PAYLOAD = b"""<?xml version="1.0" encoding="UTF-8"?>
<response><header><resultCode>00</resultCode><resultMsg>NORMAL</resultMsg></header>
<body><items><item><bstopidx>1</bstopidx><bstopnm>Stop A</bstopnm>
<nodeid>5001</nodeid><arsno>10001</arsno>
<direction>Downtown</direction><rpoint>0</rpoint></item>
</items></body></response>"""


def test_parse_and_collect_current_routes_without_scoring_claim(tmp_path: Path) -> None:
    frame = parse_routes(PAYLOAD)
    assert frame.loc[0, "headwaynorm"] == 15
    stops = parse_route_stops(STOP_PAYLOAD, "1", "10")
    assert stops.loc[0, "nodeid"] == "5001"
    assert stops.loc[0, "buslinenum"] == "10"

    raw_path = tmp_path / "routes.xml"
    csv_path = tmp_path / "routes.csv"
    route_stops_csv_path = tmp_path / "route-stops.csv"
    manifest_path = tmp_path / "manifest.json"

    def fetcher(url: str) -> bytes:
        return STOP_PAYLOAD if "busInfoByRouteId" in url else PAYLOAD

    manifest = collect(
        "encoded%2Fsecret%3D",
        raw_path,
        csv_path,
        manifest_path,
        fetcher,
        route_stops_csv_path,
    )

    assert manifest["route_count"] == 1
    assert manifest["route_stop_record_count"] == 1
    assert manifest["routes_with_stop_records"] == 1
    assert manifest["analysis_role"] == "supplemental_category_indicator"
    assert manifest["cutoff_status"] == "outside_2025_primary_period"
    assert "secret" not in manifest_path.read_text(encoding="utf-8")


def test_collect_creates_nested_route_stops_csv_directory(tmp_path: Path) -> None:
    raw_path = tmp_path / "routes.xml"
    csv_path = tmp_path / "csv" / "nested" / "routes.csv"
    route_stops_csv_path = tmp_path / "stops" / "nested" / "route-stops.csv"
    manifest_path = tmp_path / "manifests" / "manifest.json"

    def fetcher(url: str) -> bytes:
        return STOP_PAYLOAD if "busInfoByRouteId" in url else PAYLOAD

    collect(
        "encoded%2Fsecret%3D",
        raw_path,
        csv_path,
        manifest_path,
        fetcher,
        route_stops_csv_path,
    )

    assert csv_path.exists()
    assert route_stops_csv_path.exists()
    assert manifest_path.exists()
