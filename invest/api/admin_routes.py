from __future__ import annotations

import copy
import json
import queue
import threading
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from invest.config_loader import load_instruments
from invest.core.auth import create_admin_token, require_admin, verify_admin_credentials
from invest.core.crawl_logger import CrawlProgressLogger
from invest.core.crawl_config import (
    config_meta,
    find_url_changes,
    load_crawl_config,
    reset_crawl_config_override,
    save_crawl_config_full,
)
from invest.core.alert_config import (
    effective_smtp_password,
    load_alert_config,
    mask_alert_config_for_api,
    reset_alert_config_override,
    save_alert_config_full,
)
from invest.core.drawdown_alert import run_drawdown_alerts
from invest.core.instrument_registry import (
    get_instrument,
    list_display_instruments,
    load_all_instruments,
)
from invest.core.site_config import (
    load_site_config,
    public_site_payload,
    reset_site_config_override,
    save_site_config_full,
)
from invest.data.crawl_service import CrawlService
from invest.data.repository.admin_repo import AdminRepository
from invest.data.repository.user_repo import UserRepository
from invest.db.session import get_session
from invest.jobs.scheduler import (
    reload_scheduler as _reload_scheduler,
    run_scheduled_crawl,
    scheduler_status,
)
from invest.notifications.email import send_email
from invest.settings import get_ohlcv_lookback_days

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

FundMarket = Literal["QDII", "美股", "港股", "A股", "其他"]
FundSector = Literal["科技", "医疗", "消费", "金融", "新能源", "制造", "均衡", "其他"]
FundNavLookback = Literal["1y", "3y", "5y", "since_inception"]

INDEX_CRAWL_TARGETS = [
    {"instrument_id": "NDX", "display_name": "纳斯达克100", "job": "crawl_ndx"},
    {"instrument_id": "SPX", "display_name": "标普500", "job": "crawl_spx"},
    {"instrument_id": "N225", "display_name": "日经225", "job": "crawl_jp_de"},
    {"instrument_id": "DAX", "display_name": "德国DAX", "job": "crawl_jp_de"},
]


class LoginBody(BaseModel):
    username: str
    password: str


class FundResolveBody(BaseModel):
    fund_code: str = Field(min_length=6, max_length=16)


class FundCreateBody(BaseModel):
    display_name: str = Field(min_length=1, max_length=128)
    fund_code: str = Field(min_length=6, max_length=16)
    market: FundMarket = "A股"
    sector: FundSector = "均衡"
    crawl_enabled: bool = True
    nav_lookback: FundNavLookback = "since_inception"
    enabled: bool = True
    fund_manager: str | None = None
    fund_company: str | None = None
    fund_type: str | None = None
    establish_date: str | None = None
    manager_ids: list[str] = Field(default_factory=list)
    managers_on_fund: list[dict[str, Any]] = Field(default_factory=list)
    default_planned_amount: float = 300


class FundUpdateBody(BaseModel):
    display_name: str | None = None
    market: FundMarket | None = None
    sector: FundSector | None = None
    crawl_enabled: bool | None = None
    nav_lookback: FundNavLookback | None = None
    enabled: bool | None = None
    fund_manager: str | None = None
    fund_company: str | None = None
    fund_type: str | None = None
    establish_date: str | None = None
    manager_ids: list[str] | None = None
    managers_on_fund: list[dict[str, Any]] | None = None


class CrawlBody(BaseModel):
    lookback_days: int | None = None
    nav_lookback: FundNavLookback | None = None
    recent_bars: int | None = Field(None, ge=1, le=500)


class DeleteRowsBody(BaseModel):
    ids: list[int] = Field(min_length=1)


class CrawlConfigUpdateBody(BaseModel):
    config: dict[str, Any]
    confirm_url_changes: bool = False


class AlertConfigUpdateBody(BaseModel):
    config: dict[str, Any]


class AlertTestEmailBody(BaseModel):
    subject: str = "数据监测 · 连通性测试"
    body: str = "这是一封连通性测试邮件，用于确认 SMTP 配置可用。"


