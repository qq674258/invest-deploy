from datetime import date, timedelta

import pandas as pd

from invest.core.fund_performance import compute_period_returns


def test_compute_period_returns():
    # 模拟 SQLite 读出的 datetime.date 索引（修复前会 TypeError → API 500）
    rows = [
        {
            "nav_date": date.today() - timedelta(days=i),
            "nav": 1.0 + i * 0.001,
        }
        for i in range(120)
    ][::-1]
    df = pd.DataFrame(rows)
    out = compute_period_returns(df)
    assert len(out) >= 5
    assert out[-1]["period_id"] == "si"
    assert out[-1]["return_pct"] is not None
