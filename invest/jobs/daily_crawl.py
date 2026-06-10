"""
每日数据采集 CLI

用法:
  python -m invest.jobs.daily_crawl --job crawl_ndx
  python -m invest.jobs.daily_crawl --job crawl_spx
  python -m invest.jobs.daily_crawl --job crawl_us
  python -m invest.jobs.daily_crawl --job crawl_jp_de
  python -m invest.jobs.daily_crawl --job all
  python -m invest.jobs.daily_crawl --init-db
  python -m invest.jobs.daily_crawl --health
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from invest.data.crawl_service import CrawlService
from invest.db.session import init_db
from invest.settings import get_ohlcv_lookback_days, settings

JOBS = ("crawl_ndx", "crawl_spx", "crawl_jp_de")


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="投资分析系统 — 每日数据采集")
    parser.add_argument(
        "--job",
        choices=[*JOBS, "crawl_us", "all"],
        default="all",
        help="采集任务：crawl_ndx / crawl_spx / crawl_jp_de / all（crawl_us=ndx+spx 兼容）",
    )
    parser.add_argument("--init-db", action="store_true", help="初始化数据库表")
    parser.add_argument("--health", action="store_true", help="查看数据新鲜度")
    parser.add_argument(
        "--years",
        type=float,
        metavar="N",
        help="拉取近 N 年历史（如 5 或 10），覆盖环境变量 OHLCV_LOOKBACK_*",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="增量采集：仅拉取库内最新日期之后的窗口（指数/宏观约 30–90 天，基金约 30–120 天）",
    )
    parser.add_argument(
        "--funds",
        action="store_true",
        help="同时爬取 crawl_enabled 的主动基金",
    )
    args = parser.parse_args(argv)

    setup_logging()

    if args.init_db:
        init_db()
        print("数据库表已创建:", settings.database_url)
        return 0

    init_db()
    service = CrawlService()

    if args.health:
        summary = service.health_summary()
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    lookback_days: int | None = None
    if args.incremental:
        lookback_days = None
        print("增量模式：按库内最新日期计算回溯窗口")
    elif args.years is not None:
        if args.years <= 0:
            print("--years 须大于 0", file=sys.stderr)
            return 1
        lookback_days = int(args.years * 365.25) + 90
    else:
        lookback_days = get_ohlcv_lookback_days()
    if not args.incremental:
        print(f"行情回溯约 {lookback_days} 自然日（≈ {lookback_days / 365.25:.1f} 年）")

    jobs = list(JOBS) if args.job == "all" else [args.job]
    if args.job == "crawl_us":
        jobs = ["crawl_us"]
    exit_code = 0
    for job_id in jobs:
        print(f"\n=== 开始任务: {job_id} ===")
        result = service.run_job(
            job_id, lookback_days=lookback_days, incremental=args.incremental
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result.get("errors"):
            exit_code = 1

    if args.funds:
        print("\n=== 开始任务: crawl_cn_funds ===")
        fund_result = service.crawl_all_funds(incremental=args.incremental)
        print(json.dumps(fund_result, ensure_ascii=False, indent=2))
        if fund_result.get("errors"):
            exit_code = 1

    if exit_code == 0:
        print("\n--- 数据新鲜度 ---")
        print(json.dumps(service.health_summary(), ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