class SiteConfigUpdateBody(BaseModel):
    config: dict[str, Any]


class SiteUserCreateBody(BaseModel):
    phone: str
    password: str
    display_name: str | None = None
    enabled: bool = True


class SiteUserUpdateBody(BaseModel):
    phone: str | None = None
    password: str | None = None
    display_name: str | None = None
    enabled: bool | None = None


@router.post("/login")
def admin_login(body: LoginBody, request: Request):
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    with get_session() as session:
        repo = UserRepository(session)
        if not verify_admin_credentials(body.username, body.password):
            repo.create_login_log(
                phone=body.username,
                success=False,
                login_type="admin",
                ip=ip,
                user_agent=user_agent,
                failure_reason="用户名或密码错误",
            )
            raise HTTPException(401, "用户名或密码错误")
        repo.create_login_log(
            phone=body.username,
            success=True,
            login_type="admin",
            ip=ip,
            user_agent=user_agent,
        )
    token = create_admin_token(body.username)
    return {"token": token, "username": body.username}


@router.get("/me")
def admin_me(user: str = Depends(require_admin)):
    return {"username": user}


@router.get("/crawl/config")
def get_crawl_config_admin(_: str = Depends(require_admin)):
    cfg = load_crawl_config()
    return {
        "config": cfg,
        "meta": config_meta(),
        "lookback_days": get_ohlcv_lookback_days(),
    }


@router.put("/crawl/config")
def update_crawl_config(body: CrawlConfigUpdateBody, _: str = Depends(require_admin)):
    current = load_crawl_config()
    url_changes = find_url_changes(current, body.config)
    if url_changes and not body.confirm_url_changes:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "url_change_confirmation_required",
                "message": "修改接口地址需确认后才能保存",
                "changes": url_changes,
            },
        )
    saved = save_crawl_config_full(body.config)
    _reload_scheduler()
    return {
        "status": "ok",
        "url_changes_applied": url_changes,
        "config": saved,
        "lookback_days": get_ohlcv_lookback_days(),
    }


@router.delete("/crawl/config/override")
def reset_crawl_config(_: str = Depends(require_admin)):
    cfg = reset_crawl_config_override()
    return {"status": "ok", "config": cfg}


@router.get("/crawl-targets")
def crawl_targets(_: str = Depends(require_admin)):
    yaml_ids = {p.instrument_id for p in load_instruments()}
    funds = []
    for p in load_all_instruments():
        if p.asset_class == "cn_active_fund" and p.enabled:
            funds.append(
                {
                    "instrument_id": p.instrument_id,
                    "display_name": p.display_name,
                    "fund_code": p.raw.get("fund_code"),
                    "crawl_enabled": p.raw.get("crawl_enabled", True),
                    "nav_lookback": p.raw.get("nav_lookback", "since_inception"),
                    "admin_managed": p.raw.get("admin_managed", False),
                }
            )
    return {
        "indices": INDEX_CRAWL_TARGETS,
        "default_lookback_days": get_ohlcv_lookback_days(),
        "funds": funds,
        "yaml_instruments": list(yaml_ids),
    }


def _crawl_value_error_http(exc: ValueError) -> HTTPException:
    code = str(exc)
    if code == "unknown_instrument":
        return HTTPException(404, "未知标的")
    if code == "crawl_disabled":
        return HTTPException(400, "该基金已关闭自动爬取")
    if code == "not_fund":
        return HTTPException(400, "非基金标的")
    if code == "no_fund_code":
        return HTTPException(400, "缺少基金代码")
    return HTTPException(400, code)


@router.post("/crawl/instrument/{instrument_id}")
def crawl_instrument(
    instrument_id: str,
    body: CrawlBody | None = None,
    _: str = Depends(require_admin),
):
    body = body or CrawlBody()
    log = CrawlProgressLogger()
    try:
        return CrawlService().crawl_instrument_id(
            instrument_id,
            lookback_days=body.lookback_days,
            nav_lookback=body.nav_lookback,
            recent_bars=body.recent_bars,
            progress=log,
        )
    except ValueError as exc:
        raise _crawl_value_error_http(exc) from exc


