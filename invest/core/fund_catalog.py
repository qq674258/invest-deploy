from __future__ import annotations

from typing import Any

from invest.config_loader import InstrumentProfile
from invest.core.fund_performance import compute_period_returns
from invest.core.instrument_registry import get_instrument, list_display_instruments
from invest.data.repository.fund_repo import FundRepository
from invest.data.repository.user_fund_repo import UserFundRepository
from invest.db.session import get_session


def profile_from_fund_dict(raw: dict) -> InstrumentProfile:
    return InstrumentProfile(
        instrument_id=str(raw["instrument_id"]),
        display_name=str(raw["display_name"]),
        asset_class="cn_active_fund",
        enabled=bool(raw.get("enabled", True)),
        calendar_id=str(raw.get("calendar_id") or "CN_SSE_SZSE"),
        ohlcv=None,
        crawl_job=(raw.get("crawl") or {}).get("job") or "crawl_cn_fund",
        raw=raw,
    )


def list_public_funds() -> list[InstrumentProfile]:
    return [
        p
        for p in list_display_instruments()
        if p.asset_class == "cn_active_fund"
    ]


def list_all_funds() -> list[InstrumentProfile]:
    """管理后台基金 + 各前台用户曾添加的基金（去重合并）。"""
    merged: dict[str, InstrumentProfile] = {
        p.instrument_id: p for p in list_public_funds()
    }
    with get_session() as session:
        repo = UserFundRepository(session)
        for row in repo.list_all_enabled_distinct():
            iid = row.instrument_id
            if iid in merged:
                continue
            inst = get_instrument(iid)
            if inst and inst.asset_class == "cn_active_fund":
                merged[iid] = inst
            else:
                merged[iid] = profile_from_fund_dict(repo.fund_to_profile_dict(row))
    return list(merged.values())


def filter_fund_profiles(
    profiles: list[InstrumentProfile],
    *,
    q: str | None = None,
    code: str | None = None,
    market: str | None = None,
    sector: str | None = None,
) -> list[InstrumentProfile]:
    out = profiles
    if code and code.strip():
        c = code.strip()
        c_upper = c.upper()
        if c_upper.startswith("FUND_"):
            c = c[5:]
        out = [
            p
            for p in out
            if p.raw.get("fund_code") == c
            or p.instrument_id == f"FUND_{c}"
            or p.instrument_id == c_upper
        ]
    if q and q.strip():
        ql = q.strip().lower()
        out = [
            p
            for p in out
            if ql in p.display_name.lower()
            or ql in (p.raw.get("fund_code") or "").lower()
            or ql in p.instrument_id.lower()
            or ql in (p.raw.get("fund_manager") or "").lower()
            or ql in (p.raw.get("sector") or "").lower()
        ]
    if market and market.strip():
        out = [p for p in out if p.raw.get("market") == market.strip()]
    if sector and sector.strip():
        out = [p for p in out if p.raw.get("sector") == sector.strip()]
    return out


def build_fund_list_items(
    profiles: list[InstrumentProfile],
    fund_repo: FundRepository,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for p in profiles:
        nav_df = fund_repo.load_nav_df(p.instrument_id)
        periods = compute_period_returns(nav_df)
        period_map = {row["period_id"]: row["return_pct"] for row in periods}
        latest = fund_repo.latest_nav(p.instrument_id)
        items.append(
            {
                "instrument_id": p.instrument_id,
                "display_name": p.display_name,
                "fund_code": p.raw.get("fund_code"),
                "market": p.raw.get("market"),
                "sector": p.raw.get("sector"),
                "fund_manager": p.raw.get("fund_manager"),
                "latest_nav_date": latest.nav_date.isoformat() if latest else None,
                "nav_rows": len(nav_df),
                "returns": {
                    "ytd": period_map.get("ytd"),
                    "3m": period_map.get("3m"),
                    "6m": period_map.get("6m"),
                    "1y": period_map.get("1y"),
                    "3y": period_map.get("3y"),
                    "5y": period_map.get("5y"),
                    "si": period_map.get("si"),
                },
            }
        )
    return items
