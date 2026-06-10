from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any

import yaml

from invest.settings import CONFIG_DIR, DATA_DIR, settings

logger = logging.getLogger(__name__)

BASE_PATH = CONFIG_DIR / "alert_defaults.yaml"
OVERRIDE_PATH = DATA_DIR / "alert_config.override.yaml"

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


def invalidate_alert_config_cache() -> None:
    global _cache
    _cache = None


def load_alert_config(*, reload: bool = False) -> dict[str, Any]:
    global _cache
    if _cache is not None and not reload:
        return _cache
    base = _load_yaml(BASE_PATH)
    override = _load_yaml(OVERRIDE_PATH)
    _cache = _deep_merge(base, override) if override else base
    return _cache


def save_alert_config_override(partial: dict[str, Any]) -> dict[str, Any]:
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
    invalidate_alert_config_cache()
    logger.info("已写入告警配置: %s", OVERRIDE_PATH)
    return load_alert_config(reload=True)


def save_alert_config_full(config: dict[str, Any]) -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with OVERRIDE_PATH.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            config,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )
    invalidate_alert_config_cache()
    return load_alert_config(reload=True)


def reset_alert_config_override() -> dict[str, Any]:
    if OVERRIDE_PATH.exists():
        OVERRIDE_PATH.unlink()
    invalidate_alert_config_cache()
    return load_alert_config(reload=True)


def effective_smtp_password(cfg: dict[str, Any]) -> str:
    email = cfg.get("email") or {}
    return str(email.get("smtp_password") or settings.smtp_password or "")


def mask_alert_config_for_api(cfg: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(cfg)
    email = out.get("email")
    if isinstance(email, dict) and email.get("smtp_password"):
        email["smtp_password"] = "********"
        email["smtp_password_set"] = True
    elif isinstance(email, dict):
        email["smtp_password_set"] = bool(effective_smtp_password(cfg))
    return out
