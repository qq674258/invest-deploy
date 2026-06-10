from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from invest.data.providers.fund_nav import FundManagerProfile, FundNavBar
from invest.db.models import (
    CrawlAudit,
    FundManagerProfileRow,
    FundNav,
    Instrument,
    Ohlcv,
)


class AdminRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_instruments(self) -> list[Instrument]:
        return list(
            self.session.execute(select(Instrument).order_by(Instrument.instrument_id))
            .scalars()
            .all()
        )

    def get_instrument_row(self, instrument_id: str) -> Instrument | None:
        return self.session.get(Instrument, instrument_id)

    def upsert_managed_instrument(
        self,
        instrument_id: str,
        display_name: str,
        asset_class: str,
        config: dict[str, Any],
        enabled: bool = True,
    ) -> Instrument:
        config["instrument_id"] = instrument_id
        config["display_name"] = display_name
        config["asset_class"] = asset_class
        config["enabled"] = enabled
        config["admin_managed"] = True
        payload = json.dumps(config, ensure_ascii=False)
        row = self.session.get(Instrument, instrument_id)
        if row:
            row.display_name = display_name
            row.asset_class = asset_class
            row.enabled = enabled
            row.config_json = payload
            row.updated_at = datetime.utcnow()
        else:
            row = Instrument(
                instrument_id=instrument_id,
                display_name=display_name,
                asset_class=asset_class,
                enabled=enabled,
                config_json=payload,
            )
            self.session.add(row)
        return row

    def upsert_catalog_instrument(
        self,
        instrument_id: str,
        display_name: str,
        asset_class: str,
        config: dict[str, Any],
        enabled: bool = True,
    ) -> Instrument:
        config["instrument_id"] = instrument_id
        config["display_name"] = display_name
        config["asset_class"] = asset_class
        config["enabled"] = enabled
        payload = json.dumps(config, ensure_ascii=False)
        row = self.session.get(Instrument, instrument_id)
        if row:
            row.display_name = display_name
            row.asset_class = asset_class
            row.enabled = enabled
            row.config_json = payload
            row.updated_at = datetime.utcnow()
        else:
            row = Instrument(
                instrument_id=instrument_id,
                display_name=display_name,
                asset_class=asset_class,
                enabled=enabled,
                config_json=payload,
            )
            self.session.add(row)
        return row

    def set_enabled(self, instrument_id: str, enabled: bool) -> bool:
        row = self.session.get(Instrument, instrument_id)
        if not row:
            return False
        row.enabled = enabled
        row.updated_at = datetime.utcnow()
        if row.config_json:
            try:
                cfg = json.loads(row.config_json)
                cfg["enabled"] = enabled
                row.config_json = json.dumps(cfg, ensure_ascii=False)
            except json.JSONDecodeError:
                pass
        return True

    def delete_managed_instrument(self, instrument_id: str) -> bool:
        row = self.session.get(Instrument, instrument_id)
        if not row or not row.config_json:
            return False
        try:
            cfg = json.loads(row.config_json)
        except json.JSONDecodeError:
            return False
        if not cfg.get("admin_managed"):
            return False
        self.session.delete(row)
        return True

    def upsert_fund_nav(
        self,
        instrument_id: str,
        fund_code: str,
        bars: list[FundNavBar],
        source: str = "eastmoney",
        status: str = "official",
    ) -> int:
        n = 0
        for bar in bars:
            row = self.session.execute(
                select(FundNav).where(
                    FundNav.fund_code == fund_code,
                    FundNav.nav_date == bar.nav_date,
                )
            ).scalar_one_or_none()
            if row:
                row.nav = bar.nav
                row.acc_nav = bar.acc_nav
                row.daily_return = bar.daily_return
                row.source = source
                row.status = status
                row.fetched_at = datetime.utcnow()
            else:
                self.session.add(
                    FundNav(
                        fund_code=fund_code,
                        instrument_id=instrument_id,
                        nav_date=bar.nav_date,
                        nav=bar.nav,
                        acc_nav=bar.acc_nav,
                        daily_return=bar.daily_return,
                        source=source,
                        status=status,
                    )
                )
            n += 1
        return n

    def upsert_manager_profile(self, profile: FundManagerProfile) -> None:
        codes_json = json.dumps(profile.managed_fund_codes, ensure_ascii=False)
        names_json = json.dumps(profile.managed_fund_names, ensure_ascii=False)
        detail_json = (
            json.dumps(profile.detail, ensure_ascii=False) if profile.detail else None
        )
        fetched = profile.fetched_at or datetime.utcnow()
        row = self.session.get(FundManagerProfileRow, profile.mgr_id)
        if row:
            row.name = profile.name
            row.company = profile.company
            row.resume = profile.resume
            row.photo_url = profile.photo_url
            row.experience_years = profile.experience_years
            row.managed_fund_codes_json = codes_json
            row.managed_fund_names_json = names_json
            row.detail_json = detail_json
            row.fetched_at = fetched
        else:
            self.session.add(
                FundManagerProfileRow(
                    mgr_id=profile.mgr_id,
                    name=profile.name,
                    company=profile.company,
                    resume=profile.resume,
                    photo_url=profile.photo_url,
                    experience_years=profile.experience_years,
                    managed_fund_codes_json=codes_json,
                    managed_fund_names_json=names_json,
                    detail_json=detail_json,
                    fetched_at=fetched,
                )
            )

    def get_manager_profiles(self, mgr_ids: list[str]) -> list[dict[str, Any]]:
        if not mgr_ids:
            return []
        out: list[dict[str, Any]] = []
        for mid in mgr_ids:
            row = self.session.get(FundManagerProfileRow, mid)
            if not row:
                continue
            codes: list[str] = []
            names: list[str] = []
            try:
                if row.managed_fund_codes_json:
                    codes = json.loads(row.managed_fund_codes_json)
                if row.managed_fund_names_json:
                    names = json.loads(row.managed_fund_names_json)
            except json.JSONDecodeError:
                pass
            out.append(
                {
                    "mgr_id": row.mgr_id,
                    "name": row.name,
                    "company": row.company,
                    "resume": row.resume,
                    "photo_url": row.photo_url,
                    "experience_years": row.experience_years,
                    "managed_fund_codes": codes,
                    "managed_fund_names": names,
                    "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
                }
            )
        return out

    def list_ohlcv(
        self,
        instrument_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Ohlcv], int]:
        total = self.session.execute(
            select(func.count(Ohlcv.id)).where(Ohlcv.instrument_id == instrument_id)
        ).scalar_one()
        rows = (
            self.session.execute(
                select(Ohlcv)
                .where(Ohlcv.instrument_id == instrument_id)
                .order_by(Ohlcv.trade_date.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return list(rows), int(total or 0)

    def list_fund_nav(
        self,
        instrument_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[FundNav], int]:
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
        return list(rows), int(total or 0)

    def delete_ohlcv_ids(self, ids: list[int]) -> int:
        if not ids:
            return 0
        res = self.session.execute(delete(Ohlcv).where(Ohlcv.id.in_(ids)))
        return res.rowcount or 0

    def delete_fund_nav_ids(self, ids: list[int]) -> int:
        if not ids:
            return 0
        res = self.session.execute(delete(FundNav).where(FundNav.id.in_(ids)))
        return res.rowcount or 0

    def dedupe_ohlcv(self, instrument_id: str) -> int:
        rows = (
            self.session.execute(
                select(Ohlcv)
                .where(Ohlcv.instrument_id == instrument_id)
                .order_by(Ohlcv.trade_date, Ohlcv.fetched_at.desc())
            )
            .scalars()
            .all()
        )
        seen: set[date] = set()
        remove_ids: list[int] = []
        for row in rows:
            if row.trade_date in seen:
                remove_ids.append(row.id)
            else:
                seen.add(row.trade_date)
        return self.delete_ohlcv_ids(remove_ids)

    def dedupe_fund_nav(self, instrument_id: str) -> int:
        rows = (
            self.session.execute(
                select(FundNav)
                .where(FundNav.instrument_id == instrument_id)
                .order_by(FundNav.nav_date, FundNav.fetched_at.desc())
            )
            .scalars()
            .all()
        )
        seen: set[date] = set()
        remove_ids: list[int] = []
        for row in rows:
            if row.nav_date in seen:
                remove_ids.append(row.id)
            else:
                seen.add(row.nav_date)
        return self.delete_fund_nav_ids(remove_ids)

    def list_audits(self, limit: int = 30) -> list[CrawlAudit]:
        return list(
            self.session.execute(
                select(CrawlAudit).order_by(CrawlAudit.started_at.desc()).limit(limit)
            )
            .scalars()
            .all()
        )

    @staticmethod
    def build_fund_config(body: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        fund_code = str(body["fund_code"]).strip()
        instrument_id = body.get("instrument_id") or f"FUND_{fund_code}"
        market = body.get("market", "A股")
        sector = body.get("sector", "均衡")
        cfg: dict[str, Any] = {
            "instrument_id": instrument_id,
            "display_name": body["display_name"],
            "asset_class": "cn_active_fund",
            "enabled": body.get("enabled", True),
            "fund_code": fund_code,
            "market": market,
            "sector": sector,
            "admin_managed": True,
            "crawl_enabled": body.get("crawl_enabled", True),
            "nav_lookback": body.get("nav_lookback", "since_inception"),
            "fund_manager": body.get("fund_manager"),
            "fund_company": body.get("fund_company"),
            "fund_type": body.get("fund_type"),
            "establish_date": body.get("establish_date"),
            "manager_ids": body.get("manager_ids") or [],
            "managers_on_fund": body.get("managers_on_fund") or [],
            "calendar_id": "CN_SSE_SZSE",
            "nav": {"provider": "eastmoney", "symbol": fund_code},
            "metrics": body.get("metrics")
            or {
                "trend": ["nav_ma60", "nav_ma120"],
                "momentum": ["ret_3m", "ret_6m"],
                "vol": ["realized_vol_20d", "drawdown_52w"],
            },
            "crawl": {"job": "crawl_cn_fund"},
            "dca": {
                "enabled": True,
                "default_planned_amount": body.get("default_planned_amount", 300),
                "default_frequency": "BIWEEKLY",
                "default_multiplier_max": 1.5,
            },
        }
        return instrument_id, cfg
