from __future__ import annotations

import math
from typing import Any

import pandas as pd

from invest.core.chart_constants import CHART_DEFAULT_LIMIT
from invest.core.chart_macro import build_chart_macro
from invest.core.drawdown import DRAWDOWN_6M_LOOKBACK_DAYS, rolling_drawdown_from_high
from invest.data.repository.score_repo import ScoreRepository


def _series_to_json(s: pd.Series) -> list[float | None]:
    out: list[float | None] = []
    for v in s:
        if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
            out.append(None)
        else:
            out.append(float(v))
    return out


def build_market_chart(
    repo: ScoreRepository,
    instrument_id: str,
    limit: int = CHART_DEFAULT_LIMIT,
) -> dict[str, Any]:
    from invest.core.instrument_registry import get_instrument

    profile = get_instrument(instrument_id)
    if not profile:
        raise ValueError("unknown_instrument")

    ohlcv = repo.load_ohlcv_df(instrument_id)
    if ohlcv.empty:
        raise ValueError("no_ohlcv")

    df = ohlcv.sort_values("trade_date").tail(limit).copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    close = df.set_index("trade_date")["close"].astype(float)
    dd = rolling_drawdown_from_high(close, DRAWDOWN_6M_LOOKBACK_DAYS)

    dates = [d.strftime("%Y-%m-%d") for d in df["trade_date"]]
    idx = pd.DatetimeIndex(df["trade_date"])

    candles = []
    volumes = []
    for _, row in df.iterrows():
        candles.append(
            [
                round(float(row["open"]), 4),
                round(float(row["close"]), 4),
                round(float(row["low"]), 4),
                round(float(row["high"]), 4),
            ]
        )
        volumes.append(round(float(row.get("volume", 0) or 0), 2))

    indicators: dict[str, list[float | None]] = {
        "drawdown_6m_high": _series_to_json((dd * 100).reindex(idx)),
    }
    metric_ids = ["drawdown_6m_high"]

    macro_overlays, macro_snapshot = build_chart_macro(repo, profile, idx)
    indicators.update(macro_overlays)
    for mid in macro_overlays:
        if mid not in metric_ids:
            metric_ids.append(mid)

    return {
        "instrument_id": instrument_id,
        "display_name": profile.display_name,
        "dates": dates,
        "candles": candles,
        "volume": volumes,
        "indicators": indicators,
        "metric_ids": metric_ids,
        "macro_snapshot": macro_snapshot,
    }
