from __future__ import annotations

import json
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from invest.config_loader import load_instruments
from invest.data.providers.base import MacroPoint, OhlcvBar
from invest.data.validators.market_data import should_write
from invest.db.models import CrawlAudit, Instrument, MacroSeries, Ohlcv


class MarketRepository:
    def __init__(self, session: Session):
        self.session = session

    def sync_instruments_from_config(self) -> int:
        """仅同步 YAML 中的标的，不覆盖/删除管理员在 DB 中录入的基金。"""
        count = 0
        for p in load_instruments():
            existing = self.session.get(Instrument, p.instrument_id)
            config_json = json.dumps(p.raw, ensure_ascii=False)
            if existing:
                if existing.config_json:
                    try:
                        cfg = json.loads(existing.config_json)
                        if cfg.get("admin_managed"):
                            count += 1
                            continue
                    except json.JSONDecodeError:
                        pass
                existing.display_name = p.display_name
                existing.asset_class = p.asset_class
                existing.enabled = p.enabled
                existing.config_json = config_json
                existing.updated_at = datetime.utcnow()
            else:
                self.session.add(
                    Instrument(
                        instrument_id=p.instrument_id,
                        display_name=p.display_name,
                        asset_class=p.asset_class,
                        enabled=p.enabled,
                        config_json=config_json,
                    )
                )
            count += 1
        return count

    def get_ohlcv_status(
        self, instrument_id: str, trade_date: date
    ) -> str | None:
        row = self.session.execute(
            select(Ohlcv.status).where(
                Ohlcv.instrument_id == instrument_id,
                Ohlcv.trade_date == trade_date,
            )
        ).scalar_one_or_none()
        return row

    def get_prev_close(
        self, instrument_id: str, before_date: date
    ) -> float | None:
        row = self.session.execute(
            select(Ohlcv.close)
            .where(
                Ohlcv.instrument_id == instrument_id,
                Ohlcv.trade_date < before_date,
            )
            .order_by(Ohlcv.trade_date.desc())
            .limit(1)
        ).scalar_one_or_none()
        return row

    def get_last_trade_date(self, instrument_id: str) -> date | None:
        return self.session.execute(
            select(Ohlcv.trade_date)
            .where(Ohlcv.instrument_id == instrument_id)
            .order_by(Ohlcv.trade_date.desc())
            .limit(1)
        ).scalar_one_or_none()

    def upsert_ohlcv(
        self,
        instrument_id: str,
        bars: list[OhlcvBar],
        source: str = "yfinance",
        status: str = "official",
    ) -> tuple[int, list[str]]:
        upserted = 0
        errors: list[str] = []
        for bar in bars:
            existing_status = self.get_ohlcv_status(instrument_id, bar.trade_date)
            if not should_write(status, existing_status):
                continue
            row = self.session.execute(
                select(Ohlcv).where(
                    Ohlcv.instrument_id == instrument_id,
                    Ohlcv.trade_date == bar.trade_date,
                )
            ).scalar_one_or_none()
            if row:
                row.open = bar.open
                row.high = bar.high
                row.low = bar.low
                row.close = bar.close
                row.volume = bar.volume
                row.source = source
                row.status = status
                row.fetched_at = datetime.utcnow()
            else:
                self.session.add(
                    Ohlcv(
                        instrument_id=instrument_id,
                        trade_date=bar.trade_date,
                        open=bar.open,
                        high=bar.high,
                        low=bar.low,
                        close=bar.close,
                        volume=bar.volume,
                        source=source,
                        status=status,
                    )
                )
            upserted += 1
        return upserted, errors

    @staticmethod
    def _dedupe_macro_points(points: list[MacroPoint]) -> list[MacroPoint]:
        """同一 trade_date 保留最后一条（避免同批次重复 INSERT 触发 UNIQUE）。"""
        by_date: dict[date, MacroPoint] = {}
        for pt in points:
            by_date[pt.trade_date] = pt
        return [by_date[d] for d in sorted(by_date)]

    def prune_macro_month(
        self,
        series_id: str,
        year: int,
        month: int,
        *,
        keep_dates: set[date] | None = None,
    ) -> int:
        """删除指定自然月内、不在 keep_dates 中的宏观点（避免 pe_ttm 旧月度残留）。"""
        from sqlalchemy import delete

        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1)
        else:
            month_end = date(year, month + 1, 1)
        stmt = delete(MacroSeries).where(
            MacroSeries.series_id == series_id,
            MacroSeries.trade_date >= month_start,
            MacroSeries.trade_date < month_end,
        )
        if keep_dates:
            stmt = stmt.where(MacroSeries.trade_date.notin_(list(keep_dates)))
        res = self.session.execute(stmt)
        return int(res.rowcount or 0)

    def upsert_macro(
        self,
        series_id: str,
        points: list[MacroPoint],
        source: str = "fred",
        status: str = "official",
    ) -> int:
        points = self._dedupe_macro_points(points)
        upserted = 0
        for pt in points:
            existing = self.session.execute(
                select(MacroSeries.status).where(
                    MacroSeries.series_id == series_id,
                    MacroSeries.trade_date == pt.trade_date,
                )
            ).scalar_one_or_none()
            if not should_write(status, existing):
                continue
            row = self.session.execute(
                select(MacroSeries).where(
                    MacroSeries.series_id == series_id,
                    MacroSeries.trade_date == pt.trade_date,
                )
            ).scalar_one_or_none()
            if row:
                row.value = pt.value
                row.source = source
                row.status = status
                row.fetched_at = datetime.utcnow()
            else:
                self.session.add(
                    MacroSeries(
                        series_id=series_id,
                        trade_date=pt.trade_date,
                        value=pt.value,
                        source=source,
                        status=status,
                    )
                )
            upserted += 1
        return upserted

    def start_audit(self, job_id: str) -> CrawlAudit:
        audit = CrawlAudit(job_id=job_id, started_at=datetime.utcnow(), status="running")
        self.session.add(audit)
        self.session.flush()
        return audit

    def finish_audit(
        self,
        audit: CrawlAudit,
        status: str,
        rows: int,
        errors: list[str],
    ) -> None:
        audit.finished_at = datetime.utcnow()
        audit.status = status
        audit.rows_upserted = rows
        audit.errors_json = json.dumps(errors, ensure_ascii=False) if errors else None
