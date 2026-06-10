"""
数据采集流水线

  python -m invest.jobs.pipeline --all
  python -m invest.jobs.pipeline --crawl-only
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from invest.data.crawl_service import CrawlService
from invest.db.session import init_db
from invest.jobs.daily_crawl import JOBS

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="行情采集流水线")
    parser.add_argument("--all", action="store_true", help="crawl all")
    parser.add_argument("--crawl-only", action="store_true")
    args = parser.parse_args(argv)
    if not (args.all or args.crawl_only):
        args.all = True

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    init_db()
    exit_code = 0
    summary: dict = {}

    if args.all or args.crawl_only:
        crawl = CrawlService()
        crawl_results = []
        for job in JOBS:
            crawl_results.append(crawl.run_job(job))
        summary["crawl"] = crawl_results
        if any(r.get("errors") for r in crawl_results):
            exit_code = 1

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
