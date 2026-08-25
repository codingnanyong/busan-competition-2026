"""Tests for 2025 candidate-source processing."""

import json

import pandas as pd

from busan_imd.processing.candidate_processing import CandidatePaths, process_transport


def test_process_transport_reconciles_route_totals_and_keeps_district_unit(tmp_path) -> None:
    route_path = tmp_path / "route.csv"
    pd.DataFrame(
        [
            {
                "노선": "1",
                "건수(1통행)_일반": 2,
                "건수(1통행)_청소년": 1,
                "교통카드건수합계": 3,
            }
        ]
    ).to_csv(route_path, index=False, encoding="cp949")
    village_path = tmp_path / "village.json"
    village_path.write_text(
        json.dumps(
            {
                "response": {
                    "body": {
                        "items": {
                            "item": [
                                {
                                    "route_no": "중구1",
                                    "gugun": "중구",
                                    "num_of_vehicles": "2",
                                    "num_of_spare_vehicles": "0",
                                    "bus_interval": "10",
                                    "reference_date": "2025-12-01",
                                }
                            ]
                        }
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    paths = CandidatePaths(route_usage=route_path, village_bus=village_path)

    route, district, report = process_transport(paths)

    assert route.loc[0, "recalculated_card_trip_count_2025"] == 3
    assert district.loc[0, "village_bus_route_count"] == 1
    assert report["route_usage_reconciliation_failures"] == 0
    assert report["decision"] == "validation-only"
