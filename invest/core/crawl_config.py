from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any

import yaml

from invest.settings import CONFIG_DIR, DATA_DIR, settings

logger = logging.getLogger(__name__)

BASE_PATH = CONFIG_DIR / "crawl_sources.yaml"
OVERRIDE_PATH = DATA_DIR / "crawl_config.override.yaml"

# 管理后台修改这些键下的值时，须 confirm_url_changes=true
URL_CONFIG_PATHS: tuple[str, ...] = ("endpoints",)

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


def invalidate_crawl_config_cache() -> None:
    global _cache
    _cache = None


def load_crawl_config(*, reload: bool = False) -> dict[str, Any]:
    global _cache
    if _cache is not None and not reload:
        return _cache
    base = _load_yaml(BASE_PATH)
    override = _load_yaml(OVERRIDE_PATH)
    _cache = _deep_merge(base, override) if override else base
    return _cache


def save_crawl_config_override(partial: dict[str, Any]) -> dict[str, Any]:
    """将 partial 合并进 override 文件（不修改 config/ 下只读基线）。"""
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
    invalidate_crawl_config_cache()
    logger.info("已写入采集配置覆盖: %s", OVERRIDE_PATH)
    return load_crawl_config(reload=True)


def save_crawl_config_full(config: dict[str, Any]) -> dict[str, Any]:
    """管理后台保存：写入完整配置到 data/crawl_config.override.yaml。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with OVERRIDE_PATH.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            config,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )
    invalidate_crawl_config_cache()
    logger.info("已保存完整采集配置: %s", OVERRIDE_PATH)
    return load_crawl_config(reload=True)


def reset_crawl_config_override() -> dict[str, Any]:
    if OVERRIDE_PATH.exists():
        OVERRIDE_PATH.unlink()
    invalidate_crawl_config_cache()
    return load_crawl_config(reload=True)


def get_endpoint(key: str, **fmt: str) -> str:
    cfg = load_crawl_config()
    endpoints = cfg.get("endpoints") or {}
    template = str(endpoints.get(key, ""))
    if fmt:
        return template.format(**fmt)
    return template


def get_defaults() -> dict[str, Any]:
    return dict(load_crawl_config().get("defaults") or {})


def get_multpl_slugs() -> dict[str, str]:
    return dict(load_crawl_config().get("multpl_slugs") or {})


def get_provider_cfg() -> dict[str, Any]:
    return dict(load_crawl_config().get("providers") or {})


def extract_url_fields(cfg: dict[str, Any]) -> dict[str, str]:
    """扁平化 endpoints 供比对。"""
    out: dict[str, str] = {}
    endpoints = cfg.get("endpoints") or {}
    for k, v in endpoints.items():
        if isinstance(v, str):
            out[f"endpoints.{k}"] = v
    return out


def find_url_changes(
    old_cfg: dict[str, Any], new_cfg: dict[str, Any]
) -> list[dict[str, str]]:
    old_urls = extract_url_fields(old_cfg)
    new_urls = extract_url_fields(new_cfg)
    changes: list[dict[str, str]] = []
    for key in sorted(set(old_urls) | set(new_urls)):
        if old_urls.get(key) != new_urls.get(key):
            changes.append(
                {
                    "field": key,
                    "from": old_urls.get(key, ""),
                    "to": new_urls.get(key, ""),
                }
            )
    return changes


def get_ohlcv_lookback_from_config(override_days: int | None = None) -> int:
    if override_days is not None and override_days > 0:
        return override_days
    if settings.ohlcv_lookback_days and settings.ohlcv_lookback_days > 0:
        return settings.ohlcv_lookback_days
    d = get_defaults()
    years = float(d.get("lookback_years", settings.ohlcv_lookback_years))
    extra = int(d.get("lookback_days_extra", 90))
    return int(years * 365.25) + extra


def get_job_macro_items(job_id: str) -> list[dict[str, Any]]:
    jobs = load_crawl_config().get("jobs") or {}
    items = jobs.get(job_id) or []
    return list(items) if isinstance(items, list) else []


def config_meta() -> dict[str, Any]:
    return {
        "base_path": str(BASE_PATH),
        "override_path": str(OVERRIDE_PATH),
        "override_exists": OVERRIDE_PATH.exists(),
        "url_fields": list(extract_url_fields(load_crawl_config()).keys()),
    }
