from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from invest.settings import CONFIG_DIR


@dataclass
class OhlcvSource:
    provider: str
    symbol: str


@dataclass
class InstrumentProfile:
    instrument_id: str
    display_name: str
    asset_class: str
    enabled: bool
    calendar_id: str
    ohlcv: OhlcvSource | None = None
    crawl_job: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def load_instruments(path: Path | None = None) -> list[InstrumentProfile]:
    path = path or CONFIG_DIR / "instruments.yaml"
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    profiles: list[InstrumentProfile] = []
    for item in data.get("instruments", []):
        ohlcv_cfg = item.get("ohlcv")
        ohlcv = None
        if ohlcv_cfg:
            ohlcv = OhlcvSource(
                provider=ohlcv_cfg.get("provider", "yfinance"),
                symbol=ohlcv_cfg["symbol"],
            )
        crawl = item.get("crawl") or {}
        profiles.append(
            InstrumentProfile(
                instrument_id=item["instrument_id"],
                display_name=item["display_name"],
                asset_class=item["asset_class"],
                enabled=item.get("enabled", True),
                calendar_id=item.get("calendar_id", "US_NYSE"),
                ohlcv=ohlcv,
                crawl_job=crawl.get("job"),
                raw=item,
            )
        )
    return profiles


def instruments_for_job(job: str) -> list[InstrumentProfile]:
    return [
        p
        for p in load_instruments()
        if p.enabled and p.ohlcv and p.crawl_job == job
    ]


def load_yaml(name: str) -> dict:
    path = CONFIG_DIR / name
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_asset_class_templates() -> dict[str, dict]:
    data = load_yaml("instruments.yaml")
    return data.get("asset_class_templates", {})


def load_scoring_defaults() -> dict:
    data = load_yaml("instruments.yaml")
    scoring = dict(data.get("defaults", {}).get("scoring", {"lookback_years": 5}))
    try:
        from invest.core.crawl_config import get_defaults

        years = get_defaults().get("scoring_lookback_years")
        if years is not None:
            scoring["lookback_years"] = int(years)
    except Exception:
        pass
    return scoring


def get_metrics_map(profile: InstrumentProfile) -> dict[str, list[str]]:
    return profile.raw.get("metrics", {})


def get_weight_profile_name(profile: InstrumentProfile) -> str:
    if profile.raw.get("scoring_weight_profile"):
        return profile.raw["scoring_weight_profile"]
    templates = load_asset_class_templates()
    tpl = templates.get(profile.asset_class, {})
    return tpl.get("dimension_weights_profile", "nasdaq")


def flatten_metric_ids(metrics_map: dict[str, list[str]]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for ids in metrics_map.values():
        for mid in ids:
            if mid not in seen:
                seen.add(mid)
                out.append(mid)
    return out


def is_composite_scoring_enabled(profile: InstrumentProfile) -> bool:
    """国内基金等不参与综合 S，与指数评分完全隔离。"""
    if profile.asset_class == "cn_active_fund":
        return False
    scoring = profile.raw.get("scoring") or {}
    if scoring.get("enabled") is False:
        return False
    return bool(profile.ohlcv)


def instruments_for_scoring(asset_classes: list[str] | None = None) -> list[InstrumentProfile]:
    classes = set(asset_classes or ["index_us", "index_jp", "index_de"])
    return [
        p
        for p in load_instruments()
        if p.enabled
        and is_composite_scoring_enabled(p)
        and p.asset_class in classes
    ]
