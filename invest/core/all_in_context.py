from __future__ import annotations

import pandas as pd

from invest.core.drawdown import rolling_drawdown_from_high

# All in 固定：相对近半年（约 126 个交易日）滚动最高价的回撤
ALL_IN_DRAWDOWN_LOOKBACK_DAYS = 126
ALL_IN_DRAWDOWN_LABEL = "近半年"

DRAWDOWN_TIERS = [
    ("shallow", "轻微回撤", -0.05, 0.0, "接近阶段新高，追涨 All in 性价比偏低，宜观望或定投"),
    ("mild", "轻度回撤", -0.10, -0.05, "小幅回调，可小仓试探，不宜重仓一次打满"),
    ("moderate", "中度回撤", -0.20, -0.10, "明显回调，All in 性价比提升，可考虑分批进场"),
    ("deep", "深度回撤", -0.35, -0.20, "深度调整，历史上较好的买入窗口之一，注意现金流"),
    ("extreme", "极端回撤", None, -0.35, "恐慌性下跌，机会与风险并存，仅适合有预案的资金"),
]


def _lookup_series_value(series: pd.Series, ts: pd.Timestamp) -> float | None:
    if series.empty:
        return None
    s = series.sort_index()
    if ts in s.index:
        val = s.loc[ts]
    else:
        sub = s.loc[s.index <= ts]
        if sub.empty:
            return None
        val = sub.iloc[-1]
    if val is None or (isinstance(val, float) and not pd.notna(val)):
        return None
    return float(val)


def _rolling_high(close: pd.Series, lookback_days: int) -> pd.Series:
    lb = int(lookback_days)
    min_periods = min(lb, 20)
    return close.rolling(lb, min_periods=min_periods).max()


def _match_drawdown_tier(dd: float) -> tuple[str, str, str]:
    if dd > -0.05:
        tid, label, _, _, advice = DRAWDOWN_TIERS[0]
        return tid, label, advice
    if dd > -0.10:
        tid, label, _, _, advice = DRAWDOWN_TIERS[1]
        return tid, label, advice
    if dd > -0.20:
        tid, label, _, _, advice = DRAWDOWN_TIERS[2]
        return tid, label, advice
    if dd > -0.35:
        tid, label, _, _, advice = DRAWDOWN_TIERS[3]
        return tid, label, advice
    tid, label, _, _, advice = DRAWDOWN_TIERS[4]
    return tid, label, advice


def _drawdown_tier_rows() -> list[dict]:
    return [
        {"id": "shallow", "label": "轻微回撤", "range": "> -5%", "advice": DRAWDOWN_TIERS[0][4]},
        {"id": "mild", "label": "轻度回撤", "range": "-10% ~ -5%", "advice": DRAWDOWN_TIERS[1][4]},
        {"id": "moderate", "label": "中度回撤", "range": "-20% ~ -10%", "advice": DRAWDOWN_TIERS[2][4]},
        {"id": "deep", "label": "深度回撤", "range": "-35% ~ -20%", "advice": DRAWDOWN_TIERS[3][4]},
        {"id": "extreme", "label": "极端回撤", "range": "≤ -35%", "advice": DRAWDOWN_TIERS[4][4]},
    ]


def build_all_in_context(
    repo,
    instrument_id: str,
    ohlcv: pd.DataFrame,
    buy_date: str,
    latest_date: str,
) -> dict:
    _ = repo, instrument_id
    if ohlcv.empty:
        return {"drawdown_window_label": ALL_IN_DRAWDOWN_LABEL, "signals": {}}

    df = ohlcv.sort_values("trade_date").copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    close = df.set_index("trade_date")["close"].astype(float)
    dd_series = rolling_drawdown_from_high(close, ALL_IN_DRAWDOWN_LOOKBACK_DAYS)
    high_series = _rolling_high(close, ALL_IN_DRAWDOWN_LOOKBACK_DAYS)

    buy_ts = pd.Timestamp(buy_date)
    latest_ts = pd.Timestamp(latest_date)
    buy_dd_raw = _lookup_series_value(dd_series, buy_ts)
    latest_dd_raw = _lookup_series_value(dd_series, latest_ts)
    buy_dd = round(buy_dd_raw, 4) if buy_dd_raw is not None else None
    latest_dd = round(latest_dd_raw, 4) if latest_dd_raw is not None else None
    buy_high = _lookup_series_value(high_series, buy_ts)
    latest_high = _lookup_series_value(high_series, latest_ts)

    if buy_dd is not None:
        dd_id, dd_label, dd_advice = _match_drawdown_tier(buy_dd)
    else:
        dd_id, dd_label, dd_advice = None, None, None

    if latest_dd is not None:
        lat_id, lat_label, _ = _match_drawdown_tier(latest_dd)
    else:
        lat_id, lat_label = None, None

    return {
        "drawdown_window": "6m",
        "drawdown_window_days": ALL_IN_DRAWDOWN_LOOKBACK_DAYS,
        "drawdown_window_label": ALL_IN_DRAWDOWN_LABEL,
        "signals": {
            "drawdown": {
                "buy": buy_dd,
                "latest": latest_dd,
                "buy_pct": round(buy_dd * 100, 2) if buy_dd is not None else None,
                "latest_pct": round(latest_dd * 100, 2) if latest_dd is not None else None,
                "buy_high": round(buy_high, 4) if buy_high is not None else None,
                "latest_high": round(latest_high, 4) if latest_high is not None else None,
                "buy_tier_id": dd_id,
                "buy_label": dd_label,
                "latest_tier_id": lat_id,
                "latest_label": lat_label,
                "advice": dd_advice,
                "tiers": _drawdown_tier_rows(),
                "note": (
                    f"买入价相对{ALL_IN_DRAWDOWN_LABEL}（约 {ALL_IN_DRAWDOWN_LOOKBACK_DAYS} 个交易日）"
                    "滚动最高价的回撤；负值表示低于高点，如 -15% 表示距高点跌 15%"
                ),
            },
        },
    }
