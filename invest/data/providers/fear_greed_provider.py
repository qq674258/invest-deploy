from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from invest.core.crawl_config import get_endpoint
from invest.data.providers.base import MacroPoint
from invest.http_client import make_httpx_client
from invest.settings import get_ohlcv_lookback_days

logger = logging.getLogger(__name__)


class FearGreedProvider:
    def fetch_daily(self, lookback_days: int | None = None) -> list[MacroPoint]:
        lookback_days = get_ohlcv_lookback_days(lookback_days)
        with make_httpx_client() as client:
            resp = client.get(get_endpoint("cnn_fear_greed"))
            resp.raise_for_status()
            payload = resp.json()

        hist = payload.get("fear_and_greed_historical", {})
        data = hist.get("data") or []
        points: list[MacroPoint] = []
        for item in data:
            ts = item.get("x")
            score = item.get("y")
            if ts is None or score is None:
                continue
            try:
                dt = datetime.fromtimestamp(float(ts) / 1000.0, tz=timezone.utc).date()
                points.append(MacroPoint(trade_date=dt, value=float(score)))
            except (TypeError, ValueError, OSError):
                continue

        if not points:
            fg = payload.get("fear_and_greed", {})
            if fg.get("score") is not None:
                today = date.today()
                points.append(MacroPoint(trade_date=today, value=float(fg["score"])))

        by_date: dict[date, MacroPoint] = {}
        for pt in points:
            by_date[pt.trade_date] = pt
        points = [by_date[d] for d in sorted(by_date)]
        if lookback_days and points:
            cutoff = date.today() - __import__("datetime").timedelta(days=lookback_days + 30)
            points = [p for p in points if p.trade_date >= cutoff]
        logger.info("CNN 恐惧贪婪指数 %d 条", len(points))
        return points
