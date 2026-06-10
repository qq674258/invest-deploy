from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from invest.data.providers.base import OhlcvBar
from invest.http_client import make_httpx_client
from invest.core.crawl_config import get_endpoint
from invest.settings import get_ohlcv_lookback_days

logger = logging.getLogger(__name__)


class YahooChartProvider:
    """Yahoo Chart API（JSON），yfinance 失败时的备用。"""

    def fetch_ohlcv(
        self,
        symbol: str,
        lookback_days: int | None = None,
    ) -> list[OhlcvBar]:
        lookback_days = get_ohlcv_lookback_days(lookback_days)
        period2 = int(datetime.utcnow().timestamp())
        period1 = int((datetime.utcnow() - timedelta(days=lookback_days + 30)).timestamp())

        params = {
            "period1": period1,
            "period2": period2,
            "interval": "1d",
            "includePrePost": "false",
        }
        url = get_endpoint(
            "yahoo_chart_template", symbol=symbol.replace("^", "%5E")
        )
        with make_httpx_client(headers={"Accept": "application/json"}) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            payload = resp.json()

        result = payload.get("chart", {}).get("result")
        if not result:
            logger.warning("Yahoo chart 无 result: %s", symbol)
            return []

        block = result[0]
        timestamps = block.get("timestamp") or []
        quote = (block.get("indicators") or {}).get("quote", [{}])[0]
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []

        bars: list[OhlcvBar] = []
        for i, ts in enumerate(timestamps):
            c = closes[i] if i < len(closes) else None
            if c is None:
                continue
            try:
                bars.append(
                    OhlcvBar(
                        trade_date=datetime.utcfromtimestamp(ts).date(),
                        open=float(opens[i] or c),
                        high=float(highs[i] or c),
                        low=float(lows[i] or c),
                        close=float(c),
                        volume=float(volumes[i] or 0) if i < len(volumes) else 0.0,
                    )
                )
            except (TypeError, ValueError):
                continue
        bars.sort(key=lambda b: b.trade_date)
        return bars
