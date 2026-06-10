from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from invest.db.base import Base
from invest.settings import DATA_DIR, settings

_engine = None
_SessionLocal = None


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        connect_args = {}
        if settings.database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        _engine = create_engine(settings.database_url, connect_args=connect_args)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


_LEGACY_TABLES = (
    "composite_scores",
    "indicator_values",
    "dca_suggestions",
    "cash_pool_ledger",
)

# 已从配置移除的示例标的，启动时清理残留净值/持仓
_PURGED_INSTRUMENT_IDS = ("FUND_110011",)


def _purge_removed_instruments(conn) -> None:
    for iid in _PURGED_INSTRUMENT_IDS:
        conn.execute(
            text("DELETE FROM fund_nav WHERE instrument_id = :iid"), {"iid": iid}
        )
        conn.execute(
            text("DELETE FROM fund_holdings WHERE instrument_id = :iid"), {"iid": iid}
        )
        conn.execute(
            text("DELETE FROM instruments WHERE instrument_id = :iid"), {"iid": iid}
        )


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    if settings.database_url.startswith("sqlite"):
        with engine.begin() as conn:
            for name in _LEGACY_TABLES:
                conn.execute(text(f"DROP TABLE IF EXISTS {name}"))
            _purge_removed_instruments(conn)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    if _SessionLocal is None:
        get_engine()
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
