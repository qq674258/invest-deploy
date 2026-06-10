from __future__ import annotations

import logging
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from invest.data.providers.base import MacroPoint, OhlcvBar
from invest.settings import get_ohlcv_lookback_days, settings

logger = logging.getLogger(__name__)


class YFinanceProvider:
    """yfinance 行情与宏观序列（VIX、汇率等）。"""

    def fetch_ohlcv(
        self,
        symbol: str,
        lookback_days: int | None = None,
    ) -> list[OhlcvBar]:
        lookback_days = get_ohlcv_lookback_days(lookback_days)
        end = date.today() + timedelta(days=1)
        start = end - timedelta(days=lookback_days + 30)

        df = None
        try:
            df = yf.download(
                symbol,
                start=start.isoformat(),
                end=end.isoformat(),
                progress=False,
                auto_adjust=True,
                threads=False,
            )
            if df is not None and not df.empty and isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
        except Exception as exc:
            logger.warning("yfinance download 失败 %s: %s", symbol, exc)

        if df is None or df.empty:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start.isoformat(), end=end.isoformat(), auto_adjust=True)

        if df is None or df.empty:
            logger.warning("yfinance 无数据: %s", symbol)
            return []

        return self._df_to_bars(df)

    def fetch_macro_daily(
        self,
        symbol: str,
        lookback_days: int | None = None,
    ) -> list[MacroPoint]:
        """用收盘价作为宏观日序列（VIX、汇率等）。"""
        bars = self.fetch_ohlcv(symbol, lookback_days=lookback_days)
        return [MacroPoint(trade_date=b.trade_date, value=b.close) for b in bars]

    @staticmethod
    def _df_to_bars(df: pd.DataFrame) -> list[OhlcvBar]:
        bars: list[OhlcvBar] = []
        for idx, row in df.iterrows():
            trade_date = idx.date() if hasattr(idx, "date") else pd.Timestamp(idx).date()
            o, h, l, c = float(row["Open"]), float(row["High"]), float(row["Low"]), float(row["Close"])
            vol = float(row.get("Volume", 0) or 0)
            if pd.isna(o) or pd.isna(c):
                continue
            bars.append(
                OhlcvBar(
                    trade_date=trade_date,
                    open=o,
                    high=h,
                    low=l,
                    close=c,
                    volume=vol,
                )
            )
        return bars
