from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from invest.config_loader import InstrumentProfile
from invest.core.chart_constants import FUND_CHART_DEFAULT_LIMIT
from invest.core.fund_performance import (
    build_performance_chart,
    compute_period_returns,
)
from invest.core.instrument_registry import get_instrument
from invest.core.fund_catalog import (
    build_fund_list_items,
    filter_fund_profiles,
    list_all_funds,
    profile_from_fund_dict,
)
from invest.data.providers.eastmoney_fund import EastmoneyFundProvider
from invest.data.repository.admin_repo import AdminRepository
from invest.data.repository.fund_repo import FundRepository
from invest.data.repository.user_fund_repo import UserFundRepository
from invest.db.session import get_session

router = APIRouter(prefix="/api/v1/funds", tags=["funds"])


def _require_fund(instrument_id: str) -> tuple[InstrumentProfile, str]:
    profile = get_instrument(instrument_id)
    if profile and profile.asset_class == "cn_active_fund":
        fund_code = profile.raw.get("fund_code") or profile.raw.get("nav", {}).get(
            "symbol"
        )
        if fund_code:
            return profile, str(fund_code)
    with get_session() as session:
        repo = UserFundRepository(session)
        row = repo.find_any_enabled(instrument_id)
        if row:
            raw = repo.fund_to_profile_dict(row)
            profile = profile_from_fund_dict(raw)
            fund_code = raw.get("fund_code") or raw.get("nav", {}).get("symbol")
            if fund_code:
                return profile, str(fund_code)
    raise HTTPException(404, "基金不存在")


@router.get("")
def list_funds_catalog(
    q: str | None = Query(None, description="名称/代码/经理/板块模糊搜索"),
    code: str | None = Query(None, description="基金代码精确匹配"),
    market: str | None = Query(None, description="市场筛选"),
    sector: str | None = Query(None, description="板块筛选"),
):
    """公开基金目录：管理后台 + 各用户曾添加的基金。"""
    profiles = filter_fund_profiles(
        list_all_funds(),
        q=q,
        code=code,
        market=market,
        sector=sector,
    )
    with get_session() as session:
        items = build_fund_list_items(profiles, FundRepository(session))
    return {"total": len(items), "items": items}


@router.get("/{instrument_id}")
def fund_summary(instrument_id: str):
    profile, fund_code = _require_fund(instrument_id)
    with get_session() as session:
        fund_repo = FundRepository(session)
        latest = fund_repo.latest_nav(instrument_id)
        nav_df = fund_repo.load_nav_df(instrument_id)
        latest_nav = None
        latest_nav_date = None
        daily_pct = None
        if latest:
            latest_nav = latest.nav
            latest_nav_date = latest.nav_date.isoformat()
            if latest.daily_return is not None:
                daily_pct = round(latest.daily_return * 100, 2)
        periods = compute_period_returns(nav_df)
        nav_rows = len(nav_df)
    return {
        "instrument_id": instrument_id,
        "fund_code": fund_code,
        "display_name": profile.display_name,
        "market": profile.raw.get("market"),
        "sector": profile.raw.get("sector"),
        "fund_type": profile.raw.get("fund_type"),
        "fund_company": profile.raw.get("fund_company"),
        "fund_manager": profile.raw.get("fund_manager"),
        "establish_date": profile.raw.get("establish_date"),
        "manager_ids": profile.raw.get("manager_ids") or [],
        "managers_on_fund": profile.raw.get("managers_on_fund") or [],
        "latest_nav": latest_nav,
        "latest_nav_date": latest_nav_date,
        "daily_return_pct": daily_pct,
        "nav_rows": nav_rows,
        "period_returns": periods,
        "trading_rules": profile.raw.get("trading_rules"),
    }


@router.get("/{instrument_id}/performance")
def fund_performance(
    instrument_id: str,
    limit: int = Query(FUND_CHART_DEFAULT_LIMIT, ge=60, le=2000),
    refresh: bool = Query(False, description="是否尝试从东财刷新阶段涨幅"),
):
    profile, fund_code = _require_fund(instrument_id)
    with get_session() as session:
        nav_df = FundRepository(session).load_nav_df(instrument_id)
    if nav_df.empty:
        raise HTTPException(404, "暂无净值数据，请先在管理后台爬取")
    chart = build_performance_chart(nav_df, limit=limit)
    periods = compute_period_returns(nav_df)
    official: list[dict[str, Any]] = list(profile.raw.get("period_increase") or [])
    if refresh:
        try:
            official = [
                asdict(p)
                for p in EastmoneyFundProvider().fetch_period_increase(fund_code)
            ]
        except Exception:
            pass
    return {
        "instrument_id": instrument_id,
        "chart": chart,
        "computed_periods": periods,
        "official_periods": official,
    }


@router.get("/{instrument_id}/nav")
def fund_nav_history(
    instrument_id: str,
    limit: int = Query(30, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    _require_fund(instrument_id)
    with get_session() as session:
        rows, total = FundRepository(session).list_nav(
            instrument_id, limit=limit, offset=offset
        )
    return {"total": total, "rows": rows}


@router.get("/{instrument_id}/holdings")
def fund_holdings(instrument_id: str):
    profile, fund_code = _require_fund(instrument_id)
    with get_session() as session:
        items, report_date = FundRepository(session).list_holdings(instrument_id)
    if not items:
        try:
            snap = EastmoneyFundProvider().fetch_holdings(fund_code)
            if snap.holdings:
                rd = date.fromisoformat(snap.report_date[:10]) if snap.report_date else date.today()
                with get_session() as session:
                    FundRepository(session).upsert_holdings(
                        instrument_id,
                        fund_code,
                        rd,
                        [asdict(h) for h in snap.holdings],
                    )
                items = [asdict(h) for h in snap.holdings]
                report_date = snap.report_date
        except Exception:
            pass
    return {
        "instrument_id": instrument_id,
        "fund_code": fund_code,
        "report_date": report_date,
        "holdings": items,
        "disclaimer": "持仓为季报披露数据，存在滞后",
    }


@router.get("/{instrument_id}/managers")
def fund_managers(instrument_id: str):
    profile, _ = _require_fund(instrument_id)
    mgr_ids = profile.raw.get("manager_ids") or []
    with get_session() as session:
        profiles = AdminRepository(session).get_manager_profiles(mgr_ids)
    return {
        "instrument_id": instrument_id,
        "manager_ids": mgr_ids,
        "managers_on_fund": profile.raw.get("managers_on_fund") or [],
        "profiles": profiles,
    }


@router.get("/{instrument_id}/trading-rules")
def fund_trading_rules(instrument_id: str):
    profile, fund_code = _require_fund(instrument_id)
    cached = profile.raw.get("trading_rules")
    if cached:
        return {"instrument_id": instrument_id, "rules": cached, "source": "cache"}
    try:
        rules = EastmoneyFundProvider().fetch_trading_rules(fund_code)
        payload = asdict(rules)
        cfg = dict(profile.raw)
        cfg["trading_rules"] = payload
        with get_session() as session:
            AdminRepository(session).upsert_catalog_instrument(
                instrument_id,
                profile.display_name,
                profile.asset_class,
                cfg,
                enabled=profile.enabled,
            )
        return {"instrument_id": instrument_id, "rules": payload, "source": "live"}
    except Exception as exc:
        raise HTTPException(502, f"获取交易规则失败：{exc}") from exc
