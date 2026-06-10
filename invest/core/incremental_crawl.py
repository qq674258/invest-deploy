from __future__ import annotations

from datetime import date

from invest.settings import get_ohlcv_lookback_days

INCREMENTAL_BUFFER_DAYS = 14
INCREMENTAL_MIN_DAYS = 30
INCREMENTAL_MAX_DAYS = 90
FUND_INCREMENTAL_MAX_DAYS = 120

# 管理后台「采集近期」：默认拉取/覆盖最新 N 条
RECENT_CRAWL_BARS = 20
RECENT_CRAWL_LOOKBACK_DAYS = 45


def resolve_ohlcv_lookback_days(
    last_trade_date: date | None,
    full_lookback: int | None,
    *,
    incremental: bool,
) -> int:
    """增量模式：仅拉取最新日期之后的窗口（含缓冲）。"""
    base = full_lookback if full_lookback and full_lookback > 0 else get_ohlcv_lookback_days()
    if not incremental:
        return base
    if last_trade_date is None:
        return base
    gap = (date.today() - last_trade_date).days
    inc = max(gap + INCREMENTAL_BUFFER_DAYS, INCREMENTAL_MIN_DAYS)
    inc = min(inc, INCREMENTAL_MAX_DAYS, base)
    return inc


def resolve_fund_nav_max_days(
    last_nav_date: date | None,
    *,
    incremental: bool,
) -> int | None:
    """增量基金净值：限制回溯自然日；None 表示使用配置的 lookback 键。"""
    if not incremental or last_nav_date is None:
        return None
    gap = (date.today() - last_nav_date).days
    days = max(gap + INCREMENTAL_BUFFER_DAYS, INCREMENTAL_MIN_DAYS)
    return min(days, FUND_INCREMENTAL_MAX_DAYS)
