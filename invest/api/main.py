from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from invest.api.admin_routes import router as admin_router
from invest.api.cache_middleware import ApiCacheMiddleware, CACHE_MAX_AGE_SEC
from invest.api.fund_routes import router as fund_router
from invest.core.all_in_context import build_all_in_context
from invest.core.chart_constants import CHART_DEFAULT_LIMIT, CHART_MAX_LIMIT
from invest.core.chart_data import build_market_chart
from invest.core.instrument_registry import list_display_instruments
from invest.core.lump_sum_calc import compute_lump_sum_return, lump_sum_meta
from invest.core.market_stats import annualized_return_pct
from invest.core.price_series import load_close_df
from invest.core.site_config import public_site_payload
from invest.data.crawl_service import CrawlService
from invest.data.repository.score_repo import ScoreRepository
from invest.db.session import get_session, init_db
from invest.jobs.scheduler import setup_scheduler, shutdown_scheduler

API_VERSION = "0.7.0"
logger = logging.getLogger(__name__)

_HEALTH_CACHE: tuple[float, dict] | None = None
_HEALTH_TTL_SEC = CACHE_MAX_AGE_SEC

@asynccontextmanager
async def _lifespan(_app: FastAPI):
    setup_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="投资回撤提醒-定投计算器工具", version=API_VERSION, lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ApiCacheMiddleware)

init_db()
app.include_router(admin_router)
app.include_router(fund_router)


def _cached_health_summary() -> dict:
    global _HEALTH_CACHE
    now = time.time()
    if _HEALTH_CACHE and now - _HEALTH_CACHE[0] < _HEALTH_TTL_SEC:
        return _HEALTH_CACHE[1]
    data = CrawlService().health_summary()
    _HEALTH_CACHE = (now, data)
    return data


def _frontend_instruments():
    return list_display_instruments()


@app.get("/api/v1/site/config")
def get_public_site_config():
    return public_site_payload()


@app.get("/api/v1/version")
def version():
    paths = sorted(
        {getattr(r, "path", "") for r in app.routes if getattr(r, "path", "")}
    )
    return {"api_version": API_VERSION, "routes": paths}


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "data": CrawlService().health_summary()}


@app.get("/api/v1/instruments")
def list_instruments():
    return [
        {
            "instrument_id": p.instrument_id,
            "display_name": p.display_name,
            "asset_class": p.asset_class,
            "enabled": p.enabled,
            "fund_code": p.raw.get("fund_code"),
            "market": p.raw.get("market"),
            "sector": p.raw.get("sector"),
        }
        for p in _frontend_instruments()
    ]


@app.get("/api/v1/dashboard")
def dashboard(refresh: bool = Query(False)):
    """总览：指数标的 + 数据新鲜度（主动基金见 /funds）。"""
    global _HEALTH_CACHE
    if refresh:
        _HEALTH_CACHE = None
    health_data = _cached_health_summary()
    profiles = [
        p for p in _frontend_instruments() if p.asset_class != "cn_active_fund"
    ]
    items = []
    last_dates: list[str] = []
    with get_session() as session:
        for p in profiles:
            inst_health = health_data.get("instruments", {}).get(p.instrument_id, {})
            ld = inst_health.get("last_date")
            if ld:
                last_dates.append(ld)
            items.append(
                {
                    "instrument_id": p.instrument_id,
                    "display_name": p.display_name,
                    "asset_class": p.asset_class,
                    "fund_code": p.raw.get("fund_code"),
                    "market": p.raw.get("market"),
                    "sector": p.raw.get("sector"),
                    "fund_manager": p.raw.get("fund_manager"),
                    "latest_nav": None,
                    "latest_daily_return_pct": None,
                    "data": inst_health,
                }
            )
    as_of = max(last_dates) if last_dates else date.today().isoformat()
    return {
        "as_of": as_of,
        "items": items,
        "health": health_data,
    }


@app.get("/api/v1/market/{instrument_id}/chart")
def market_chart(
    instrument_id: str,
    limit: int = Query(CHART_DEFAULT_LIMIT, ge=60, le=CHART_MAX_LIMIT),
):
    """K 线走势 + 近半年高点回撤深度。"""
    try:
        with get_session() as session:
            payload = build_market_chart(
                ScoreRepository(session),
                instrument_id,
                limit=limit,
            )
    except ValueError as exc:
        code = str(exc)
        if code == "unknown_instrument":
            raise HTTPException(404, "未知标的") from exc
        if code == "no_ohlcv":
            raise HTTPException(404, "无行情数据，请先执行 crawl") from exc
        raise
    return payload


@app.get("/api/v1/market/{instrument_id}/return-stats")
def market_return_stats(instrument_id: str):
    with get_session() as session:
        ohlcv = load_close_df(session, instrument_id)
    if ohlcv.empty:
        raise HTTPException(404, "无行情，请先 crawl")
    return {"instrument_id": instrument_id, **annualized_return_pct(ohlcv)}


@app.get("/api/v1/market/{instrument_id}/lump-sum")
def market_lump_sum(
    instrument_id: str,
    buy_date: str = Query(..., description="买入日 YYYY-MM-DD"),
    amount: float = Query(..., gt=0, description="买入金额"),
):
    with get_session() as session:
        repo = ScoreRepository(session)
        ohlcv = load_close_df(session, instrument_id)
    if ohlcv.empty:
        raise HTTPException(404, "无净值/行情数据，请先在管理后台爬取该基金")
    try:
        payload = compute_lump_sum_return(ohlcv, buy_date, amount)
        payload["context"] = build_all_in_context(
            repo,
            instrument_id,
            ohlcv,
            payload["buy_date"],
            payload["latest_date"],
        )
    except ValueError as exc:
        code = str(exc)
        if code == "buy_date_after_latest":
            raise HTTPException(400, "买入日不能晚于最新净值日期") from exc
        if code == "invalid_amount":
            raise HTTPException(400, "金额须大于 0") from exc
        raise HTTPException(404, "无净值/行情数据") from exc
    return {"instrument_id": instrument_id, **payload}


@app.get("/api/v1/market/{instrument_id}/lump-sum/meta")
def market_lump_sum_meta(instrument_id: str):
    with get_session() as session:
        ohlcv = load_close_df(session, instrument_id)
    if ohlcv.empty:
        raise HTTPException(404, "无净值/行情数据，请先在管理后台爬取该基金")
    meta = lump_sum_meta(ohlcv)
    return {"instrument_id": instrument_id, **meta}
