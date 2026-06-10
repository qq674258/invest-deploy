from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select

from invest.config_loader import InstrumentProfile, OhlcvSource, load_instruments
from invest.db.models import Instrument
from invest.db.session import get_session

DISPLAY_ASSET_CLASSES = frozenset(
    {"index_us", "index_jp", "index_de", "cn_active_fund"}
)


def profile_from_raw(item: dict[str, Any]) -> InstrumentProfile:
    ohlcv_cfg = item.get("ohlcv")
    ohlcv = None
    if ohlcv_cfg:
        ohlcv = OhlcvSource(
            provider=ohlcv_cfg.get("provider", "yfinance"),
            symbol=ohlcv_cfg["symbol"],
        )
    nav_cfg = item.get("nav")
    crawl = item.get("crawl") or {}
    crawl_job = crawl.get("job")
    if not crawl_job and item.get("asset_class") == "cn_active_fund":
        crawl_job = "crawl_cn_fund"
    return InstrumentProfile(
        instrument_id=item["instrument_id"],
        display_name=item["display_name"],
        asset_class=item["asset_class"],
        enabled=item.get("enabled", True),
        calendar_id=item.get("calendar_id", "US_NYSE"),
        ohlcv=ohlcv,
        crawl_job=crawl_job,
        raw=item,
    )


def profile_from_db_row(row: Instrument) -> InstrumentProfile | None:
    if not row.config_json:
        return None
    try:
        item = json.loads(row.config_json)
    except json.JSONDecodeError:
        return None
    item.setdefault("instrument_id", row.instrument_id)
    item.setdefault("display_name", row.display_name)
    item.setdefault("asset_class", row.asset_class)
    item["enabled"] = row.enabled
    return profile_from_raw(item)


def load_db_only_profiles() -> list[InstrumentProfile]:
    yaml_ids = {p.instrument_id for p in load_instruments()}
    out: list[InstrumentProfile] = []
    with get_session() as session:
        rows = session.execute(select(Instrument)).scalars().all()
        for row in rows:
            if row.instrument_id in yaml_ids:
                continue
            p = profile_from_db_row(row)
            if p:
                out.append(p)
    return out


def load_all_instruments() -> list[InstrumentProfile]:
    """YAML 配置 + 仅存在于 DB 的管理员录入标的。"""
    merged = list(load_instruments())
    merged.extend(load_db_only_profiles())
    return merged


def get_instrument(instrument_id: str) -> InstrumentProfile | None:
    for p in load_all_instruments():
        if p.instrument_id == instrument_id:
            return p
    return None


def list_display_instruments() -> list[InstrumentProfile]:
    return [
        p
        for p in load_all_instruments()
        if p.enabled and p.asset_class in DISPLAY_ASSET_CLASSES
    ]
