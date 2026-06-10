from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from invest.core.alert_config import load_alert_config
from invest.core.drawdown import rolling_drawdown_from_high
from invest.core.instrument_registry import get_instrument
from invest.core.price_series import load_close_df
from invest.db.session import get_session
from invest.core.user_alert_config import effective_user_smtp_password
from invest.data.repository.user_fund_repo import UserFundRepository
from invest.notifications.email import send_email
from invest.settings import DATA_DIR

logger = logging.getLogger(__name__)

STATE_PATH = DATA_DIR / "alert_state.json"


def _load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    try:
        with STATE_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(state: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with STATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _current_drawdown_pct(close: pd.Series, lookback_days: int) -> float | None:
    if close.empty:
        return None
    dd = rolling_drawdown_from_high(close, lookback_days)
    last = dd.dropna()
    if last.empty:
        return None
    return round(float(last.iloc[-1]) * 100.0, 2)


def run_drawdown_alerts(*, dry_run: bool = False) -> dict[str, Any]:
    """检查回撤阈值并发送邮件；返回执行摘要（全站管理员配置）。"""
    cfg = load_alert_config()
    dd_cfg = cfg.get("drawdown") or {}
    email_cfg = cfg.get("email") or {}
    if not dd_cfg.get("enabled"):
        return {"status": "skipped", "reason": "drawdown_disabled"}
    if not email_cfg.get("enabled") and not dry_run:
        return {"status": "skipped", "reason": "email_disabled"}

    state = _load_state()
    result = _evaluate_drawdown_alerts(
        cfg,
        state=state,
        dry_run=dry_run,
    )
    _save_state(state)
    return result


def run_drawdown_alerts_for_user(user_id: int, *, dry_run: bool = False) -> dict[str, Any]:
    with get_session() as session:
        repo = UserFundRepository(session)
        cfg = repo.get_alert_config(user_id)
        dd_cfg = cfg.get("drawdown") or {}
        email_cfg = cfg.get("email") or {}
        if not dd_cfg.get("enabled"):
            return {"status": "skipped", "reason": "drawdown_disabled", "user_id": user_id}
        if not email_cfg.get("enabled") and not dry_run:
            return {"status": "skipped", "reason": "email_disabled", "user_id": user_id}
        if not effective_user_smtp_password(cfg) and not dry_run:
            return {"status": "skipped", "reason": "smtp_missing", "user_id": user_id}
        state = repo.load_alert_state(user_id)
        result = _evaluate_drawdown_alerts(cfg, state=state, dry_run=dry_run)
        repo.save_alert_state(user_id, state)
        result["user_id"] = user_id
        return result


def run_all_user_drawdown_alerts(*, dry_run: bool = False) -> dict[str, Any]:
    with get_session() as session:
        user_ids = UserFundRepository(session).list_users_with_alerts_enabled()
    summaries = []
    for uid in user_ids:
        try:
            summaries.append(run_drawdown_alerts_for_user(uid, dry_run=dry_run))
        except Exception:
            logger.exception("用户 %s 回撤告警失败", uid)
            summaries.append({"user_id": uid, "status": "error"})
    return {"users": len(user_ids), "results": summaries}


def _evaluate_drawdown_alerts(
    cfg: dict[str, Any],
    *,
    state: dict[str, Any],
    dry_run: bool,
) -> dict[str, Any]:
    dd_cfg = cfg.get("drawdown") or {}
    instrument_ids = list(dd_cfg.get("instrument_ids") or [])
    lookback_days = int(dd_cfg.get("lookback_days") or 252)
    thresholds = sorted(
        int(x) for x in (dd_cfg.get("thresholds_pct") or [5, 10, 15]) if int(x) > 0
    )
    recover_above = float(dd_cfg.get("recover_above_pct") or 4)

    alerts: list[dict[str, Any]] = []
    checked: list[dict[str, Any]] = []

    with get_session() as session:
        for iid in instrument_ids:
            profile = get_instrument(iid)
            if not profile:
                continue
            ohlcv = load_close_df(session, iid)
            if ohlcv.empty:
                checked.append({"instrument_id": iid, "error": "no_data"})
                continue
            close = ohlcv.sort_values("trade_date")["close"].astype(float)
            close.index = pd.to_datetime(close.index)
            dd_pct = _current_drawdown_pct(close, lookback_days)
            if dd_pct is None:
                checked.append({"instrument_id": iid, "error": "no_drawdown"})
                continue

            inst_state = state.setdefault(iid, {"notified": [], "last_dd_pct": None})
            notified: list[int] = [int(x) for x in inst_state.get("notified") or []]

            if dd_pct > -recover_above:
                if notified:
                    inst_state["notified"] = []
                    notified = []
                    logger.info("%s 回撤恢复至 %.2f%%，重置告警状态", iid, dd_pct)

            inst_state["last_dd_pct"] = dd_pct
            inst_state["last_check"] = datetime.utcnow().isoformat()
            checked.append(
                {
                    "instrument_id": iid,
                    "display_name": profile.display_name,
                    "drawdown_pct": dd_pct,
                    "notified": list(notified),
                }
            )

            abs_dd = abs(dd_pct)
            for thr in thresholds:
                if abs_dd >= thr and thr not in notified:
                    line = (
                        f"{profile.display_name}（{iid}）"
                        f" 相对近 {lookback_days} 交易日高点回调 {dd_pct:.2f}%，"
                        f"达到 {thr}% 监测线。"
                    )
                    alerts.append(
                        {
                            "instrument_id": iid,
                            "threshold_pct": thr,
                            "drawdown_pct": dd_pct,
                            "message": line,
                        }
                    )
                    notified.append(thr)
            inst_state["notified"] = notified

    sent = 0
    errors: list[str] = []
    if alerts and not dry_run:
        body_lines = [
            f"市场回调监测 · {date.today().isoformat()}",
            "",
            *[a["message"] for a in alerts],
            "",
            "仅供参考，数据可能存在延迟。",
        ]
        top = max(alerts, key=lambda a: a["threshold_pct"])
        top_profile = get_instrument(top["instrument_id"])
        top_name = (
            top_profile.display_name if top_profile else top["instrument_id"]
        )
        if len(alerts) == 1:
            subject = f"{top_name}回调{top['threshold_pct']}%提示"
        else:
            subject = (
                f"{top_name}回调{top['threshold_pct']}%提示"
                f"等{len(alerts)}条"
            )
        try:
            send_email(
                cfg,
                subject=subject,
                body="\n".join(body_lines),
            )
            sent = 1
        except Exception as exc:
            logger.exception("发送回撤邮件失败")
            errors.append(str(exc))

    status = "success" if not errors else "partial"
    if not alerts:
        status = "no_alert"
    return {
        "status": status,
        "checked": checked,
        "alerts": alerts,
        "emails_sent": sent,
        "errors": errors,
        "dry_run": dry_run,
    }
