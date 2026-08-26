import pandas as pd
import pytest

from busan_imd.collectors.consumer_sales import prepare, prepare_compositions


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


def test_prepare_compositions_builds_age_and_time_transaction_shares() -> None:
    reference = pd.DataFrame(
        {
            "sigungu_name": ["중구"],
            "admin_dong_name": ["중앙동"],
            "admin_dong_code": ["21010510"],
        }
    )
    age = pd.DataFrame(
        {
            "기준년월": [202501, 202501, 202501],
            "행정동코드": [2611051000] * 3,
            "행정동명": ["중구 중앙동"] * 3,
            "연령대": ["20대미만", "20대", "60대이상"],
            "평균이용건수": [10, 20, 70],
        }
    )
    hourly_counts = [0] * 24
    hourly_counts[0], hourly_counts[9], hourly_counts[17], hourly_counts[22] = 10, 20, 30, 40
    hour = pd.DataFrame(
        {
            "기준년월": [202501] * 24,
            "행정동코드": [2611051000] * 24,
            "행정동명": ["중구 중앙동"] * 24,
            "시간대": [f"{value:02d}시" for value in range(24)],
            "평균이용건수": hourly_counts,
        }
    )

    result, checks = prepare_compositions(age, hour, reference)
    row = result.iloc[0]

    assert row["consumer_sales_under_30_transaction_share_pct_2025"] == pytest.approx(30)
    assert row["consumer_sales_senior_transaction_share_pct_2025"] == pytest.approx(70)
    assert row["consumer_sales_late_night_transaction_share_pct_2025"] == pytest.approx(50)
    assert row["consumer_sales_daytime_transaction_share_pct_2025"] == pytest.approx(50)
    assert bool(row["consumer_sales_hour_band_complete_2025"]) is True
    assert checks["composition_admin_dong_count"] == 1
