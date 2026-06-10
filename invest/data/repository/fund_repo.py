from __future__ import annotations

import json
from datetime import date
from typing import Any

import pandas as pd
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from invest.db.models import FundHolding, FundNav


class FundRepository:
    def __init__(self, session: Session):
        self.session = session

    def load_nav_df(self, instrument_id: str) -> pd.DataFrame:
        rows = (
            self.session.execute(
                select(FundNav)
                .where(FundNav.instrument_id == instrument_id)
                .order_by(FundNav.nav_date.asc())
            )
            .scalars()
            .all()
        )
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(
            [
                {
                    "nav_date": r.nav_date,
                    "nav": r.nav,
                    "acc_nav": r.acc_nav,
                    "daily_return": r.daily_return,
                }
                for r in rows
            ]
        )

    def latest_nav(self, instrument_id: str) -> FundNav | None:
        return (
            self.session.execute(
                select(FundNav)
                .where(FundNav.instrument_id == instrument_id)
                .order_by(FundNav.nav_date.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )

    def get_last_nav_date(self, instrument_id: str) -> date | None:
        row = self.latest_nav(instrument_id)
        return row.nav_date if row else None

    def list_nav(
        self,
        instrument_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        total = self.session.execute(
            select(func.count(FundNav.id)).where(
                FundNav.instrument_id == instrument_id
            )
        ).scalar_one()
        rows = (
            self.session.execute(
                select(FundNav)
                .where(FundNav.instrument_id == instrument_id)
                .order_by(FundNav.nav_date.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        items = [
            {
                "nav_date": r.nav_date.isoformat(),
                "nav": r.nav,
                "acc_nav": r.acc_nav,
                "daily_return": r.daily_return,
            }
            for r in rows
        ]
        return items, int(total or 0)

    def list_holdings(
        self, instrument_id: str, report_date: date | None = None
    ) -> tuple[list[dict[str, Any]], str | None]:
        q = select(FundHolding).where(FundHolding.instrument_id == instrument_id)
        if report_date:
            q = q.where(FundHolding.report_date == report_date)
        else:
            latest = self.session.execute(
                select(func.max(FundHolding.report_date)).where(
                    FundHolding.instrument_id == instrument_id
                )
            ).scalar_one()
            if not latest:
                return [], None
            q = q.where(FundHolding.report_date == latest)
            report_date = latest
        rows = (
            self.session.execute(q.order_by(FundHolding.weight_pct.desc()))
            .scalars()
            .all()
        )
        items = [
            {
                "symbol": r.symbol or None,
                "name": r.name,
                "weight_pct": r.weight_pct,
                "change_pct": r.change_pct,
                "industry": r.industry,
            }
            for r in rows
        ]
        rd = report_date.isoformat() if report_date else None
        return items, rd

    def upsert_holdings(
        self,
        instrument_id: str,
        fund_code: str,
        report_date: date,
        holdings: list[dict[str, Any]],
        source: str = "eastmoney",
    ) -> int:
        self.session.execute(
            delete(FundHolding).where(
                FundHolding.instrument_id == instrument_id,
                FundHolding.report_date == report_date,
            )
        )
        n = 0
        for h in holdings:
            self.session.add(
                FundHolding(
                    instrument_id=instrument_id,
                    fund_code=fund_code,
                    report_date=report_date,
                    symbol=str(h.get("symbol") or ""),
                    name=str(h.get("name") or ""),
                    weight_pct=h.get("weight_pct"),
                    change_pct=h.get("change_pct"),
                    industry=h.get("industry"),
                    source=source,
                )
            )
            n += 1
        return n
