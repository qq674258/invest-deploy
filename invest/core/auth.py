from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from invest.settings import settings

_bearer = HTTPBearer(auto_error=False)
_TOKEN_TTL_SEC = 24 * 3600


def _secret() -> bytes:
    key = settings.admin_secret or settings.admin_password or "change-me"
    return key.encode("utf-8")


def verify_admin_credentials(username: str, password: str) -> bool:
    user_ok = secrets.compare_digest(username, settings.admin_username)
    pass_ok = secrets.compare_digest(password, settings.admin_password)
    return user_ok and pass_ok


def create_admin_token(username: str) -> str:
    payload = {
        "sub": username,
        "typ": "admin",
        "exp": int(time.time()) + _TOKEN_TTL_SEC,
        "iat": int(time.time()),
    }
    body = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).decode()
    sig = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def create_user_token(phone: str, *, user_id: int) -> str:
    payload = {
        "sub": phone,
        "uid": int(user_id),
        "typ": "user",
        "exp": int(time.time()) + _TOKEN_TTL_SEC,
        "iat": int(time.time()),
    }
    body = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).decode()
    sig = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def decode_token(token: str) -> dict[str, Any]:
    try:
        body, sig = token.rsplit(".", 1)
        expected = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
        if not secrets.compare_digest(sig, expected):
            raise ValueError("bad signature")
        payload = json.loads(base64.urlsafe_b64decode(body + "=="))
        if int(payload.get("exp", 0)) < time.time():
            raise ValueError("expired")
        return payload
    except Exception as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="登录已失效，请重新登录"
        ) from exc


def decode_admin_token(token: str) -> dict[str, Any]:
    payload = decode_token(token)
    if payload.get("typ") not in (None, "admin"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="需要管理员登录")
    return payload


def decode_user_token(token: str) -> dict[str, Any]:
    payload = decode_token(token)
    if payload.get("typ") != "user":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="需要前台登录")
    return payload


def require_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="需要登录")
    payload = decode_user_token(creds.credentials)
    return str(payload.get("sub", ""))


def require_user_id(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> int:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="需要登录")
    payload = decode_user_token(creds.credentials)
    uid = payload.get("uid")
    if uid is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="需要重新登录")
    return int(uid)

def require_admin(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="需要管理员登录")
    payload = decode_admin_token(creds.credentials)
    return str(payload.get("sub", ""))

