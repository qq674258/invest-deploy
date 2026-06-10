from __future__ import annotations

import pandas as pd


def _resolve_buy_date(index: pd.DatetimeIndex, buy_date: str | pd.Timestamp) -> pd.Timestamp:
    if not len(index):
        raise ValueError("no_ohlcv")
    ts = pd.Timestamp(buy_date).normalize()
    if ts in index:
        return ts
    on_or_before = index[index <= ts]
    if len(on_or_before):
        return on_or_before[-1]
    return index[0]


def compute_lump_sum_return(
    ohlcv: pd.DataFrame,
    buy_date: str,
    amount: float,
) -> dict:
    """
    按历史收盘价：在 buy_date（对齐最近交易日）一次性买入 amount，持有至最新收盘。
    """
    if ohlcv.empty:
        raise ValueError("no_ohlcv")
    if amount <= 0:
        raise ValueError("invalid_amount")

    df = ohlcv.sort_values("trade_date").copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    prices = df.set_index("trade_date")["close"].astype(float)
    prices = prices[prices > 0]
    if prices.empty:
        raise ValueError("no_ohlcv")

    entry_ts = _resolve_buy_date(prices.index, buy_date)
    latest_ts = prices.index[-1]
    if entry_ts > latest_ts:
        raise ValueError("buy_date_after_latest")

    entry_price = float(prices.loc[entry_ts])
    latest_price = float(prices.loc[latest_ts])
    final_value = round(amount * latest_price / entry_price, 2)
    profit = round(final_value - amount, 2)
    return_pct = round((latest_price / entry_price - 1) * 100, 2)
    holding_days = int((latest_ts - entry_ts).days)
    holding_years = max(holding_days / 365.25, 1 / 365.25)
    growth = latest_price / entry_price
    annualized_pct = round((growth ** (1.0 / holding_years) - 1) * 100, 2)

    data_start = prices.index[0].strftime("%Y-%m-%d")
    data_end = latest_ts.strftime("%Y-%m-%d")

    return {
        "buy_date_requested": pd.Timestamp(buy_date).strftime("%Y-%m-%d"),
        "buy_date": entry_ts.strftime("%Y-%m-%d"),
        "buy_price": round(entry_price, 2),
        "latest_date": latest_ts.strftime("%Y-%m-%d"),
        "latest_price": round(latest_price, 2),
        "amount": round(amount, 2),
        "final_value": final_value,
        "profit": profit,
        "return_pct": return_pct,
        "annualized_return_pct": annualized_pct,
        "holding_days": holding_days,
        "holding_years": round(holding_years, 2),
        "data_start": data_start,
        "data_end": data_end,
        "date_snapped": entry_ts.strftime("%Y-%m-%d")
        != pd.Timestamp(buy_date).strftime("%Y-%m-%d"),
    }


def lump_sum_meta(ohlcv: pd.DataFrame) -> dict:
    if ohlcv.empty:
        raise ValueError("no_ohlcv")
    df = ohlcv.sort_values("trade_date")
    return {
        "data_start": pd.Timestamp(df["trade_date"].iloc[0]).strftime("%Y-%m-%d"),
        "data_end": pd.Timestamp(df["trade_date"].iloc[-1]).strftime("%Y-%m-%d"),
        "latest_price": round(float(df["close"].iloc[-1]), 2),
    }
