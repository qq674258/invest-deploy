from __future__ import annotations

import logging
from datetime import date, timedelta

from invest.data.providers.base import MacroPoint
from invest.http_client import make_httpx_client
from invest.core.crawl_config import get_endpoint
from invest.settings import get_ohlcv_lookback_days, settings

logger = logging.getLogger(__name__)


class FredProvider:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.fred_api_key

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def fetch_series(
        self,
        fred_series_id: str,
        lookback_days: int | None = None,
    ) -> list[MacroPoint]:
        if not self.available:
            logger.warning("未配置 FRED_API_KEY，跳过 %s", fred_series_id)
            return []

        lookback_days = get_ohlcv_lookback_days(lookback_days)
        start = (date.today() - timedelta(days=lookback_days + 30)).isoformat()
        params = {
            "series_id": fred_series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "observation_start": start,
            "sort_order": "asc",
        }
        with make_httpx_client() as client:
            resp = client.get(get_endpoint("fred_observations"), params=params)
            resp.raise_for_status()
            payload = resp.json()

        points: list[MacroPoint] = []
        for obs in payload.get("observations", []):
            raw_val = obs.get("value")
            if raw_val in (None, ".", ""):
                continue
            try:
                value = float(raw_val)
            except ValueError:
                continue
            d = date.fromisoformat(obs["date"])
            points.append(MacroPoint(trade_date=d, value=value))
        return points