@router.post("/crawl/instrument/{instrument_id}/stream")
def crawl_instrument_stream(
    instrument_id: str,
    body: CrawlBody | None = None,
    _: str = Depends(require_admin),
):
    """SSE：实时推送采集日志与最终结果。"""
    body = body or CrawlBody()

    def generate():
        event_q: queue.Queue[dict[str, Any]] = queue.Queue()

        def on_event(ev: dict[str, Any]) -> None:
            event_q.put(ev)

        def worker() -> None:
            try:
                progress = CrawlProgressLogger(on_event=on_event)
                result = CrawlService().crawl_instrument_id(
                    instrument_id,
                    lookback_days=body.lookback_days,
                    nav_lookback=body.nav_lookback,
                    recent_bars=body.recent_bars,
                    progress=progress,
                )
                event_q.put({"type": "done", "result": result})
            except ValueError as exc:
                http_exc = _crawl_value_error_http(exc)
                event_q.put(
                    {
                        "type": "error",
                        "code": str(exc),
                        "message": http_exc.detail,
                    }
                )
            except Exception as exc:
                event_q.put({"type": "error", "message": str(exc)})

        threading.Thread(target=worker, daemon=True).start()
        while True:
            item = event_q.get()
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
            if item.get("type") in ("done", "error"):
                break

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/crawl/job/{job_id}")
def crawl_job(
    job_id: str,
    lookback_days: int | None = None,
    _: str = Depends(require_admin),
):
    allowed = ("crawl_ndx", "crawl_spx", "crawl_us", "crawl_jp_de", "all")
    if job_id not in allowed:
        raise HTTPException(400, f"job_id 须为 {' / '.join(allowed)}")
    svc = CrawlService()
    if job_id == "all":
        out = []
        for jid in ("crawl_ndx", "crawl_spx", "crawl_jp_de"):
            out.append(svc.run_job(jid, lookback_days=lookback_days))
        return {"jobs": out}
    return svc.run_job(job_id, lookback_days=lookback_days)


def _instrument_admin_items() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    health = CrawlService().health_summary()
    for p in load_all_instruments():
        data = health.get("instruments", {}).get(p.instrument_id)
        if not data and p.asset_class == "cn_active_fund":
            data = health.get("funds", {}).get(p.instrument_id)
        items.append(
            {
                "instrument_id": p.instrument_id,
                "display_name": p.display_name,
                "asset_class": p.asset_class,
                "enabled": p.enabled,
                "admin_managed": p.raw.get("admin_managed", False),
                "fund_code": p.raw.get("fund_code"),
                "market": p.raw.get("market"),
                "sector": p.raw.get("sector"),
                "crawl_enabled": p.raw.get("crawl_enabled", True),
                "nav_lookback": p.raw.get("nav_lookback"),
                "fund_manager": p.raw.get("fund_manager"),
                "manager_ids": p.raw.get("manager_ids") or [],
                "data": data,
            }
        )
    return items


@router.get("/instruments")
def admin_list_instruments(_: str = Depends(require_admin)):
    return _instrument_admin_items()


def _filter_funds(
    items: list[dict[str, Any]],
    *,
    q: str | None = None,
    code: str | None = None,
    market: str | None = None,
    sector: str | None = None,
) -> list[dict[str, Any]]:
    out = items
    if code and code.strip():
        c = code.strip()
        c_upper = c.upper()
        if c_upper.startswith("FUND_"):
            c = c[5:]
        out = [
            x
            for x in out
            if x.get("fund_code") == c
            or x.get("instrument_id") == f"FUND_{c}"
            or x.get("instrument_id") == c_upper
        ]
    if q and q.strip():
        ql = q.strip().lower()
        out = [
            x
            for x in out
            if ql in (x.get("display_name") or "").lower()
            or ql in (x.get("fund_code") or "").lower()
            or ql in (x.get("instrument_id") or "").lower()
            or ql in (x.get("fund_manager") or "").lower()
            or ql in (x.get("sector") or "").lower()
        ]
    if market and market.strip():
        out = [x for x in out if x.get("market") == market.strip()]
    if sector and sector.strip():
        out = [x for x in out if x.get("sector") == sector.strip()]
    return out


