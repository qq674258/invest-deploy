from __future__ import annotations

import logging
from datetime import date

import yfinance as yf

from invest.data.providers.base import MacroPoint

logger = logging.getLogger(__name__)


class EtfValuationProvider:
    """ETF 估值快照（QQQ→NDX，SPY→SPX）。"""

    def fetch_forward_pe(self, symbol: str) -> list[MacroPoint]:
        try:
            info = yf.Ticker(symbol).info or {}
        except Exception as exc:
            logger.warning("%s 估值 info 失败: %s", symbol, exc)
            return []
        pe = info.get("forwardPE") or info.get("trailingPE")
        if pe is None:
            return []
        return [MacroPoint(trade_date=date.today(), value=float(pe))]

    def fetch_trailing_pe(self, symbol: str) -> list[MacroPoint]:
        """滚动市盈率 TTM（与行情软件 ETF 口径一致）。"""
        try:
            info = yf.Ticker(symbol).info or {}
        except Exception as exc:
            logger.warning("%s trailingPE 失败: %s", symbol, exc)
            return []
        pe = info.get("trailingPE")
        if pe is None or not isinstance(pe, (int, float)) or pe <= 0:
            logger.warning("%s 无有效 trailingPE", symbol)
            return []
        return [MacroPoint(trade_date=date.today(), value=float(pe))]
