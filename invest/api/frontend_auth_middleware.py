from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from invest.core.auth import decode_user_token

_PUBLIC_API_PREFIXES = (
    "/api/v1/site/",
    "/api/v1/auth/",
    "/api/v1/health",
    "/api/v1/version",
    "/api/v1/admin/",
    "/api/v1/dashboard",
    "/api/v1/instruments",
    "/api/v1/market/",
    "/api/v1/funds",
)

_PROTECTED_API_PREFIXES = (
    "/api/v1/me/",
)


class FrontendAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api/v1/"):
            return await call_next(request)
        if any(path.startswith(prefix) for prefix in _PUBLIC_API_PREFIXES):
            return await call_next(request)
        if not any(path.startswith(prefix) for prefix in _PROTECTED_API_PREFIXES):
            return await call_next(request)

        auth = request.headers.get("authorization", "")
        if not auth.lower().startswith("bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "需要登录"},
            )
        token = auth[7:].strip()
        try:
            decode_user_token(token)
        except Exception:
            return JSONResponse(
                status_code=401,
                content={"detail": "登录已失效，请重新登录"},
            )
        return await call_next(request)