@router.post("/funds/resolve")
def resolve_fund(body: FundResolveBody, _: str = Depends(require_admin)):
    """根据基金代码拉取概况与现任基金经理 ID（录入前预览）。"""
    fund_code = body.fund_code.strip()
    try:
        resolved = CrawlService().eastmoney.resolve_fund(fund_code)
    except Exception as exc:
        raise HTTPException(400, f"解析失败：{exc}") from exc
    return {
        "fund_code": resolved.fund_code,
        "display_name": resolved.display_name,
        "fund_manager": resolved.fund_manager,
        "fund_company": resolved.fund_company,
        "fund_type": resolved.fund_type,
        "establish_date": resolved.establish_date,
        "manager_ids": resolved.manager_ids,
        "managers": [
            {
                "mgr_id": m.mgr_id,
                "name": m.name,
                "start_date": m.start_date,
                "end_date": m.end_date,
                "tenure_days": m.tenure_days,
                "tenure_return_pct": m.tenure_return_pct,
                "is_current": m.is_current,
            }
            for m in resolved.managers
        ],
    }


@router.get("/funds")
def list_funds(
    q: str | None = Query(None, description="名称/经理模糊搜索"),
    code: str | None = Query(None, description="基金代码精确匹配（6位）"),
    market: str | None = Query(None, description="市场筛选"),
    sector: str | None = Query(None, description="板块筛选"),
    _: str = Depends(require_admin),
):
    items = [
        x for x in _instrument_admin_items() if x.get("asset_class") == "cn_active_fund"
    ]
    filtered = _filter_funds(items, q=q, code=code, market=market, sector=sector)
    return {"total": len(filtered), "items": filtered}


@router.get("/funds/{instrument_id}")
def get_fund(instrument_id: str, _: str = Depends(require_admin)):
    profile = get_instrument(instrument_id)
    if not profile or profile.asset_class != "cn_active_fund":
        raise HTTPException(404, "基金不存在")
    health = CrawlService().health_summary()
    data = health.get("funds", {}).get(instrument_id)
    return {
        "instrument_id": instrument_id,
        "display_name": profile.display_name,
        "asset_class": profile.asset_class,
        "enabled": profile.enabled,
        "admin_managed": profile.raw.get("admin_managed", False),
        "fund_code": profile.raw.get("fund_code"),
        "market": profile.raw.get("market"),
        "sector": profile.raw.get("sector"),
        "crawl_enabled": profile.raw.get("crawl_enabled", True),
        "nav_lookback": profile.raw.get("nav_lookback"),
        "fund_manager": profile.raw.get("fund_manager"),
        "fund_company": profile.raw.get("fund_company"),
        "fund_type": profile.raw.get("fund_type"),
        "establish_date": profile.raw.get("establish_date"),
        "manager_ids": profile.raw.get("manager_ids") or [],
        "managers_on_fund": profile.raw.get("managers_on_fund") or [],
        "data": data,
    }


@router.get("/funds/{instrument_id}/managers")
def get_fund_managers(instrument_id: str, _: str = Depends(require_admin)):
    profile = get_instrument(instrument_id)
    if not profile or profile.asset_class != "cn_active_fund":
        raise HTTPException(404, "基金不存在")
    mgr_ids = profile.raw.get("manager_ids") or []
    with get_session() as session:
        profiles = AdminRepository(session).get_manager_profiles(mgr_ids)
    return {
        "instrument_id": instrument_id,
        "manager_ids": mgr_ids,
        "managers_on_fund": profile.raw.get("managers_on_fund") or [],
        "profiles": profiles,
    }


