from __future__ import annotations

import pandas as pd
from sqlalchemy.orm import Session

from invest.core.instrument_registry import get_instrument
from invest.data.repository.fund_repo import FundRepository
from invest.data.repository.score_repo import ScoreRepository


def _nav_df_to_close_df(nav_df: pd.DataFrame) -> pd.DataFrame:
    if nav_df.empty:
        return pd.DataFrame()
    df = nav_df.copy()
    df["trade_date"] = pd.to_datetime(df["nav_date"])
    df["close"] = pd.to_numeric(df["nav"], errors="coerce")
    df = df.dropna(subset=["close"])
    df = df[df["close"] > 0]
    if df.empty:
        return pd.DataFrame()
    return df[["trade_date", "close"]].sort_values("trade_date").reset_index(drop=True)


def load_close_df(session: Session, instrument_id: str) -> pd.DataFrame:
    """指数/ETF 用 OHLCV 收盘价；国内基金用单位净值序列。"""
    profile = get_instrument(instrument_id)
    if profile and profile.asset_class == "cn_active_fund":
        return _nav_df_to_close_df(FundRepository(session).load_nav_df(instrument_id))

    ohlcv = ScoreRepository(session).load_ohlcv_df(instrument_id)
    if ohlcv.empty:
        return pd.DataFrame()
    out = ohlcv[["trade_date", "close"]].copy()
    out["trade_date"] = pd.to_datetime(out["trade_date"])
    out["close"] = pd.to_numeric(out["close"], errors="coerce")
    return out.dropna(subset=["close"]).sort_values("trade_date").reset_index(drop=True)
