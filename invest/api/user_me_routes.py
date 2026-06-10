from __future__ import annotations

import copy
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from invest.api.admin_routes import FundCreateBody, FundResolveBody, FundUpdateBody
from invest.config_loader import InstrumentProfile
from invest.core.auth import require_user, require_user_id
from invest.core.drawdown_alert import run_drawdown_alerts_for_user
from invest.core.fund_catalog import build_fund_list_items, filter_fund_profiles
from invest.core.user_alert_config import (
    effective_user_smtp_password,
    mask_user_alert_config_for_api,
)
from invest.data.providers.eastmoney_fund import EastmoneyFundProvider
from invest.data.repository.fund_repo import FundRepository
from invest.data.repository.user_fund_repo import UserFundRepository
from invest.db.session import get_session
from invest.notifications.email import send_email

router = APIRouter(prefix="/api/v1/me", tags=["me"])


class AlertConfigBody(BaseModel):
    config: dict[str, Any]


class AlertTestEmailBody(BaseModel):
    subject: str = "数据监测 · 连通性测试"
    body: str = "这是一封连通性测试邮件，用于确认 SMTP 配置可用。"


def _profiles_from_user_funds(repo: UserFundRepository, user_id: int) -> list[InstrumentProfile]:
    profiles: list[InstrumentProfile] = []
    for row in repo.list_funds(user_id):
        if not row.enabled:
            continue
        raw = repo.fund_to_profile_dict(row)
        profiles.append(
            InstrumentProfile(
                instrument_id=row.instrument_id,
                display_name=row.display_name,
                asset_class="cn_active_fund",
                enabled=row.enabled,
                calendar_id=str(raw.get("calendar_id") or "CN_SSE_SZSE"),
                ohlcv=None,
                crawl_job=(raw.get("crawl") or {}).get("job"),
                raw=raw,
            )
        )
    return profiles


@router.get("")
def me_profile(phone: str = Depends(require_user), user_id: int = Depends(require_user_id)):
    with get_session() as session:
        repo = UserFundRepository(session)
        cfg = repo.get_alert_config(user_id)
    return {
        "phone": phone,
        "user_id": user_id,
        "alert_config": mask_user_alert_config_for_api(cfg),
    }


@router.get("/funds")
def list_my_funds(
    user_id: int = Depends(require_user_id),
    q: str | None = Query(None),
    code: str | None = Query(None),
    market: str | None = Query(None),
    sector: str | None = Query(None),
):
    with get_session() as session:
        repo = UserFundRepository(session)
        profiles = filter_fund_profiles(
            _profiles_from_user_funds(repo, user_id),
            q=q,
            code=code,
            market=market,
            sector=sector,
        )
        items = build_fund_list_items(profiles, FundRepository(session))
    return {"total": len(items), "items": items}


@router.post("/funds/resolve")
def resolve_my_fund(body: FundResolveBody, _: int = Depends(require_user_id)):
    fund_code = body.fund_code.strip()
    try:
        resolved = EastmoneyFundProvider().resolve_fund(fund_code)
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


@router.post("/funds")
def create_my_fund(body: FundCreateBody, user_id: int = Depends(require_user_id)):
    with get_session() as session:
        repo = UserFundRepository(session)
        try:
            row = repo.create_fund(user_id, body.model_dump())
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    return {"instrument_id": row.instrument_id, "status": "created"}


@router.patch("/funds/{instrument_id}")
def update_my_fund(
    instrument_id: str,
    body: FundUpdateBody,
    user_id: int = Depends(require_user_id),
):
    with get_session() as session:
        repo = UserFundRepository(session)
        try:
            repo.update_fund(
                user_id,
                instrument_id,
                body.model_dump(exclude_unset=True),
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    return {"instrument_id": instrument_id, "status": "updated"}


@router.delete("/funds/{instrument_id}")
def delete_my_fund(instrument_id: str, user_id: int = Depends(require_user_id)):
    with get_session() as session:
        repo = UserFundRepository(session)
        if not repo.delete_fund(user_id, instrument_id):
            raise HTTPException(404, "基金不存在")
    return {"status": "ok"}


@router.get("/alerts/config")
def get_my_alert_config(user_id: int = Depends(require_user_id)):
    with get_session() as session:
        cfg = UserFundRepository(session).get_alert_config(user_id)
    return {"config": mask_user_alert_config_for_api(cfg)}


@router.put("/alerts/config")
def save_my_alert_config(body: AlertConfigBody, user_id: int = Depends(require_user_id)):
    with get_session() as session:
        repo = UserFundRepository(session)
        current = repo.get_alert_config(user_id)
        merged = copy.deepcopy(current)
        for key, val in body.config.items():
            if isinstance(val, dict) and isinstance(merged.get(key), dict):
                next_section = copy.deepcopy(merged[key])
                next_section.update(val)
                merged[key] = next_section
            else:
                merged[key] = copy.deepcopy(val)
        email = merged.get("email") or {}
        if email.get("smtp_password") in ("", "********", None) and current.get("email", {}).get(
            "smtp_password"
        ):
            email["smtp_password"] = current["email"]["smtp_password"]
        saved = repo.save_alert_config(user_id, merged)
    return {"status": "ok", "config": saved}


@router.post("/alerts/test-email")
def test_my_alert_email(body: AlertTestEmailBody, user_id: int = Depends(require_user_id)):
    with get_session() as session:
        cfg = UserFundRepository(session).get_alert_config(user_id)
    email_cfg = cfg.get("email") or {}
    if not email_cfg.get("enabled"):
        raise HTTPException(400, "请先启用邮件并保存配置")
    send_cfg = copy.deepcopy(cfg)
    if not effective_user_smtp_password(send_cfg):
        raise HTTPException(400, "请填写 SMTP 密码")
    try:
        send_email(send_cfg, subject=body.subject, body=body.body)
    except Exception as exc:
        raise HTTPException(400, f"发送失败：{exc}") from exc
    return {"status": "sent"}


@router.post("/alerts/check-drawdown")
def check_my_drawdown_alerts(
    dry_run: bool = Query(False),
    user_id: int = Depends(require_user_id),
):
    return run_drawdown_alerts_for_user(user_id, dry_run=dry_run)