@router.post("/funds")
def create_fund(body: FundCreateBody, _: str = Depends(require_admin)):
    instrument_id = f"FUND_{body.fund_code}"
    with get_session() as session:
        admin = AdminRepository(session)
        if admin.get_instrument_row(instrument_id):
            raise HTTPException(409, f"基金 {instrument_id} 已存在")
        payload = body.model_dump()
        _, cfg = admin.build_fund_config(payload)
        cfg["fund_manager"] = body.fund_manager or cfg.get("fund_manager")
        cfg["fund_company"] = body.fund_company or cfg.get("fund_company")
        admin.upsert_managed_instrument(
            instrument_id,
            body.display_name,
            "cn_active_fund",
            cfg,
            enabled=body.enabled,
        )
    return {"instrument_id": instrument_id, "status": "created"}


@router.patch("/funds/{instrument_id}")
def update_fund(
    instrument_id: str, body: FundUpdateBody, _: str = Depends(require_admin)
):
    profile = get_instrument(instrument_id)
    if not profile or profile.asset_class != "cn_active_fund":
        raise HTTPException(404, "基金不存在")
    cfg = dict(profile.raw)
    if body.display_name is not None:
        cfg["display_name"] = body.display_name
    if body.market is not None:
        cfg["market"] = body.market
    if body.sector is not None:
        cfg["sector"] = body.sector
    if body.crawl_enabled is not None:
        cfg["crawl_enabled"] = body.crawl_enabled
    if body.nav_lookback is not None:
        cfg["nav_lookback"] = body.nav_lookback
    if body.fund_manager is not None:
        cfg["fund_manager"] = body.fund_manager
    if body.fund_company is not None:
        cfg["fund_company"] = body.fund_company
    if body.fund_type is not None:
        cfg["fund_type"] = body.fund_type
    if body.establish_date is not None:
        cfg["establish_date"] = body.establish_date
    if body.manager_ids is not None:
        cfg["manager_ids"] = body.manager_ids
    if body.managers_on_fund is not None:
        cfg["managers_on_fund"] = body.managers_on_fund
    with get_session() as session:
        admin = AdminRepository(session)
        admin.upsert_managed_instrument(
            instrument_id,
            cfg.get("display_name", profile.display_name),
            "cn_active_fund",
            cfg,
            enabled=body.enabled if body.enabled is not None else profile.enabled,
        )
    return {"instrument_id": instrument_id, "status": "updated"}


@router.delete("/funds/{instrument_id}")
def delete_fund(instrument_id: str, _: str = Depends(require_admin)):
    with get_session() as session:
        admin = AdminRepository(session)
        ok = admin.delete_managed_instrument(instrument_id)
    if not ok:
        raise HTTPException(400, "仅可删除管理员录入的基金")
    return {"status": "deleted"}


@router.get("/data/{instrument_id}")
def list_market_data(
    instrument_id: str,
    data_type: Literal["ohlcv", "nav", "auto"] = "auto",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: str = Depends(require_admin),
):
    profile = get_instrument(instrument_id)
    if not profile:
        raise HTTPException(404, "未知标的")
    dtype = data_type
    if dtype == "auto":
        dtype = "nav" if profile.asset_class == "cn_active_fund" else "ohlcv"
    with get_session() as session:
        admin = AdminRepository(session)
        if dtype == "nav":
            rows, total = admin.list_fund_nav(instrument_id, limit, offset)
            return {
                "data_type": "nav",
                "total": total,
                "rows": [
                    {
                        "id": r.id,
                        "date": r.nav_date.isoformat(),
                        "nav": r.nav,
                        "acc_nav": r.acc_nav,
                        "daily_return": r.daily_return,
                        "source": r.source,
                        "status": r.status,
                    }
                    for r in rows
                ],
            }
        rows, total = admin.list_ohlcv(instrument_id, limit, offset)
        return {
            "data_type": "ohlcv",
            "total": total,
            "rows": [
                {
                    "id": r.id,
                    "date": r.trade_date.isoformat(),
                    "open": r.open,
                    "high": r.high,
                    "low": r.low,
                    "close": r.close,
                    "volume": r.volume,
                    "source": r.source,
                    "status": r.status,
                }
                for r in rows
            ],
        }


