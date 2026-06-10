from __future__ import annotations

import logging
import time
from datetime import date, timedelta

import pandas as pd
import yaml

from invest.data.providers.base import MacroPoint
from invest.data.providers.yfinance_provider import YFinanceProvider
from invest.core.crawl_config import get_defaults
from invest.settings import CONFIG_DIR, get_ohlcv_lookback_days

logger = logging.getLogger(__name__)


class IndexBreadthProvider:
    """指数成分股样本：收盘价高于 200 日均线的占比。"""

    def __init__(self, constituents_file: str, label: str):
        self.constituents_file = constituents_file
        self.label = label
        self.yf = YFinanceProvider()

    def load_symbols(self) -> list[str]:
        path = CONFIG_DIR / self.constituents_file
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return list(data.get("symbols") or [])

    def compute_pct_above_ma200(
        self, lookback_days: int | None = None
    ) -> list[MacroPoint]:
        symbols = self.load_symbols()
        if not symbols:
            logger.warning("%s 成分股配置为空: %s", self.label, self.constituents_file)
            return []

        lookback_days = get_ohlcv_lookback_days(lookback_days)
        end = date.today() + timedelta(days=1)
        start = end - timedelta(days=lookback_days + 280)

        daily_pct: dict[date, list[float]] = {}
        for sym in symbols:
            try:
                bars = self.yf.fetch_ohlcv(sym, lookback_days=lookback_days + 280)
            except Exception as exc:
                logger.warning("%s 广度 %s 失败: %s", self.label, sym, exc)
                continue
            if len(bars) < 210:
                continue
            df = pd.DataFrame(
                {"close": [b.close for b in bars], "date": [b.trade_date for b in bars]}
            )
            df = df.sort_values("date")
            df["ma200"] = df["close"].rolling(200).mean()
            df["above"] = (df["close"] > df["ma200"]).astype(float)
            for _, row in df.dropna(subset=["ma200"]).iterrows():
                d = row["date"]
                if d < start:
                    continue
                daily_pct.setdefault(d, []).append(float(row["above"]))
            sleep_sec = float(get_defaults().get("breadth_symbol_sleep_sec", 0.35))
            time.sleep(sleep_sec)

        points: list[MacroPoint] = []
        for d, flags in sorted(daily_pct.items()):
            if len(flags) < max(5, len(symbols) // 3):
                continue
            pct = sum(flags) / len(flags) * 100.0
            points.append(MacroPoint(trade_date=d, value=round(pct, 4)))
        logger.info(
            "%s 广度 %d 个交易日（样本 %d 只）",
            self.label,
            len(points),
            len(symbols),
        )
        return points
