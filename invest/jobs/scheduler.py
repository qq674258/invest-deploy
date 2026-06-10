from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from invest.core.alert_config import load_alert_config
from invest.core.crawl_config import get_defaults
from invest.core.drawdown_alert import run_all_user_drawdown_alerts, run_drawdown_alerts
from invest.data.crawl_service import CrawlService
from invest.settings import get_ohlcv_lookback_days

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _parse_hhmm(value: str) -> tuple[int, int]:
    parts = str(value or "07:30").strip().split(":")
    hour = int(parts[0]) if parts else 7
    minute = int(parts[1]) if len(parts) > 1 else 30
    return hour, minute


def run_scheduled_crawl() -> None:
    defaults = get_defaults()
    if not defaults.get("auto_crawl_enabled"):
        logger.debug("自动采集未启用，跳过")
        return

    incremental = bool(defaults.get("auto_crawl_incremental", True))
    include_funds = bool(defaults.get("auto_crawl_include_funds", True))
    run_alerts = bool(defaults.get("auto_crawl_run_alerts", True))
    lookback = None if incremental else get_ohlcv_lookback_days()

    logger.info(
        "开始定时采集 incremental=%s funds=%s",
        incremental,
        include_funds,
    )
    svc = CrawlService()
    try:
        for job_id in ("crawl_ndx", "crawl_spx", "crawl_jp_de"):
            result = svc.run_job(job_id, lookback_days=lookback, incremental=incremental)
            logger.info("定时任务 %s: %s", job_id, result.get("status"))
        if include_funds:
            fund_result = svc.crawl_all_funds(incremental=incremental)
            logger.info("定时基金采集: %s", fund_result.get("status"))
    except Exception:
        logger.exception("定时采集失败")

    if run_alerts:
        try:
            alert_result = run_drawdown_alerts()
            logger.info("全站回撤告警检查: %s", alert_result.get("status"))
            user_alert_result = run_all_user_drawdown_alerts()
            logger.info(
                "用户回撤告警检查: %s 个用户",
                user_alert_result.get("users"),
            )
        except Exception:
            logger.exception("回撤告警失败")


def setup_scheduler() -> BackgroundScheduler | None:
    global _scheduler
    defaults = get_defaults()
    if not defaults.get("auto_crawl_enabled"):
        logger.warning(
            "auto_crawl_enabled=false，未启动内置定时器。"
            "请在管理后台「告警与定时」启用，或编辑 data/crawl_config.override.yaml"
        )
        return None

    tz = str(defaults.get("auto_crawl_timezone") or "Asia/Shanghai")
    hour, minute = _parse_hhmm(str(defaults.get("auto_crawl_time") or "07:30"))

    _scheduler = BackgroundScheduler(timezone=tz)
    _scheduler.add_job(
        run_scheduled_crawl,
        CronTrigger(hour=hour, minute=minute, timezone=tz),
        id="daily_crawl",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("已启动每日定时采集 %02d:%02d (%s)", hour, minute, tz)
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("定时采集调度器已停止")


def reload_scheduler() -> BackgroundScheduler | None:
    shutdown_scheduler()
    return setup_scheduler()


def scheduler_status() -> dict:
    defaults = get_defaults()
    alert_cfg = load_alert_config()
    jobs = []
    if _scheduler:
        for job in _scheduler.get_jobs():
            nxt = job.next_run_time
            jobs.append(
                {
                    "id": job.id,
                    "next_run": nxt.isoformat() if nxt else None,
                }
            )
    return {
        "running": _scheduler is not None and _scheduler.running,
        "auto_crawl_enabled": bool(defaults.get("auto_crawl_enabled")),
        "auto_crawl_time": defaults.get("auto_crawl_time"),
        "auto_crawl_timezone": defaults.get("auto_crawl_timezone"),
        "auto_crawl_incremental": defaults.get("auto_crawl_incremental"),
        "auto_crawl_include_funds": defaults.get("auto_crawl_include_funds"),
        "auto_crawl_run_alerts": defaults.get("auto_crawl_run_alerts"),
        "drawdown_alert_enabled": bool((alert_cfg.get("drawdown") or {}).get("enabled")),
        "email_enabled": bool((alert_cfg.get("email") or {}).get("enabled")),
        "jobs": jobs,
        "server_time": datetime.now().isoformat(),
    }
