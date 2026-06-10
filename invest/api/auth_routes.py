from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from invest.core.auth import create_user_token, require_user
from invest.core.passwords import verify_password
from invest.core.site_config import load_site_config, public_site_payload
from invest.data.repository.user_repo import UserRepository, normalize_phone
from invest.db.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["auth"])


class UserLoginBody(BaseModel):
    phone: str
    password: str


@router.get("/site/config")
def get_public_site_config():
    return public_site_payload()


@router.post("/auth/login")
def user_login(body: UserLoginBody, request: Request):
    cfg = public_site_payload()

    try:
        phone = normalize_phone(body.phone)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    with get_session() as session:
        repo = UserRepository(session)
        user = repo.get_by_phone(phone)
        if not user or not user.enabled:
            repo.create_login_log(
                phone=phone,
                success=False,
                ip=ip,
                user_agent=user_agent,
                failure_reason="账号不存在或已禁用",
            )
            raise HTTPException(401, "手机号或密码错误")
        if not verify_password(body.password, user.password_hash):
            repo.create_login_log(
                phone=phone,
                success=False,
                ip=ip,
                user_agent=user_agent,
                failure_reason="密码错误",
            )
            raise HTTPException(401, "手机号或密码错误")
        repo.create_login_log(
            phone=phone,
            success=True,
            ip=ip,
            user_agent=user_agent,
        )
        token = create_user_token(phone, user_id=user.id)
        return {
            "token": token,
            "phone": phone,
            "user_id": user.id,
            "display_name": user.display_name,
            "site": cfg,
        }


@router.get("/auth/me")
def user_me(phone: str = Depends(require_user)):
    with get_session() as session:
        repo = UserRepository(session)
        user = repo.get_by_phone(phone)
        if not user or not user.enabled:
            raise HTTPException(401, "账号不存在或已禁用")
        return {
            "phone": user.phone,
            "user_id": user.id,
            "display_name": user.display_name,
            "site": public_site_payload(),
        }
