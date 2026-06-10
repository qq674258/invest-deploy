from __future__ import annotations

import copy
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from invest.settings import CONFIG_DIR

logger = logging.getLogger(__name__)

BASE_PATH = CONFIG_DIR / "alert_defaults.yaml"

_DEFAULT_CACHE: dict[str, Any] | None = None


def _load_defaults() -> dict[str, Any]:
    global _DEFAULT_CACHE
    if _DEFAULT_CACHE is not None:
        return _DEFAULT_CACHE
    if not BASE_PATH.exists():
        _DEFAULT_CACHE = {}
        return _DEFAULT_CACHE
    with BASE_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    _DEFAULT_CACHE = data if isinstance(data, dict) else {}
    return _DEFAULT_CACHE


def default_user_alert_config() -> dict[str, Any]:
    return copy.deepcopy(_load_defaults())


def mask_user_alert_config_for_api(cfg: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(cfg)
    email = out.get("email")
    if isinstance(email, dict) and email.get("smtp_password"):
        email["smtp_password"] = "********"
        email["smtp_password_set"] = True
    elif isinstance(email, dict):
        email["smtp_password_set"] = bool(email.get("smtp_password"))
    return out


def effective_user_smtp_password(cfg: dict[str, Any]) -> str:
    email = cfg.get("email") or {}
    return str(email.get("smtp_password") or "")
