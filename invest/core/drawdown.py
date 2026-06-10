from __future__ import annotations

import pandas as pd

DRAWDOWN_6M_LOOKBACK_DAYS = 126


def rolling_drawdown_from_high(
    close: pd.Series, lookback_days: int = DRAWDOWN_6M_LOOKBACK_DAYS
) -> pd.Series:
    """当前价相对滚动高点的回撤（≤0，如 -0.15 表示距高点跌 15%）。"""
    lb = int(lookback_days)
    min_periods = min(lb, 20)
    roll_max = close.rolling(lb, min_periods=min_periods).max()
    return close / roll_max - 1.0
