import pandas as pd

from busan_imd.collectors.consumer_sales import prepare


def test_prepare_recovers_one_unnamed_dong_without_zero_filling() -> None:
    reference = pd.DataFrame(
        {
            "sigungu_name": ["중구", "강서구"],
            "admin_dong_name": ["중앙동", "신호동"],
            "admin_dong_code": ["21010510", "21120562"],
        }
    )
    frame = pd.DataFrame(
        {
            "기준년월": [202501, 202502, 202502],
            "행정동코드": [2611051000, 2611051000, 2644059000],
            "행정동명": ["중구 중앙동", "중구 중앙동", None],
            "업종대분류": ["생활", "생활", "생활"],
            "평균이용금액": [31, 28, 56],
            "평균이용건수": [3.1, 2.8, 5.6],
        }
    )
    summary, category, checks = prepare(frame, reference)
    signal = summary.set_index("admin_dong_code").loc["21120562"]
    assert signal["consumer_sales_observed_months_2025"] == 1
    assert signal["consumer_sales_avg_daily_amount_2025"] == 56
    assert len(category) == 2
    assert checks["recovered_names"][0]["name"] == "강서구 신호동"
