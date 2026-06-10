from __future__ import annotations

import pandas as pd


def apply_derived_metrics(
    metrics: pd.DataFrame, metric_ids: list[str]
) -> pd.DataFrame:
    """在合并宏观/价格序列后计算派生指标（ERP、利差等）。"""
    out = metrics.copy()

    if "erp_spread" in metric_ids:
        if "_earnings_yield" in out.columns and "us10y" in out.columns:
            # multpl 盈利收益率多为百分比，如 4.5 表示 4.5%
            out["erp_spread"] = out["_earnings_yield"] - out["us10y"]
            out = out.drop(columns=["_earnings_yield"], errors="ignore")
        elif "pe_ttm" in out.columns and "us10y" in out.columns:
            pe = out["pe_ttm"].replace(0, pd.NA)
            out["erp_spread"] = (100.0 / pe) - out["us10y"]

    if "yield_curve_2s10s" in metric_ids and "yield_curve_2s10s" not in out.columns:
        if "us2y" in out.columns and "us10y" in out.columns:
            out["yield_curve_2s10s"] = out["us10y"] - out["us2y"]

    return out
