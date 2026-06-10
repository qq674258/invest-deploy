from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

CACHE_MAX_AGE_SEC = 60
CACHE_CONTROL = f"public, max-age={CACHE_MAX_AGE_SEC}, stale-while-revalidate={CACHE_MAX_AGE_SEC}"

_CACHEABLE_PREFIXES = (
    "/api/v1/instruments",
    "/api/v1/dashboard",
    "/api/v1/site/",
    "/api/v1/market/",
    "/api/v1/funds",
)


def is_cacheable_api_get(path: str, query: str) -> bool:
    if not path.startswith("/api/v1/"):
        return False
    if path.startswith(("/api/v1/admin/", "/api/v1/me/", "/api/v1/auth/")):
        return False
    if path in ("/api/v1/health", "/api/v1/version"):
        return False
    if "/lump-sum" in path and not path.endswith("/meta"):
        return False
    if "refresh=true" in query:
        return False
    return any(path.startswith(prefix) for prefix in _CACHEABLE_PREFIXES)


class ApiCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.method != "GET" or response.status_code != 200:
            return response
        if is_cacheable_api_get(request.url.path, request.url.query):
            response.headers["Cache-Control"] = CACHE_CONTROL
        return response
