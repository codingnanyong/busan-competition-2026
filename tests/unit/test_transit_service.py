"""Unit tests for current Busan route-service collection."""

from pathlib import Path

from busan_imd.collectors.transit_service import collect, parse_routes

PAYLOAD = b"""<?xml version="1.0" encoding="UTF-8"?>
<response><header><resultCode>00</resultCode><resultMsg>NORMAL</resultMsg></header>
<body><items><item><lineid>1</lineid><buslinenum>10</buslinenum>
<bustype>normal</bustype><startpoint>A</startpoint><endpoint>B</endpoint>
<firsttime>05:00</firsttime><endtime>23:00</endtime><headway>12</headway>
<headwaynorm>15</headwaynorm><headwaypeak>10</headwaypeak>
<headwayholi>20</headwayholi></item></items></body></response>"""


def test_parse_and_collect_current_routes_without_scoring_claim(tmp_path: Path) -> None:
    frame = parse_routes(PAYLOAD)
    assert frame.loc[0, "headwaynorm"] == 15

    raw_path = tmp_path / "routes.xml"
    csv_path = tmp_path / "routes.csv"
    manifest_path = tmp_path / "manifest.json"
    manifest = collect(
        "encoded%2Fsecret%3D",
        raw_path,
        csv_path,
        manifest_path,
        lambda _url: PAYLOAD,
    )

    assert manifest["route_count"] == 1
    assert manifest["analysis_role"] == "supplemental_validation"
    assert manifest["cutoff_status"] == "outside_2025_primary_period"
    assert "secret" not in manifest_path.read_text(encoding="utf-8")