@router.delete("/data/ohlcv")
def delete_ohlcv_rows(body: DeleteRowsBody, _: str = Depends(require_admin)):
    with get_session() as session:
        n = AdminRepository(session).delete_ohlcv_ids(body.ids)
    return {"deleted": n}


@router.delete("/data/nav")
def delete_nav_rows(body: DeleteRowsBody, _: str = Depends(require_admin)):
    with get_session() as session:
        n = AdminRepository(session).delete_fund_nav_ids(body.ids)
    return {"deleted": n}


@router.post("/data/{instrument_id}/dedupe")
def dedupe_data(instrument_id: str, _: str = Depends(require_admin)):
    profile = get_instrument(instrument_id)
    if not profile:
        raise HTTPException(404, "未知标的")
    with get_session() as session:
        admin = AdminRepository(session)
        if profile.asset_class == "cn_active_fund":
            removed = admin.dedupe_fund_nav(instrument_id)
            dtype = "nav"
        else:
            removed = admin.dedupe_ohlcv(instrument_id)
            dtype = "ohlcv"
    return {"instrument_id": instrument_id, "data_type": dtype, "removed": removed}


@router.get("/audits")
def list_audits(limit: int = Query(30, le=100), _: str = Depends(require_admin)):
    with get_session() as session:
        rows = AdminRepository(session).list_audits(limit)
    return [
        {
            "id": r.id,
            "job_id": r.job_id,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "status": r.status,
            "rows_upserted": r.rows_upserted,
            "errors": json.loads(r.errors_json) if r.errors_json else [],
        }
        for r in rows
    ]


def _prepare_alert_config_save(body: dict[str, Any]) -> dict[str, Any]:
    current = load_alert_config(reload=True)
    merged = copy.deepcopy(body)
    email = merged.get("email")
    if isinstance(email, dict):
        pwd = email.get("smtp_password")
        if pwd in (None, "", "********"):
            old_email = current.get("email") or {}
            kept = str(old_email.get("smtp_password") or "") or effective_smtp_password(current)
            if kept:
                email["smtp_password"] = kept
            else:
                email.pop("smtp_password", None)
    return merged


@router.get("/alerts/config")
def get_alert_config_admin(_: str = Depends(require_admin)):
    cfg = load_alert_config()
    indices = [
        p
        for p in list_display_instruments()
        if p.asset_class.startswith("index_")
    ]
    return {
        "config": mask_alert_config_for_api(cfg),
        "indices": [
            {"instrument_id": p.instrument_id, "display_name": p.display_name}
            for p in indices
        ],
        "scheduler": scheduler_status(),
    }


@router.put("/alerts/config")
def update_alert_config(body: AlertConfigUpdateBody, _: str = Depends(require_admin)):
    saved = save_alert_config_full(_prepare_alert_config_save(body.config))
    _reload_scheduler()
    return {"status": "ok", "config": mask_alert_config_for_api(saved)}


@router.delete("/alerts/config/override")
def reset_alert_config(_: str = Depends(require_admin)):
    cfg = reset_alert_config_override()
    return {"status": "ok", "config": mask_alert_config_for_api(cfg)}


@router.post("/alerts/test-email")
def test_alert_email(body: AlertTestEmailBody, _: str = Depends(require_admin)):
    cfg = load_alert_config()
    try:
        send_email(cfg, subject=body.subject, body=body.body)
    except Exception as exc:
        raise HTTPException(400, f"发送失败：{exc}") from exc
    return {"status": "sent"}


