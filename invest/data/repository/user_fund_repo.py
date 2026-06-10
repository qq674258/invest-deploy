from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from invest.core.user_alert_config import default_user_alert_config, mask_user_alert_config_for_api
from invest.data.repository.admin_repo import AdminRepository
from invest.db.models import UserAlertConfig, UserAlertState, UserFund


def build_user_fund_config(body: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    fund_code = str(body["fund_code"]).strip()
    instrument_id = body.get("instrument_id") or f"FUND_{fund_code}"
    cfg: dict[str, Any] = {
        "instrument_id": instrument_id,
        "display_name": body["display_name"],
        "asset_class": "cn_active_fund",
        "enabled": body.get("enabled", True),
        "fund_code": fund_code,
        "market": body.get("market", "A股"),
        "sector": body.get("sector", "均衡"),
        "user_managed": True,
        "admin_managed": False,
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


class UserFundRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_funds(self, user_id: int) -> list[UserFund]:
        return list(
            self.session.execute(
                select(UserFund)
                .where(UserFund.user_id == user_id)
                .order_by(UserFund.id.desc())
            )
            .scalars()
            .all()
        )

    def list_all_enabled_distinct(self) -> list[UserFund]:
        """全部用户已启用基金，按 instrument_id 去重。"""
        rows = list(
            self.session.execute(
                select(UserFund)
                .where(UserFund.enabled.is_(True))
                .order_by(UserFund.id.desc())
            )
            .scalars()
            .all()
        )
        seen: dict[str, UserFund] = {}
        for row in rows:
            if row.instrument_id not in seen:
                seen[row.instrument_id] = row
        return list(seen.values())

    def find_any_enabled(self, instrument_id: str) -> UserFund | None:
        return self.session.execute(
            select(UserFund)
            .where(
                UserFund.instrument_id == instrument_id,
                UserFund.enabled.is_(True),
            )
            .limit(1)
        ).scalar_one_or_none()

    def get_fund(self, user_id: int, instrument_id: str) -> UserFund | None:
        return self.session.execute(
            select(UserFund).where(
                UserFund.user_id == user_id,
                UserFund.instrument_id == instrument_id,
            )
        ).scalar_one_or_none()

    def owns_fund(self, user_id: int, instrument_id: str) -> bool:
        return self.get_fund(user_id, instrument_id) is not None

    def create_fund(self, user_id: int, body: dict[str, Any]) -> UserFund:
        instrument_id, cfg = build_user_fund_config(body)
        existing = self.get_fund(user_id, instrument_id)
        if existing:
            raise ValueError("该基金已在您的列表中")
        admin = AdminRepository(self.session)
        admin.upsert_catalog_instrument(
            instrument_id,
            str(body["display_name"]),
            "cn_active_fund",
            cfg,
            enabled=bool(body.get("enabled", True)),
        )
        row = UserFund(
            user_id=user_id,
            instrument_id=instrument_id,
            fund_code=str(body["fund_code"]).strip(),
            display_name=str(body["display_name"]),
            market=str(body.get("market", "A股")),
            sector=str(body.get("sector", "均衡")),
            enabled=bool(body.get("enabled", True)),
            crawl_enabled=bool(body.get("crawl_enabled", True)),
            nav_lookback=str(body.get("nav_lookback", "since_inception")),
            config_json=json.dumps(cfg, ensure_ascii=False),
        )
        self.session.add(row)
        self.session.flush()
        return row

    def update_fund(
        self, user_id: int, instrument_id: str, body: dict[str, Any]
    ) -> UserFund:
        row = self.get_fund(user_id, instrument_id)
        if not row:
            raise ValueError("基金不存在")
        cfg = json.loads(row.config_json) if row.config_json else {}
        if body.get("display_name") is not None:
            row.display_name = str(body["display_name"])
            cfg["display_name"] = row.display_name
        for key in ("market", "sector", "nav_lookback", "fund_manager", "fund_company"):
            if body.get(key) is not None:
                setattr(row, key, body[key])
                cfg[key] = body[key]
        if body.get("enabled") is not None:
            row.enabled = bool(body["enabled"])
            cfg["enabled"] = row.enabled
        if body.get("crawl_enabled") is not None:
            row.crawl_enabled = bool(body["crawl_enabled"])
            cfg["crawl_enabled"] = row.crawl_enabled
        row.updated_at = datetime.utcnow()
        row.config_json = json.dumps(cfg, ensure_ascii=False)
        AdminRepository(self.session).upsert_catalog_instrument(
            instrument_id,
            row.display_name,
            "cn_active_fund",
            cfg,
            enabled=row.enabled,
        )
        return row

    def delete_fund(self, user_id: int, instrument_id: str) -> bool:
        row = self.get_fund(user_id, instrument_id)
        if not row:
            return False
        self.session.delete(row)
        return True

    def fund_to_profile_dict(self, row: UserFund) -> dict[str, Any]:
        cfg: dict[str, Any] = {}
        if row.config_json:
            try:
                cfg = json.loads(row.config_json)
            except json.JSONDecodeError:
                cfg = {}
        cfg.update(
            {
                "instrument_id": row.instrument_id,
                "display_name": row.display_name,
                "fund_code": row.fund_code,
                "market": row.market,
                "sector": row.sector,
                "enabled": row.enabled,
                "crawl_enabled": row.crawl_enabled,
                "nav_lookback": row.nav_lookback,
            }
        )
        return cfg

    def list_crawl_enabled_fund_codes(self) -> list[tuple[int, str, str]]:
        rows = list(
            self.session.execute(
                select(UserFund).where(
                    UserFund.enabled.is_(True),
                    UserFund.crawl_enabled.is_(True),
                )
            )
            .scalars()
            .all()
        )
        return [(r.user_id, r.instrument_id, r.fund_code) for r in rows]

    def get_alert_config(self, user_id: int) -> dict[str, Any]:
        row = self.session.get(UserAlertConfig, user_id)
        if not row:
            return default_user_alert_config()
        try:
            data = json.loads(row.config_json)
            return data if isinstance(data, dict) else default_user_alert_config()
        except json.JSONDecodeError:
            return default_user_alert_config()

    def save_alert_config(self, user_id: int, config: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps(config, ensure_ascii=False)
        row = self.session.get(UserAlertConfig, user_id)
        if row:
            row.config_json = payload
            row.updated_at = datetime.utcnow()
        else:
            self.session.add(
                UserAlertConfig(
                    user_id=user_id,
                    config_json=payload,
                )
            )
        self.session.flush()
        return mask_user_alert_config_for_api(config)

    def list_users_with_alerts_enabled(self) -> list[int]:
        rows = self.session.execute(select(UserAlertConfig)).scalars().all()
        out: list[int] = []
        for row in rows:
            try:
                cfg = json.loads(row.config_json)
            except json.JSONDecodeError:
                continue
            email_on = bool((cfg.get("email") or {}).get("enabled"))
            dd_on = bool((cfg.get("drawdown") or {}).get("enabled"))
            if email_on and dd_on:
                out.append(int(row.user_id))
        return out

    def load_alert_state(self, user_id: int) -> dict[str, Any]:
        rows = list(
            self.session.execute(
                select(UserAlertState).where(UserAlertState.user_id == user_id)
            )
            .scalars()
            .all()
        )
        state: dict[str, Any] = {}
        for row in rows:
            notified: list[int] = []
            if row.notified_json:
                try:
                    notified = [int(x) for x in json.loads(row.notified_json)]
                except (json.JSONDecodeError, TypeError, ValueError):
                    notified = []
            state[row.instrument_id] = {
                "notified": notified,
                "last_dd_pct": row.last_dd_pct,
                "last_check": row.last_check.isoformat() if row.last_check else None,
            }
        return state

    def save_alert_state(self, user_id: int, state: dict[str, Any]) -> None:
        for iid, inst_state in state.items():
            row = self.session.execute(
                select(UserAlertState).where(
                    UserAlertState.user_id == user_id,
                    UserAlertState.instrument_id == iid,
                )
            ).scalar_one_or_none()
            notified_json = json.dumps(inst_state.get("notified") or [])
            last_check_raw = inst_state.get("last_check")
            last_check = None
            if isinstance(last_check_raw, str) and last_check_raw:
                try:
                    last_check = datetime.fromisoformat(last_check_raw)
                except ValueError:
                    last_check = datetime.utcnow()
            if row:
                row.notified_json = notified_json
                row.last_dd_pct = inst_state.get("last_dd_pct")
                row.last_check = last_check or datetime.utcnow()
            else:
                self.session.add(
                    UserAlertState(
                        user_id=user_id,
                        instrument_id=iid,
                        notified_json=notified_json,
                        last_dd_pct=inst_state.get("last_dd_pct"),
                        last_check=last_check or datetime.utcnow(),
                    )
                )

    def delete_alert_state_for_user(self, user_id: int) -> None:
        self.session.execute(
            delete(UserAlertState).where(UserAlertState.user_id == user_id)
        )
