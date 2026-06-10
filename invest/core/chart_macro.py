from __future__ import annotations

import math
from typing import Any

import pandas as pd

from invest.core.instrument_registry import InstrumentProfile
from invest.core.macro_map import resolve_macro_series_id
from invest.data.repository.score_repo import ScoreRepository

CHART_OVERLAY_METRICS = ("pe_ttm", "vix")

INFLATION_SERIES: dict[str, tuple[str, str]] = {
    "cpi": ("macro:ndx:cpi", "CPI 同比"),
    "pce": ("macro:ndx:pce", "PCE 同比"),
}

INFLATION_SERIES_SPX: dict[str, tuple[str, str]] = {
    "cpi": ("macro:spx:cpi", "CPI 同比"),
    "pce": ("macro:spx:pce", "PCE 同比"),
}


def _series_to_json(s: pd.Series) -> list[float | None]:
    out: list[float | None] = []
    for v in s:
        if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
            out.append(None)
        else:
            out.append(float(v))
    return out


def _align_macro_to_dates(
    series: pd.Series, dates: pd.DatetimeIndex | pd.Series
) -> pd.Series:
    if isinstance(dates, pd.Series):
        dates = pd.DatetimeIndex(dates)
    if series.empty or len(dates) == 0:
        return pd.Series(index=dates, dtype=float)
    s = series.sort_index()
    aligned = s.reindex(dates, method="ffill")
    if len(s) > 0:
        last_px = dates[-1]
        snap_dt = s.index[-1]
        snap_val = float(s.iloc[-1])
        if snap_dt > last_px and (snap_dt - last_px).days <= 7:
            aligned.iloc[-1] = snap_val
    return aligned


def _latest_point(series: pd.Series) -> dict[str, Any] | None:
    if series.empty:
        return None
    s = series.dropna().sort_index()
    if s.empty:
        return None
    dt = s.index[-1]
    return {
        "value": round(float(s.iloc[-1]), 4),
        "date": pd.Timestamp(dt).strftime("%Y-%m-%d"),
    }


def _yoy_monthly(series: pd.Series) -> dict[str, Any] | None:
    s = series.dropna().sort_index()
    if len(s) < 13:
        return None
    latest_dt = s.index[-1]
    latest_val = float(s.iloc[-1])
    cutoff = latest_dt - pd.DateOffset(months=12)
    prior = s.loc[s.index <= cutoff]
    if prior.empty:
        return None
    base = float(prior.iloc[-1])
    if base <= 0:
        return None
    yoy = (latest_val / base - 1.0) * 100.0
    return {
        "value": round(yoy, 2),
        "date": pd.Timestamp(latest_dt).strftime("%Y-%m-%d"),
        "unit": "%",
        "label": "同比",
    }


def _inflation_map(profile: InstrumentProfile) -> dict[str, tuple[str, str]]:
    iid = profile.instrument_id.upper()
    if iid == "SPX":
        return INFLATION_SERIES_SPX
    if iid == "NDX":
        return INFLATION_SERIES
    return {}


def build_chart_macro(
    repo: ScoreRepository,
    profile: InstrumentProfile,
    dates: pd.DatetimeIndex,
) -> tuple[dict[str, list[float | None]], dict[str, Any]]:
    """叠加序列（PE/VIX）与首页快照（PE/VIX/CPI/PCE）。"""
    overlays: dict[str, list[float | None]] = {}
    snapshot: dict[str, Any] = {}

    overlay_ids: dict[str, str] = {}
    for mid in CHART_OVERLAY_METRICS:
        sid = resolve_macro_series_id(profile, mid)
        if sid:
            overlay_ids[mid] = sid

    inflation = _inflation_map(profile)
    load_ids = list(overlay_ids.values()) + [sid for sid, _ in inflation.values()]
    macro = repo.load_macro_series(list(dict.fromkeys(load_ids))) if load_ids else {}

    for mid, sid in overlay_ids.items():
        if sid not in macro:
            continue
        aligned = _align_macro_to_dates(macro[sid], dates)
        overlays[mid] = _series_to_json(aligned)
        pt = _latest_point(macro[sid])
        if pt:
            snapshot[mid] = pt

    for key, (sid, title) in inflation.items():
        if sid not in macro:
            continue
        yoy = _yoy_monthly(macro[sid])
        if yoy:
            snapshot[key] = {**yoy, "label": title}

    return overlays, snapshot
