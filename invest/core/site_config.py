from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any

import yaml

from invest.settings import CONFIG_DIR, DATA_DIR

logger = logging.getLogger(__name__)

BASE_PATH = CONFIG_DIR / "site_defaults.yaml"
OVERRIDE_PATH = DATA_DIR / "site_config.override.yaml"

_cache: dict[str, Any] | None = None


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, val in override.items():
        if key in out and isinstance(out[key], dict) and isinstance(val, dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = copy.deepcopy(val)
    return out


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def invalidate_site_config_cache() -> None:
    global _cache
    _cache = None


def load_site_config(*, reload: bool = False) -> dict[str, Any]:
    global _cache
    if _cache is not None and not reload:
        return _cache
    base = _load_yaml(BASE_PATH)
    override = _load_yaml(OVERRIDE_PATH)
    _cache = _deep_merge(base, override) if override else base
    return _cache


def save_site_config_override(partial: dict[str, Any]) -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    current = _load_yaml(OVERRIDE_PATH)
    merged = _deep_merge(current, partial)
    with OVERRIDE_PATH.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            merged,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )
    invalidate_site_config_cache()
    logger.info("已写入站点配置: %s", OVERRIDE_PATH)
    return load_site_config(reload=True)


def save_site_config_full(config: dict[str, Any]) -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with OVERRIDE_PATH.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            config,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )
    invalidate_site_config_cache()
    return load_site_config(reload=True)


def reset_site_config_override() -> dict[str, Any]:
    if OVERRIDE_PATH.exists():
        OVERRIDE_PATH.unlink()
    invalidate_site_config_cache()
    return load_site_config(reload=True)


def public_site_payload(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    data = cfg or load_site_config()
    site = data.get("site") or {}
    return {
        "title": str(site.get("title") or "投资回撤提醒-定投计算器工具"),
        "frontend_login_enabled": bool(site.get("frontend_login_enabled")),
    }


def is_frontend_login_enabled() -> bool:
    return bool(public_site_payload().get("frontend_login_enabled"))
