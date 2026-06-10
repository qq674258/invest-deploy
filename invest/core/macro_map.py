"""指标 ID → 宏观序列；NDX/SPX 以 instruments.yaml 中 macro_series 为准。"""
from __future__ import annotations

from invest.config_loader import InstrumentProfile

# 日韩德等未单独配置 macro_series 的标的
LEGACY_MACRO_METRIC_SERIES: dict[str, str] = {
    "vix": "macro:vix",
    "vdax": "macro:vdax",
    "us10y": "macro:us10y",
    "us2y": "macro:us2y",
    "dxy": "macro:dxy",
    "usdjpy": "macro:usdjpy",
    "eurusd": "macro:eurusd",
}

DERIVED_METRICS = frozenset({"erp_spread", "yield_curve_2s10s"})


def resolve_macro_series_id(
    profile: InstrumentProfile, metric_id: str
) -> str | None:
    custom = profile.raw.get("macro_series") or {}
    if metric_id in custom:
        return str(custom[metric_id])
    if metric_id == "earnings_yield":
        iid = profile.instrument_id.lower()
        if iid in ("ndx", "spx"):
            return f"macro:{iid}:earnings_yield"
    return LEGACY_MACRO_METRIC_SERIES.get(metric_id)


def macro_series_map_for_metrics(
    profile: InstrumentProfile, metric_ids: list[str]
) -> dict[str, str]:
    out: dict[str, str] = {}
    for mid in metric_ids:
        sid = resolve_macro_series_id(profile, mid)
        if sid:
            out[mid] = sid
    return out


def macro_metric_ids(metric_ids: list[str], series_map: dict[str, str]) -> list[str]:
    return [m for m in metric_ids if m in series_map]
