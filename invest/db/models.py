from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from invest.db.base import Base


class Instrument(Base):
    __tablename__ = "instruments"

    instrument_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(32), nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True)
    config_json: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Ohlcv(Base):
    __tablename__ = "ohlcv"
    __table_args__ = (
        UniqueConstraint("instrument_id", "trade_date", name="uq_ohlcv_instrument_date"),
        Index("ix_ohlcv_instrument_date", "instrument_id", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instrument_id: Mapped[str] = mapped_column(String(32), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(32), default="yfinance")
    status: Mapped[str] = mapped_column(String(16), default="official")
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MacroSeries(Base):
    __tablename__ = "macro_series"
    __table_args__ = (
        UniqueConstraint("series_id", "trade_date", name="uq_macro_series_date"),
        Index("ix_macro_series_id_date", "series_id", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_id: Mapped[str] = mapped_column(String(64), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="fred")
    status: Mapped[str] = mapped_column(String(16), default="official")
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ValuationSeries(Base):
    __tablename__ = "valuation_series"
    __table_args__ = (
        UniqueConstraint("instrument_id", "trade_date", name="uq_valuation_instrument_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instrument_id: Mapped[str] = mapped_column(String(32), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    pe_ttm: Mapped[Optional[float]] = mapped_column(Float)
    pb: Mapped[Optional[float]] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="official")
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FundManagerProfileRow(Base):
    """东方财富基金经理档案缓存（按 mgr_id 去重）。"""

    __tablename__ = "fund_manager_profiles"

    mgr_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(128))
    company: Mapped[Optional[str]] = mapped_column(String(128))
    resume: Mapped[Optional[str]] = mapped_column(Text)
    photo_url: Mapped[Optional[str]] = mapped_column(String(512))
    experience_years: Mapped[Optional[str]] = mapped_column(String(64))
    managed_fund_codes_json: Mapped[Optional[str]] = mapped_column(Text)
    managed_fund_names_json: Mapped[Optional[str]] = mapped_column(Text)
    detail_json: Mapped[Optional[str]] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FundHolding(Base):
    __tablename__ = "fund_holdings"
    __table_args__ = (
        UniqueConstraint(
            "instrument_id",
            "report_date",
            "symbol",
            name="uq_fund_holding",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instrument_id: Mapped[str] = mapped_column(String(32), nullable=False)
    fund_code: Mapped[str] = mapped_column(String(16), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), default="")
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    weight_pct: Mapped[Optional[float]] = mapped_column(Float)
    change_pct: Mapped[Optional[float]] = mapped_column(Float)
    industry: Mapped[Optional[str]] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(32), default="eastmoney")
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FundNav(Base):
    __tablename__ = "fund_nav"
    __table_args__ = (
        UniqueConstraint("fund_code", "nav_date", name="uq_fund_nav_code_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fund_code: Mapped[str] = mapped_column(String(16), nullable=False)
    instrument_id: Mapped[str] = mapped_column(String(32), nullable=False)
    nav_date: Mapped[date] = mapped_column(Date, nullable=False)
    nav: Mapped[float] = mapped_column(Float, nullable=False)
    acc_nav: Mapped[Optional[float]] = mapped_column(Float)
    daily_return: Mapped[Optional[float]] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(32), default="eastmoney")
    status: Mapped[str] = mapped_column(String(16), default="official")
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CrawlAudit(Base):
    __tablename__ = "crawl_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(16), default="running")
    rows_upserted: Mapped[int] = mapped_column(Integer, default=0)
    errors_json: Mapped[Optional[str]] = mapped_column(Text)


class SiteUser(Base):
    __tablename__ = "site_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(64))
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LoginLog(Base):
    __tablename__ = "login_logs"
    __table_args__ = (Index("ix_login_logs_created_at", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    login_type: Mapped[str] = mapped_column(String(16), default="frontend")
    success: Mapped[bool] = mapped_column(default=False)
    ip: Mapped[Optional[str]] = mapped_column(String(64))
    user_agent: Mapped[Optional[str]] = mapped_column(String(512))
    failure_reason: Mapped[Optional[str]] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserFund(Base):
    __tablename__ = "user_funds"
    __table_args__ = (
        UniqueConstraint("user_id", "instrument_id", name="uq_user_fund"),
        Index("ix_user_funds_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    instrument_id: Mapped[str] = mapped_column(String(32), nullable=False)
    fund_code: Mapped[str] = mapped_column(String(16), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    market: Mapped[str] = mapped_column(String(16), default="A股")
    sector: Mapped[str] = mapped_column(String(16), default="均衡")
    enabled: Mapped[bool] = mapped_column(default=True)
    crawl_enabled: Mapped[bool] = mapped_column(default=True)
    nav_lookback: Mapped[str] = mapped_column(String(32), default="since_inception")
    config_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserAlertConfig(Base):
    __tablename__ = "user_alert_configs"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserAlertState(Base):
    __tablename__ = "user_alert_state"
    __table_args__ = (
        UniqueConstraint("user_id", "instrument_id", name="uq_user_alert_state"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    instrument_id: Mapped[str] = mapped_column(String(32), nullable=False)
    notified_json: Mapped[Optional[str]] = mapped_column(Text)
    last_dd_pct: Mapped[Optional[float]] = mapped_column(Float)
    last_check: Mapped[Optional[datetime]] = mapped_column(DateTime)
