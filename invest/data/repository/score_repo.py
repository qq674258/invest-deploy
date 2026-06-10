from __future__ import annotations

from datetime import date, datetime

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from invest.db.models import MacroSeries, Ohlcv


class ScoreRepository:
    """行情与宏观序列读取（历史命名保留，避免大范围重命名）。"""

    def __init__(self, session: Session):
        self.session = session

    def load_ohlcv_df(self, instrument_id: str, status: str = "official") -> pd.DataFrame:
        rows = self.session.execute(
            select(Ohlcv)
            .where(Ohlcv.instrument_id == instrument_id, Ohlcv.status == status)
            .order_by(Ohlcv.trade_date)
        ).scalars().all()
        data = [
            {
                "trade_date": r.trade_date,
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
            }
            for r in rows
        ]
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        return df

    def load_macro_series(
        self,
        series_ids: list[str],
        status: str = "official",
        *,
        start_date: date | None = None,
    ) -> dict[str, pd.Series]:
        if not series_ids:
            return {}
        rows = self._fetch_macro_rows(series_ids, status, start_date)
        if not rows and status == "official":
            rows = self._fetch_macro_rows(series_ids, None, start_date)
        out: dict[str, pd.Series] = {}
        by_id: dict[str, list[MacroSeries]] = {sid: [] for sid in series_ids}
        for r in rows:
            if r.series_id in by_id:
                by_id[r.series_id].append(r)
        for sid, sid_rows in by_id.items():
            if not sid_rows:
                continue
            dates: list = []
            values: list[float] = []
            for r in sid_rows:
                if r.value is None:
                    continue
                dates.append(r.trade_date)
                values.append(float(r.value))
            if dates:
                out[sid] = pd.Series(
                    values, index=pd.to_datetime(dates), name=sid
                ).sort_index()
        return out

    def _fetch_macro_rows(
        self,
        series_ids: list[str],
        status: str | None,
        start_date: date | None,
    ) -> list[MacroSeries]:
        stmt = select(MacroSeries).where(MacroSeries.series_id.in_(series_ids))
        if status is not None:
            stmt = stmt.where(MacroSeries.status == status)
        if start_date is not None:
            stmt = stmt.where(MacroSeries.trade_date >= start_date)
        stmt = stmt.order_by(MacroSeries.series_id, MacroSeries.trade_date)
        return list(self.session.execute(stmt).scalars().all())