@router.post("/alerts/test-drawdown-email")
def test_drawdown_alert_email(_: str = Depends(require_admin)):
    """发送一封模拟回调告警邮件，用于验证告警模板与投递链路。"""
    cfg = load_alert_config()
    email_cfg = cfg.get("email") or {}
    if not email_cfg.get("enabled"):
        raise HTTPException(400, "请先启用邮件并保存配置")
    sample_body = "\n".join(
        [
            f"市场回调监测 · {date.today().isoformat()}",
            "",
            "【监测链路测试】纳斯达克100（NDX） 相对近 252 交易日高点回调 -10.25%，达到 10% 监测线。",
            "",
            "此为测试邮件，用于确认回调告警投递正常；非实时行情触发。",
            "",
            "仅供参考，数据可能存在延迟。",
        ]
    )
    try:
        send_email(
            cfg,
            subject="纳斯达克100回调10%提示",
            body=sample_body,
        )
    except Exception as exc:
        raise HTTPException(400, f"发送失败：{exc}") from exc
    return {"status": "sent"}


@router.post("/alerts/check-drawdown")
def check_drawdown_alerts(
    dry_run: bool = Query(False),
    _: str = Depends(require_admin),
):
    return run_drawdown_alerts(dry_run=dry_run)


@router.get("/scheduler/status")
def get_scheduler_status(_: str = Depends(require_admin)):
    return scheduler_status()


@router.post("/scheduler/reload")
def reload_scheduler_route(_: str = Depends(require_admin)):
    _reload_scheduler()
    return scheduler_status()


@router.post("/scheduler/run-now")
def run_scheduler_now(_: str = Depends(require_admin)):
    run_scheduled_crawl()
    return {"status": "ok", "scheduler": scheduler_status()}


@router.get("/site/config")
def get_site_config_admin(_: str = Depends(require_admin)):
    cfg = load_site_config()
    return {"config": cfg, "public": public_site_payload(cfg)}


@router.put("/site/config")
def update_site_config(body: SiteConfigUpdateBody, _: str = Depends(require_admin)):
    saved = save_site_config_full(body.config)
    return {"status": "ok", "config": saved, "public": public_site_payload(saved)}


@router.delete("/site/config/override")
def reset_site_config(_: str = Depends(require_admin)):
    cfg = reset_site_config_override()
    return {"status": "ok", "config": cfg, "public": public_site_payload(cfg)}


@router.get("/site-users")
def list_site_users(_: str = Depends(require_admin)):
    with get_session() as session:
        repo = UserRepository(session)
        return {"items": [repo.user_to_dict(u) for u in repo.list_users()]}


@router.post("/site-users")
def create_site_user(body: SiteUserCreateBody, _: str = Depends(require_admin)):
    with get_session() as session:
        repo = UserRepository(session)
        try:
            row = repo.create_user(
                phone=body.phone,
                password=body.password,
                display_name=body.display_name,
                enabled=body.enabled,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return {"status": "ok", "user": repo.user_to_dict(row)}


@router.put("/site-users/{user_id}")
def update_site_user(
    user_id: int,
    body: SiteUserUpdateBody,
    _: str = Depends(require_admin),
):
    with get_session() as session:
        repo = UserRepository(session)
        try:
            row = repo.update_user(
                user_id,
                phone=body.phone,
                password=body.password,
                display_name=body.display_name,
                enabled=body.enabled,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return {"status": "ok", "user": repo.user_to_dict(row)}


@router.delete("/site-users/{user_id}")
def delete_site_user(user_id: int, _: str = Depends(require_admin)):
    with get_session() as session:
        repo = UserRepository(session)
        if not repo.delete_user(user_id):
            raise HTTPException(404, "用户不存在")
        return {"status": "ok"}


@router.get("/login-logs")
def list_login_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: str = Depends(require_admin),
):
    with get_session() as session:
        repo = UserRepository(session)
        items = repo.list_login_logs(limit=limit, offset=offset)
        return {
            "items": [repo.login_log_to_dict(x) for x in items],
            "total": repo.count_login_logs(),
            "limit": limit,
            "offset": offset,
        }


@router.delete("/login-logs/{log_id}")
def delete_login_log(log_id: int, _: str = Depends(require_admin)):
    with get_session() as session:
        repo = UserRepository(session)
        if not repo.delete_login_log(log_id):
            raise HTTPException(404, "日志不存在")
        return {"status": "ok"}
