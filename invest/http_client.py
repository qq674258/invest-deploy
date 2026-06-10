from __future__ import annotations

import os
from typing import Optional

import httpx

from invest.settings import settings


def get_http_proxy() -> Optional[str]:
    """仅使用 .env / 环境变量中的代理，避免误用未启动的 127.0.0.1:10808。"""
    if getattr(settings, "http_proxy", None):
        return settings.http_proxy or None
    for key in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        val = os.environ.get(key)
        if val:
            return val
    return None


def make_httpx_client(**kwargs) -> httpx.Client:
    proxy = get_http_proxy()
    if proxy:
        kwargs.setdefault("proxy", proxy)
    kwargs.setdefault("timeout", 60.0)
    kwargs.setdefault("follow_redirects", True)
    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", settings.crawl_user_agent)
    kwargs["headers"] = headers
    return httpx.Client(**kwargs)
