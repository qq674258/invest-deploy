from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd

# 与支付宝/天天基金常见区间对齐
PERIOD_DEFS: list[tuple[str, str, int | None]] = [
    ("1w", "近1周", 7),
    ("1m", "近1月", 30),
    ("3m", "近3月", 92),
    ("6m", "近6月", 183),
    ("1y", "近1年", 365),
    ("3y", "近3年", 365 * 3),
    ("5y", "近5年", 365 * 5),
    ("ytd", "今年以来", None),
    ("si", "成立以来", None),
]


def _nav_series(nav_df: pd.DataFrame) -> pd.Series:
    s = nav_df.set_index("nav_date")["nav"].astype(float).sort_index()
    # SQLite 读出为 datetime.date，须统一为 DatetimeIndex，否则与 Timestamp 比较会 500
    s.index = pd.to_datetime(s.index)
    return s[~s.index.duplicated(keep="last")]


def period_return_pct(series: pd.Series, start: date) -> float | None:
    if series.empty:
        return None
    end = series.index[-1]
    if isinstance(end, pd.Timestamp):
        end = end.date()
    start_ts = pd.Timestamp(start)
    sub = series[series.index >= start_ts]
    if sub.empty:
        sub = series
    first = float(sub.iloc[0])
    last = float(sub.iloc[-1])
    if first <= 0:
        return None
    return round((last / first - 1.0) * 100.0, 4)


def compute_period_returns(nav_df: pd.DataFrame) -> list[dict[str, Any]]:
    if nav_df.empty:
        return []
    series = _nav_series(nav_df)
    if series.empty:
        return []
    last_date = series.index[-1]
    if isinstance(last_date, pd.Timestamp):
        last_d = last_date.date()
    else:
        last_d = last_date
    ytd_start = date(last_d.year, 1, 1)
    out: list[dict[str, Any]] = []
    for pid, label, days in PERIOD_DEFS:
        if pid == "ytd":
            start = ytd_start
        elif pid == "si":
            start = series.index[0]
            if isinstance(start, pd.Timestamp):
                start = start.date()
        elif days:
            start = last_d - timedelta(days=days)
        else:
            start = last_d
        ret = period_return_pct(series, start)
        out.append(
            {
                "period_id": pid,
                "label": label,
                "return_pct": ret,
            }
        )
    return out


def build_performance_chart(
    nav_df: pd.DataFrame,
    *,
    limit: int = 252,
) -> dict[str, Any]:
    """净值归一化业绩走势（基准=100）。"""
    if nav_df.empty:
        return {"dates": [], "nav": [], "normalized": []}
    series = _nav_series(nav_df).tail(limit)
    base = float(series.iloc[0])
    dates = [pd.Timestamp(d).strftime("%Y-%m-%d") for d in series.index]
    navs = [round(float(v), 4) for v in series.values]
    norm = [round(float(v) / base * 100.0, 4) for v in series.values]
    return {
        "dates": dates,
        "nav": navs,
        "normalized": norm,
        "base_date": dates[0] if dates else None,
    }
