from __future__ import annotations

import io
import logging
from datetime import date, timedelta

import pandas as pd

from invest.data.providers.base import OhlcvBar
from invest.http_client import make_httpx_client
from invest.core.crawl_config import get_endpoint
from invest.settings import get_ohlcv_lookback_days

logger = logging.getLogger(__name__)

# Stooq 日线 CSV（免费，无需 API Key）
STOOQ_SYMBOL_MAP = {
    "QQQ": "qqq.us",
    "^GSPC": "spx.us",
    "^NDX": "ndx.us",
    "^N225": "nkx.jp",
    "^GDAXI": "dax.de",
    "^VIX": "vix.us",
    "JPY=X": "usdjpy",
    "EURUSD=X": "eurusd",
}


class StooqProvider:
    def fetch_ohlcv(
        self,
        yfinance_symbol: str,
        lookback_days: int | None = None,
    ) -> list[OhlcvBar]:
        stooq_sym = STOOQ_SYMBOL_MAP.get(yfinance_symbol)
        if not stooq_sym:
            logger.warning("Stooq 无映射: %s", yfinance_symbol)
            return []

        lookback_days = get_ohlcv_lookback_days(lookback_days)
        url = f"{get_endpoint('stooq_daily')}?s={stooq_sym}&i=d"
        with make_httpx_client() as client:
            resp = client.get(url)
            resp.raise_for_status()
            text = resp.text.strip()
            if not text.startswith("Date"):
                logger.warning("Stooq 非 CSV 响应: %s", yfinance_symbol)
                return []
            df = pd.read_csv(io.StringIO(text))

        if df.empty or "Date" not in df.columns:
            return []

        cutoff = date.today() - timedelta(days=lookback_days + 30)
        bars: list[OhlcvBar] = []
        for _, row in df.iterrows():
            d = pd.to_datetime(row["Date"]).date()
            if d < cutoff:
                continue
            try:
                bars.append(
                    OhlcvBar(
                        trade_date=d,
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=float(row.get("Volume", 0) or 0),
                    )
                )
            except (ValueError, TypeError):
                continue
        bars.sort(key=lambda b: b.trade_date)
        return bars
