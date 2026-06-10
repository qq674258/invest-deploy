from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta
from html import unescape

from invest.data.providers.base import MacroPoint
from invest.http_client import make_httpx_client
from invest.core.crawl_config import get_endpoint, get_multpl_slugs
from invest.settings import get_ohlcv_lookback_days

logger = logging.getLogger(__name__)


class MultplProvider:
    def fetch_series(
        self,
        series_id: str,
        lookback_days: int | None = None,
    ) -> list[MacroPoint]:
        slugs = get_multpl_slugs()
        slug = slugs.get(series_id)
        if not slug:
            raise ValueError(f"multpl 未配置序列: {series_id}")

        lookback_days = get_ohlcv_lookback_days(lookback_days)
        cutoff = date.today() - timedelta(days=lookback_days + 60)
        url = get_endpoint("multpl_table_template", slug=slug)

        with make_httpx_client() as client:
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text

        points = _parse_monthly_table(html)
        out = [p for p in points if p.trade_date >= cutoff]
        logger.info("multpl %s 解析 %d 条（过滤后 %d）", series_id, len(points), len(out))
        return out


def _parse_monthly_table(html: str) -> list[MacroPoint]:
    """按 <tr> 解析 Date / Value 两列（multpl 新版表格不再是一维 td 交替）。"""
    points: list[MacroPoint] = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.IGNORECASE | re.DOTALL):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.IGNORECASE | re.DOTALL)
        if len(tds) < 2:
            continue
        d_raw = _clean_cell(tds[0])
        v_raw = _clean_cell(tds[1])
        if not d_raw or not v_raw or d_raw.lower() == "date":
            continue
        try:
            trade_date = _parse_multpl_date(d_raw)
            num = re.search(r"[-+]?\d*\.?\d+", v_raw.replace(",", ""))
            if not num:
                continue
            value = float(num.group())
        except (ValueError, TypeError):
            continue
        points.append(MacroPoint(trade_date=trade_date, value=value))
    points.sort(key=lambda p: p.trade_date)
    return points


def _clean_cell(raw: str) -> str:
    text = unescape(re.sub(r"<[^>]+>", "", raw))
    return text.replace("\xa0", " ").replace("\u2002", " ").strip()


def _parse_multpl_date(raw: str) -> date:
    raw = raw.strip()
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"无法解析日期: {raw}")
