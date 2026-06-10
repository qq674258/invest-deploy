from __future__ import annotations

import pandas as pd


def annualized_return_pct(ohlcv: pd.DataFrame) -> dict:
    """历史收盘价年化收益率（CAGR），供复利计算器默认参考。"""
    if ohlcv.empty or len(ohlcv) < 2:
        return {"annualized_return_pct": 10.0, "sample_years": 0, "source": "default"}

    df = ohlcv.sort_values("trade_date")
    start = float(df["close"].iloc[0])
    end = float(df["close"].iloc[-1])
    d0 = pd.Timestamp(df["trade_date"].iloc[0])
    d1 = pd.Timestamp(df["trade_date"].iloc[-1])
    years = max((d1 - d0).days / 365.25, 1 / 365.25)
    if start <= 0:
        return {"annualized_return_pct": 10.0, "sample_years": round(years, 2), "source": "default"}

    total = end / start - 1.0
    cagr = (1.0 + total) ** (1.0 / years) - 1.0
    return {
        "annualized_return_pct": round(cagr * 100, 2),
        "sample_years": round(years, 2),
        "source": "ohlcv_cagr",
    }
