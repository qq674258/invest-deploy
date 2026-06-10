from __future__ import annotations

import csv
import io
import logging
import re
from datetime import date, datetime, timedelta

from invest.core.crawl_config import get_endpoint, get_provider_cfg
from invest.data.providers.base import MacroPoint
from invest.http_client import make_httpx_client
from invest.settings import get_ohlcv_lookback_days

logger = logging.getLogger(__name__)

_RATIO_COL_HINTS = (
    "P/C RATIO",
    "P/C Ratio",
    "TOTAL VOLUME P/C RATIO",
)

_CSV_SOURCES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("cboe_pc_ratio_archive", ("TOTAL VOLUME P/C RATIO", "P/C Ratio")),
    ("cboe_totalpc_archive", ("P/C Ratio",)),
    ("cboe_totalpc_csv", ("P/C Ratio",)),
)


class CboePutCallProvider:
    """Cboe Total Put/Call：CDN 历史 CSV + 每日统计页当日快照。"""

    def fetch_series(self, lookback_days: int | None = None) -> list[MacroPoint]:
        lookback_days = get_ohlcv_lookback_days(lookback_days)
        cutoff = date.today() - timedelta(days=lookback_days + 30)
        by_date: dict[date, float] = {}

        for endpoint_key, ratio_hints in _CSV_SOURCES:
            url = get_endpoint(endpoint_key)
            if not url:
                continue
            try:
                rows = self._fetch_csv(url, ratio_hints)
            except Exception as exc:
                logger.warning("Cboe CSV %s 拉取失败: %s", endpoint_key, exc)
                continue
            for pt in rows:
                by_date[pt.trade_date] = pt.value
            logger.info("Cboe CSV %s 解析 %d 条", endpoint_key, len(rows))

        for pt in self.fetch_daily_snapshot():
            by_date[pt.trade_date] = pt.value

        out = [
            MacroPoint(trade_date=d, value=v)
            for d, v in sorted(by_date.items())
            if d >= cutoff
        ]
        logger.info(
            "Cboe Put/Call 合并 %d 条（回溯 %d 天，最早 %s）",
            len(out),
            lookback_days,
            out[0].trade_date if out else "—",
        )
        return out

    def fetch_daily_snapshot(
        self,
        ratio_name: str | None = None,
    ) -> list[MacroPoint]:
        pcfg = get_provider_cfg()
        ratio_name = ratio_name or str(
            pcfg.get("cboe_put_call_ratio_name", "TOTAL PUT/CALL RATIO")
        )
        fallbacks = tuple(pcfg.get("cboe_put_call_fallbacks") or ())
        with make_httpx_client() as client:
            resp = client.get(get_endpoint("cboe_daily_stats"))
            resp.raise_for_status()
            html = resp.text

        ratios = _parse_ratios(html)
        if not ratios:
            logger.warning("Cboe 页面未解析到 Put/Call 比率")
            return []

        value = ratios.get(ratio_name.upper())
        if value is None:
            for alt in fallbacks:
                value = ratios.get(alt.upper())
                if value is not None:
                    logger.info("使用备用 Put/Call: %s", alt)
                    break
        if value is None:
            logger.warning("Cboe 无目标比率 %s，可用: %s", ratio_name, list(ratios)[:8])
            return []

        today = date.today()
        logger.info("Cboe Put/Call %s = %.4f (%s)", ratio_name, value, today)
        return [MacroPoint(trade_date=today, value=value)]

    def _fetch_csv(self, url: str, ratio_hints: tuple[str, ...]) -> list[MacroPoint]:
        with make_httpx_client() as client:
            resp = client.get(url)
            resp.raise_for_status()
        return _parse_pc_csv(resp.text, ratio_hints)


def _parse_pc_csv(text: str, ratio_hints: tuple[str, ...]) -> list[MacroPoint]:
    lines = text.splitlines()
    header_idx = _find_header_row(lines)
    if header_idx is None:
        return []

    reader = csv.DictReader(io.StringIO("\n".join(lines[header_idx:])), skipinitialspace=True)
    if not reader.fieldnames:
        return []

    date_col = _pick_column(reader.fieldnames, ("DATE", "TRADE_DATE"))
    ratio_col = _pick_ratio_column(reader.fieldnames, ratio_hints)
    if not date_col or not ratio_col:
        return []

    points: list[MacroPoint] = []
    for row in reader:
        d_raw = (row.get(date_col) or "").strip()
        v_raw = (row.get(ratio_col) or "").strip()
        if not d_raw or not v_raw:
            continue
        try:
            trade_date = _parse_trade_date(d_raw)
            value = float(v_raw.replace(",", ""))
        except (ValueError, TypeError):
            continue
        if not _valid_ratio(value):
            continue
        points.append(MacroPoint(trade_date=trade_date, value=value))
    return points


def _find_header_row(lines: list[str]) -> int | None:
    for i, line in enumerate(lines):
        upper = line.upper()
        if "P/C" in upper and ("DATE" in upper or "TRADE_DATE" in upper):
            return i
    return None


def _pick_column(fieldnames: list[str], hints: tuple[str, ...]) -> str | None:
    normalized = {f.strip().upper(): f for f in fieldnames if f}
    for hint in hints:
        if hint.upper() in normalized:
            return normalized[hint.upper()]
    for f in fieldnames:
        if f and f.strip().upper() in hints:
            return f
    return None


def _pick_ratio_column(
    fieldnames: list[str], ratio_hints: tuple[str, ...]
) -> str | None:
    for hint in ratio_hints:
        col = _pick_column(fieldnames, (hint,))
        if col:
            return col
    for f in fieldnames:
        if f and any(h.upper() in f.upper() for h in _RATIO_COL_HINTS):
            return f
    return None


def _parse_trade_date(raw: str) -> date:
    raw = raw.strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return datetime.fromisoformat(raw).date()


def _valid_ratio(value: float) -> bool:
    return 0.05 < value < 5.0


def _parse_ratios(html: str) -> dict[str, float]:
    out: dict[str, float] = {}
    patterns = (
        r'"name"\s*:\s*"([^"]+)"\s*,\s*"value"\s*:\s*"([^"]*)"',
        r'\\"name\\":\\"([^"\\]+)\\",\\"value\\":\\"([^"\\]*)\\"',
        r"name\\\":\\\"([^\\\"]+)\\\"\\,\\\"value\\\":\\\"([^\\\"]*)\\\"",
    )
    for pat in patterns:
        for name, raw in re.findall(pat, html, flags=re.IGNORECASE):
            if "PUT/CALL" not in name.upper():
                continue
            try:
                val = float(raw)
            except ValueError:
                continue
            if _valid_ratio(val):
                out[name.strip().upper()] = val
    return out
