from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class FundNavBar:
    nav_date: date
    nav: float
    acc_nav: float | None = None
    daily_return: float | None = None


@dataclass
class FundMeta:
    fund_code: str
    name: str | None = None
    fund_manager: str | None = None
    fund_company: str | None = None
    fund_type: str | None = None
    establish_date: str | None = None


@dataclass
class FundManagerOnFund:
    """基金经理在某只基金上的任职信息。"""

    mgr_id: str
    name: str | None = None
    fund_code: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    tenure_days: int | None = None
    tenure_return_pct: float | None = None
    is_current: bool = True


@dataclass
class FundManagerProfile:
    """基金经理档案（可跨多只基金复用）。"""

    mgr_id: str
    name: str | None = None
    company: str | None = None
    resume: str | None = None
    photo_url: str | None = None
    experience_years: str | None = None
    managed_fund_codes: list[str] = field(default_factory=list)
    managed_fund_names: list[str] = field(default_factory=list)
    detail: dict | None = None
    fetched_at: datetime | None = None


@dataclass
class FundHoldingRow:
    symbol: str | None
    name: str
    weight_pct: float | None = None
    change_pct: float | None = None
    industry: str | None = None


@dataclass
class FundHoldingsSnapshot:
    fund_code: str
    report_date: str | None
    holdings: list[FundHoldingRow]
    source: str = "eastmoney"


@dataclass
class FundPeriodReturn:
    period_id: str
    label: str
    return_pct: float | None = None
    peer_avg_pct: float | None = None
    benchmark_pct: float | None = None
    rank: str | None = None
    peer_count: str | None = None


@dataclass
class FundTradingRules:
    fund_code: str
    purchase_status: str | None = None
    redeem_status: str | None = None
    min_purchase: str | None = None
    management_fee: str | None = None
    custody_fee: str | None = None
    sales_fee: str | None = None
    performance_benchmark: str | None = None
    subscription_fee: str | None = None
    redemption_fee: str | None = None
    dca_supported: str | None = None
    trade_notes: str | None = None
    detail: dict | None = None


@dataclass
class FundResolveResult:
    fund_code: str
    display_name: str | None = None
    fund_manager: str | None = None
    fund_company: str | None = None
    fund_type: str | None = None
    establish_date: str | None = None
    manager_ids: list[str] = field(default_factory=list)
    managers: list[FundManagerOnFund] = field(default_factory=list)
