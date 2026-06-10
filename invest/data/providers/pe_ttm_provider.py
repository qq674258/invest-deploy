from __future__ import annotations

import logging
from datetime import date

from invest.core.crawl_config import get_multpl_slugs
from invest.data.providers.base import MacroPoint
from invest.data.providers.etf_valuation_provider import EtfValuationProvider
from invest.data.providers.multpl_provider import MultplProvider

logger = logging.getLogger(__name__)

# 日频 TTM PE 用 ETF 代表指数；历史月度仍来自 multpl（标普口径，作长期参考）
ETF_BY_SERIES: dict[str, str] = {
    "macro:ndx:pe_ttm": "QQQ",
    "macro:spx:pe_ttm": "SPY",
}


class PeTtmProvider:
    """PE-TTM：multpl 月度历史 + Yahoo ETF trailingPE 日频快照（覆盖当月）。"""

    def __init__(self) -> None:
        self._multpl = MultplProvider()
        self._etf = EtfValuationProvider()

    def fetch_series(
        self,
        series_id: str,
        lookback_days: int | None = None,
    ) -> list[MacroPoint]:
        slugs = get_multpl_slugs()
        if series_id not in slugs:
            raise ValueError(f"pe_ttm 未配置 multpl slug: {series_id}")

        monthly = self._multpl.fetch_series(series_id, lookback_days=lookback_days)
        symbol = ETF_BY_SERIES.get(series_id)
        if not symbol:
            return monthly

        snap = self._etf.fetch_trailing_pe(symbol)
        if not snap:
            logger.warning("%s 无 Yahoo trailingPE，仅保留 multpl 月度", series_id)
            return monthly

        merged = _merge_trailing_snapshot(monthly, snap[0])
        logger.info(
            "%s PE-TTM: multpl %d 条 + %s 日频 %.2f → 合并 %d 条",
            series_id,
            len(monthly),
            symbol,
            snap[0].value,
            len(merged),
        )
        return merged


def _merge_trailing_snapshot(
    monthly: list[MacroPoint], snap: MacroPoint
) -> list[MacroPoint]:
    """用 ETF 日频 TTM 覆盖快照所在自然月及之后的 multpl 月度点。"""
    if not monthly:
        return [snap]
    snap_ym = (snap.trade_date.year, snap.trade_date.month)
    kept = [
        p
        for p in monthly
        if (p.trade_date.year, p.trade_date.month) < snap_ym
    ]
    kept.append(snap)
    kept.sort(key=lambda p: p.trade_date)
    return kept
