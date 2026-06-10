"""清空行情/宏观/基金净值等采集数据，保留标的目录与用户配置。"""
from __future__ import annotations

import argparse
import json
import sys

from sqlalchemy import delete, text

from invest.db.models import (
    CrawlAudit,
    FundHolding,
    FundNav,
    MacroSeries,
    Ohlcv,
    ValuationSeries,
)
from invest.db.session import get_engine, get_session, init_db
from invest.settings import settings

_LEGACY_TABLES = (
    "composite_scores",
    "indicator_values",
    "dca_suggestions",
    "cash_pool_ledger",
)

_PURGE_MODELS = (
    FundNav,
    FundHolding,
    Ohlcv,
    ValuationSeries,
    MacroSeries,
    CrawlAudit,
)


def purge_market_data(*, dry_run: bool = False) -> dict[str, int]:
    counts: dict[str, int] = {}
    with get_session() as session:
        for model in _PURGE_MODELS:
            table = model.__tablename__
            if dry_run:
                row = session.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                ).scalar_one()
                counts[table] = int(row or 0)
                continue
            res = session.execute(delete(model))
            counts[table] = int(res.rowcount or 0)

        for table in _LEGACY_TABLES:
            if dry_run:
                try:
                    row = session.execute(
                        text(f"SELECT COUNT(*) FROM {table}")
                    ).scalar_one()
                    counts[table] = int(row or 0)
                except Exception:
                    counts[table] = 0
                continue
            try:
                res = session.execute(text(f"DELETE FROM {table}"))
                counts[table] = int(res.rowcount or 0)
            except Exception:
                counts[table] = 0

        if dry_run:
            session.rollback()
    return counts


def vacuum_sqlite() -> None:
    """DELETE 后 SQLite 文件不会自动缩小，需 VACUUM。"""
    if not settings.database_url.startswith("sqlite"):
        return
    with get_engine().connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("VACUUM"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="清空采集数据（OHLCV/宏观/基金净值/持仓/采集日志），保留 instruments 与用户配置"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅统计将删除的行数，不实际删除",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="确认执行删除（非 dry-run 时必须）",
    )
    args = parser.parse_args(argv)

    init_db()

    if not args.dry_run and not args.yes:
        print("将清空所有采集数据。请加 --yes 确认，或先用 --dry-run 查看行数。", file=sys.stderr)
        return 1

    counts = purge_market_data(dry_run=args.dry_run)
    label = "将删除" if args.dry_run else "已删除"
    print(f"{label}：")
    print(json.dumps(counts, ensure_ascii=False, indent=2))

    if not args.dry_run:
        print("\n正在 VACUUM，回收磁盘空间…")
        vacuum_sqlite()
        print("VACUUM 完成。")

    if args.dry_run:
        print("\n确认后执行：python -m invest.jobs.purge_market_data --yes")
    else:
        print("\n数据已清空。请重新采集，例如：")
        print("  python -m invest.jobs.daily_crawl --job all --years 1 --funds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
