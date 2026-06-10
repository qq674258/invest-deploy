from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any

from invest.config_loader import InstrumentProfile, instruments_for_job
from invest.core.crawl_logger import CrawlProgressLogger
from invest.core.instrument_registry import get_instrument
from invest.data.providers.eastmoney_fund import EastmoneyFundProvider
from invest.data.providers.fund_nav import FundManagerProfile
from invest.data.providers.base import MacroPoint
from invest.data.providers.cboe_putcall_provider import CboePutCallProvider
from invest.data.providers.fear_greed_provider import FearGreedProvider
from invest.data.providers.fred_provider import FredProvider
from invest.data.providers.etf_valuation_provider import EtfValuationProvider
from invest.data.providers.index_breadth_provider import IndexBreadthProvider
from invest.data.providers.multpl_provider import MultplProvider
from invest.data.providers.pe_ttm_provider import PeTtmProvider
from invest.data.providers.stooq_provider import StooqProvider
from invest.data.providers.yahoo_chart_provider import YahooChartProvider
from invest.data.providers.yfinance_provider import YFinanceProvider
from invest.data.repository.admin_repo import AdminRepository
from invest.data.repository.fund_repo import FundRepository
from invest.data.repository.market_repo import MarketRepository
from invest.data.validators.market_data import (
    ValidationError,
    validate_macro_point,
    validate_ohlcv_bar,
    validate_price_jump,
)
from invest.core.crawl_config import get_defaults, get_job_macro_items, load_crawl_config
from invest.core.incremental_crawl import (
    RECENT_CRAWL_LOOKBACK_DAYS,
    resolve_fund_nav_max_days,
    resolve_ohlcv_lookback_days,
)
from invest.core.instrument_registry import load_all_instruments
from invest.db.session import get_session
from invest.settings import settings

logger = logging.getLogger(__name__)


def _manager_profile_stub(
    mgr_id: str, on_fund: dict[str, Any] | None
) -> FundManagerProfile | None:
    if not on_fund:
        return None
    name = on_fund.get("name")
    if not name and not on_fund.get("tenure_return_pct"):
        return None
    return FundManagerProfile(
        mgr_id=mgr_id,
        name=name,
        resume=None,
        detail={
            "source": "fund_manager_list_stub",
            "start_date": on_fund.get("start_date"),
            "tenure_days": on_fund.get("tenure_days"),
            "tenure_return_pct": on_fund.get("tenure_return_pct"),
        },
        fetched_at=datetime.utcnow(),
    )


@dataclass
class MacroSpec:
    series_id: str
    provider: str  # yfinance | fred | multpl | pe_ttm | cboe_putcall | cnn_fear_greed | index_breadth | etf_valuation
    symbol: str | None = None
    fred_id: str | None = None


def _macro_spec_from_item(item: dict) -> MacroSpec:
    return MacroSpec(
        series_id=str(item["series_id"]),
        provider=str(item["provider"]),
        symbol=item.get("symbol"),
        fred_id=item.get("fred_id"),
    )


def macro_specs_for_job(job_id: str) -> list[MacroSpec]:
    items = get_job_macro_items(job_id)
    return [_macro_spec_from_item(it) for it in items]


def macro_by_job() -> dict[str, list[MacroSpec]]:
    cfg = load_crawl_config()
    jobs = cfg.get("jobs") or {}
    out: dict[str, list[MacroSpec]] = {}
    for job_id in jobs:
        specs = macro_specs_for_job(job_id)
        if specs:
            out[job_id] = specs
    if "crawl_us" not in out:
        ndx = macro_specs_for_job("crawl_ndx")
        spx = macro_specs_for_job("crawl_spx")
        if ndx or spx:
            out["crawl_us"] = ndx + spx
    return out


class CrawlService:
    def __init__(self):
        self.yf = YFinanceProvider()
        self.stooq = StooqProvider()
        self.yahoo_chart = YahooChartProvider()
        self.fred = FredProvider()
        self.multpl = MultplProvider()
        self.pe_ttm = PeTtmProvider()
        self.fear_greed = FearGreedProvider()
        self.cboe_putcall = CboePutCallProvider()
        self.etf_valuation = EtfValuationProvider()
        self.eastmoney = EastmoneyFundProvider()

    def run_job(
        self,
        job_id: str,
        lookback_days: int | None = None,
        *,
        incremental: bool = False,
    ) -> dict:
        errors: list[str] = []
        total_rows = 0
        self._lookback_days = lookback_days
        self._incremental = incremental

        with get_session() as session:
            repo = MarketRepository(session)
            synced = repo.sync_instruments_from_config()
            logger.info("同步标的配置 %d 条", synced)
            audit = repo.start_audit(job_id)

            profiles = instruments_for_job(job_id)
            for profile in profiles:
                try:
                    n = self._crawl_instrument(repo, profile, errors)
                    total_rows += n
                except Exception as exc:
                    msg = f"{profile.instrument_id}: {exc}"
                    logger.exception(msg)
                    errors.append(msg)

            for spec in macro_by_job().get(job_id, []):
                try:
                    n = self._crawl_macro(repo, spec, errors)
                    total_rows += n
                except Exception as exc:
                    msg = f"{spec.series_id}: {exc}"
                    logger.exception(msg)
                    errors.append(msg)

            status = "success" if not errors else "partial"
            repo.finish_audit(audit, status, total_rows, errors)

        return {"job_id": job_id, "rows": total_rows, "errors": errors, "status": status}

    def crawl_all_funds(
        self,
        *,
        incremental: bool = False,
        progress: CrawlProgressLogger | None = None,
    ) -> dict:
        """爬取所有 crawl_enabled 的主动基金。"""
        errors: list[str] = []
        total_rows = 0
        self._incremental = incremental
        funds = [
            p
            for p in load_all_instruments()
            if p.asset_class == "cn_active_fund"
            and p.enabled
            and p.raw.get("crawl_enabled", True)
        ]
        for profile in funds:
            try:
                result = self.crawl_fund_id(
                    profile.instrument_id,
                    progress=progress,
                )
                total_rows += int(result.get("rows") or 0)
                errors.extend(result.get("errors") or [])
            except Exception as exc:
                msg = f"{profile.instrument_id}: {exc}"
                logger.exception(msg)
                errors.append(msg)
        status = "success" if not errors else "partial"
        return {
            "job_id": "crawl_cn_funds",
            "funds": len(funds),
            "rows": total_rows,
            "errors": errors,
            "status": status,
            "incremental": incremental,
        }

    def crawl_instrument_id(
        self,
        instrument_id: str,
        lookback_days: int | None = None,
        *,
        nav_lookback: str | None = None,
        recent_bars: int | None = None,
        progress: CrawlProgressLogger | None = None,
    ) -> dict:
        log = progress or CrawlProgressLogger()
        self._recent_bars = recent_bars
        profile = get_instrument(instrument_id)
        if not profile:
            raise ValueError("unknown_instrument")
        if recent_bars:
            log.info(f"开始采集 {instrument_id}（{profile.display_name}）· 近期 {recent_bars} 条", 2)
        else:
            log.info(f"开始采集 {instrument_id}（{profile.display_name}）", 2)
        if profile.asset_class == "cn_active_fund":
            lookback = nav_lookback or profile.raw.get("nav_lookback", "since_inception")
            result = self.crawl_fund_id(
                instrument_id,
                nav_lookback=lookback,
                recent_bars=recent_bars,
                progress=log,
            )
            result["logs"] = log.as_list()
            return result
        self._lookback_days = lookback_days
        job_id = f"manual_{instrument_id}"
        errors: list[str] = []
        with get_session() as session:
            repo = MarketRepository(session)
            repo.sync_instruments_from_config()
            log.info("同步标的配置完成", 8)
            audit = repo.start_audit(job_id)
            try:
                log.info(f"拉取行情 {profile.ohlcv.symbol if profile.ohlcv else '?'}…", 15)
                n = self._crawl_instrument(repo, profile, errors)
                log.info(f"行情写入 {n} 条", 70)
                if profile.crawl_job:
                    for spec in macro_by_job().get(profile.crawl_job or "", []):
                        try:
                            log.info(f"拉取宏观 {spec.series_id}…", 75)
                            n += self._crawl_macro(repo, spec, errors)
                        except Exception as exc:
                            errors.append(f"{spec.series_id}: {exc}")
                            log.warn(f"宏观 {spec.series_id} 失败: {exc}")
            except Exception as exc:
                errors.append(str(exc))
                log.error(f"采集异常: {exc}")
                n = 0
            status = "success" if not errors else "partial"
            repo.finish_audit(audit, status, n, errors)
        log.info(
            f"完成：状态 {status}，共 {n} 条"
            + (f"，{len(errors)} 条警告/错误" if errors else ""),
            100,
        )
        return {
            "instrument_id": instrument_id,
            "rows": n,
            "errors": errors,
            "status": status,
            "logs": log.as_list(),
        }

    def _sync_fund_managers(
        self,
        fund_code: str,
        cfg: dict[str, Any],
        admin: AdminRepository,
        log: CrawlProgressLogger,
        errors: list[str],
        *,
        base_progress: int = 20,
    ) -> dict[str, Any]:
        mgr_ids: list[str] = list(cfg.get("manager_ids") or [])
        try:
            if not mgr_ids:
                log.info("解析现任基金经理 ID…", base_progress)
                current = self.eastmoney.fetch_manager_list(
                    fund_code, current_only=True
                )
                mgr_ids = [m.mgr_id for m in current]
                cfg["manager_ids"] = mgr_ids
                cfg["managers_on_fund"] = [asdict(m) for m in current]
                if current:
                    names = "、".join(m.name for m in current if m.name)
                    if names:
                        cfg["fund_manager"] = names
                log.info(
                    f"现任经理 {len(mgr_ids)} 人"
                    + (f"：{cfg.get('fund_manager', '')}" if mgr_ids else "（未解析到）"),
                    base_progress + 4,
                )
            else:
                log.info(f"使用已保存的经理 ID（{len(mgr_ids)} 人）", base_progress + 2)

            if not mgr_ids:
                return cfg

            log.info("拉取基金经理详情…", base_progress + 6)
            on_fund = {
                str(m.get("mgr_id")): m
                for m in (cfg.get("managers_on_fund") or [])
                if m.get("mgr_id")
            }
            for i, mid in enumerate(mgr_ids):
                try:
                    detail = self.eastmoney.fetch_manager_detail(mid, fund_code)
                    admin.upsert_manager_profile(detail)
                    label = detail.name or mid
                    pct = base_progress + 8 + int((i + 1) / max(len(mgr_ids), 1) * 10)
                    log.info(f"经理档案：{label}（{i + 1}/{len(mgr_ids)}）", pct)
                except Exception as exc:
                    stub = _manager_profile_stub(mid, on_fund.get(mid))
                    if stub:
                        admin.upsert_manager_profile(stub)
                        log.warn(
                            f"经理 {mid} 详情 API 失败，已保存任职摘要: {exc}",
                            base_progress + 10,
                        )
                    else:
                        errors.append(f"manager_{mid}: {exc}")
                        log.warn(f"经理 {mid} 详情失败: {exc}", base_progress + 10)
                if i < len(mgr_ids) - 1:
                    time.sleep(0.8)
            cfg["managers_fetched_at"] = datetime.utcnow().isoformat()
        except Exception as exc:
            errors.append(f"managers: {exc}")
            log.warn(f"经理信息同步失败（继续净值）: {exc}", base_progress + 4)
        return cfg

    def _sync_fund_extras(
        self,
        instrument_id: str,
        fund_code: str,
        cfg: dict[str, Any],
        fund_repo: FundRepository,
        log: CrawlProgressLogger,
        errors: list[str],
    ) -> dict[str, Any]:
        try:
            log.info("拉取阶段涨幅（历史业绩）…", 91)
            periods = self.eastmoney.fetch_period_increase(fund_code)
            cfg["period_increase"] = [asdict(p) for p in periods]
            log.info(f"阶段涨幅 {len(periods)} 项", 92)
        except Exception as exc:
            errors.append(f"period_increase: {exc}")
            log.warn(f"阶段涨幅失败: {exc}", 92)
        try:
            rules = self.eastmoney.fetch_trading_rules(fund_code)
            cfg["trading_rules"] = asdict(rules)
            log.info("交易规则已更新", 93)
        except Exception as exc:
            errors.append(f"trading_rules: {exc}")
            log.warn(f"交易规则失败: {exc}", 93)
        try:
            snap = self.eastmoney.fetch_holdings(fund_code)
            if snap.holdings and snap.report_date:
                rd = date.fromisoformat(snap.report_date[:10])
                n = fund_repo.upsert_holdings(
                    instrument_id,
                    fund_code,
                    rd,
                    [asdict(h) for h in snap.holdings],
                )
                log.info(f"持仓入库 {n} 条（报告期 {snap.report_date}）", 94)
            elif snap.holdings:
                log.warn("持仓无报告期，跳过入库", 94)
            else:
                log.info("未解析到持仓（可能为债基/QDII 或接口变更）", 94)
        except Exception as exc:
            errors.append(f"holdings: {exc}")
            log.warn(f"持仓失败: {exc}", 94)
        return cfg

    def crawl_fund_id(
        self,
        instrument_id: str,
        nav_lookback: str | None = None,
        *,
        recent_bars: int | None = None,
        progress: CrawlProgressLogger | None = None,
    ) -> dict:
        profile = get_instrument(instrument_id)
        if not profile or profile.asset_class != "cn_active_fund":
            raise ValueError("not_fund")
        log = progress or CrawlProgressLogger()
        if not profile.raw.get("crawl_enabled", True):
            raise ValueError("crawl_disabled")
        fund_code = profile.raw.get("fund_code") or profile.raw.get("nav", {}).get(
            "symbol"
        )
        if not fund_code:
            raise ValueError("no_fund_code")
        lookback = nav_lookback or profile.raw.get("nav_lookback", "since_inception")
        lookback_label = {
            "1y": "1年",
            "3y": "3年",
            "5y": "5年",
            "since_inception": "成立以来",
        }.get(lookback, lookback)
        incremental = getattr(self, "_incremental", False)
        if recent_bars:
            lookback_label = f"近期 {recent_bars} 条"
        elif incremental:
            lookback_label = f"{lookback_label}（增量）"
        job_id = f"manual_fund_{instrument_id}"
        errors: list[str] = []
        meta_note: dict = {}
        cfg = dict(profile.raw)
        log.info(
            f"基金 {profile.display_name}（{fund_code}）· 回溯 {lookback_label}",
            5,
        )
        with get_session() as session:
            from invest.data.repository.admin_repo import AdminRepository

            repo = MarketRepository(session)
            admin = AdminRepository(session)
            fund_repo = FundRepository(session)
            nav_max_days = resolve_fund_nav_max_days(
                fund_repo.get_last_nav_date(instrument_id),
                incremental=incremental,
            )
            audit = repo.start_audit(job_id)
            n = 0
            try:
                if not recent_bars:
                    try:
                        log.info("请求东方财富基金概况…", 10)
                        meta = self.eastmoney.fetch_meta(fund_code)
                        meta_note = {
                            "fund_manager": meta.fund_manager,
                            "fund_company": meta.fund_company,
                            "fund_type": meta.fund_type,
                            "establish_date": meta.establish_date,
                        }
                        cfg.update({k: v for k, v in meta_note.items() if v})
                        parts = [
                            p
                            for p in [
                                meta.fund_company,
                                meta.fund_manager,
                                meta.fund_type,
                            ]
                            if p
                        ]
                        log.info(
                            "概况获取成功" + (f"：{' · '.join(parts)}" if parts else ""),
                            18,
                        )
                    except Exception as exc:
                        errors.append(f"meta: {exc}")
                        log.warn(f"概况接口失败（继续拉净值）: {exc}", 18)

                    cfg = self._sync_fund_managers(
                        fund_code, cfg, admin, log, errors, base_progress=20
                    )

                page_count = 0

                def on_page(page: int, count: int, oldest: date | None) -> None:
                    nonlocal page_count
                    page_count = page
                    pct = min(38 + page * 10, 88)
                    oldest_s = oldest.isoformat() if oldest else "—"
                    log.info(
                        f"净值第 {page} 页：本页 {count} 条，最早 {oldest_s}",
                        pct,
                    )

                crawl_defaults = get_defaults()
                nav_sleep = float(crawl_defaults.get("fund_nav_page_sleep_sec", 2.0))
                if recent_bars:
                    log.info(
                        f"近期模式：仅拉取最新 {recent_bars} 条净值（同日期覆盖）…",
                        36,
                    )
                else:
                    log.info(
                        f"开始分页拉取历史净值（每页 20 条，间隔约 {nav_sleep}s；"
                        "失败自动重试，中断时保留已拉取数据）…",
                        36,
                    )
                bars, nav_truncated = self.eastmoney.fetch_nav_history(
                    fund_code,
                    lookback=lookback if not recent_bars else "1y",
                    max_lookback_days=nav_max_days if not recent_bars else RECENT_CRAWL_LOOKBACK_DAYS,
                    max_pages=1 if recent_bars else None,
                    on_page=on_page if not recent_bars else None,
                )
                if recent_bars and bars:
                    bars = bars[-recent_bars:]
                if nav_truncated:
                    errors.append(
                        "nav: 分页中途网络/限流中断，已写入截至中断前的净值"
                    )
                    log.warn(
                        f"净值分页提前结束，保留 {len(bars)} 条（可能未覆盖完整 {lookback_label}）",
                        88,
                    )
                if bars:
                    pages_note = f"{page_count} 页" if not recent_bars else "1 页"
                    log.info(
                        f"净值拉取完成：共 {len(bars)} 条（{pages_note}），"
                        f"{bars[0].nav_date} → {bars[-1].nav_date}",
                        90,
                    )
                else:
                    log.warn("未获取到净值数据", 90)
                log.info("写入数据库…", 92)
                n = admin.upsert_fund_nav(
                    instrument_id, fund_code, bars, source="eastmoney"
                )
                log.info(f"入库 {n} 条净值", 90)
                fund_repo = FundRepository(session)
                if not recent_bars:
                    cfg = self._sync_fund_extras(
                        instrument_id, fund_code, cfg, fund_repo, log, errors
                    )
                cfg["last_crawl_at"] = datetime.utcnow().isoformat()
                admin.upsert_managed_instrument(
                    instrument_id,
                    profile.display_name,
                    profile.asset_class,
                    cfg,
                    enabled=profile.enabled,
                )
            except Exception as exc:
                errors.append(str(exc))
                log.error(f"采集失败: {exc}")
            status = "success" if not errors else "partial"
            repo.finish_audit(audit, status, n, errors)
        log.info(
            f"完成：{status}，写入 {n} 条"
            + (f"；{len(errors)} 项异常" if errors else ""),
            100,
        )
        return {
            "instrument_id": instrument_id,
            "fund_code": fund_code,
            "rows": n,
            "errors": errors,
            "status": status,
            "meta": meta_note,
            "nav_lookback": lookback,
            "recent_bars": recent_bars,
            "logs": log.as_list(),
        }

    def _crawl_instrument(
        self,
        repo: MarketRepository,
        profile: InstrumentProfile,
        errors: list[str],
    ) -> int:
        assert profile.ohlcv is not None
        symbol = profile.ohlcv.symbol
        full_lookback = getattr(self, "_lookback_days", None)
        incremental = getattr(self, "_incremental", False)
        recent_bars = getattr(self, "_recent_bars", None)
        last_date = repo.get_last_trade_date(profile.instrument_id)
        if recent_bars:
            lookback = RECENT_CRAWL_LOOKBACK_DAYS
        else:
            lookback = resolve_ohlcv_lookback_days(
                last_date, full_lookback, incremental=incremental
            )
        if incremental and last_date:
            logger.info(
                "%s 增量采集：自 %s 起约 %d 自然日",
                profile.instrument_id,
                last_date,
                lookback,
            )
        crawl_defaults = get_defaults()
        retry_n = int(crawl_defaults.get("crawl_retry", settings.crawl_retry))
        retry_sec = int(
            crawl_defaults.get("crawl_retry_interval_sec", settings.crawl_retry_interval_sec)
        )
        jump_thr = float(
            crawl_defaults.get("price_jump_threshold", settings.price_jump_threshold)
        )

        bars = []
        for attempt in range(1, retry_n + 1):
            try:
                bars = self.yf.fetch_ohlcv(symbol, lookback_days=lookback)
                if bars:
                    break
            except Exception as exc:
                logger.warning("yfinance %s (%d/%d): %s", symbol, attempt, retry_n, exc)
            time.sleep(retry_sec)

        source = "yfinance"
        if not bars:
            logger.info("yfinance 无数据，尝试 Yahoo Chart API: %s", symbol)
            try:
                bars = self.yahoo_chart.fetch_ohlcv(symbol, lookback_days=lookback)
                source = "yahoo_chart"
            except Exception as exc:
                logger.warning("Yahoo chart 失败 %s: %s", symbol, exc)
        if not bars:
            logger.info("尝试 Stooq: %s", symbol)
            bars = self.stooq.fetch_ohlcv(symbol, lookback_days=lookback)
            source = "stooq"

        valid_bars = []
        latest_date = max((b.trade_date for b in bars), default=None)
        for bar in bars:
            try:
                validate_ohlcv_bar(bar)
                if bar.trade_date == latest_date:
                    db_prev = repo.get_prev_close(profile.instrument_id, bar.trade_date)
                    if db_prev is not None:
                        try:
                            validate_price_jump(db_prev, bar.close, jump_thr)
                        except ValidationError as exc:
                            errors.append(
                                f"{profile.instrument_id} latest {bar.trade_date}: {exc}"
                            )
                            continue
                valid_bars.append(bar)
            except ValidationError as exc:
                errors.append(f"{profile.instrument_id} {bar.trade_date}: {exc}")

        if recent_bars and valid_bars:
            valid_bars = sorted(valid_bars, key=lambda b: b.trade_date)[-recent_bars:]

        n, _ = repo.upsert_ohlcv(profile.instrument_id, valid_bars, source=source)
        logger.info("%s OHLCV 写入 %d 条", profile.instrument_id, n)
        return n

    def _crawl_macro(
        self,
        repo: MarketRepository,
        spec: MacroSpec,
        errors: list[str],
    ) -> int:
        points = []
        source = spec.provider
        lookback = getattr(self, "_lookback_days", None)
        incremental = getattr(self, "_incremental", False)
        recent_bars = getattr(self, "_recent_bars", None)
        if recent_bars:
            lookback = RECENT_CRAWL_LOOKBACK_DAYS
        elif lookback is None and incremental:
            from invest.core.incremental_crawl import INCREMENTAL_MAX_DAYS

            lookback = INCREMENTAL_MAX_DAYS
        elif lookback is None:
            from invest.settings import get_ohlcv_lookback_days

            lookback = get_ohlcv_lookback_days()

        if spec.provider == "yfinance" and spec.symbol:
            points = self.yf.fetch_macro_daily(spec.symbol, lookback_days=lookback)
            if not points:
                for fetcher, src in (
                    (self.yahoo_chart.fetch_ohlcv, "yahoo_chart"),
                    (self.stooq.fetch_ohlcv, "stooq"),
                ):
                    try:
                        bars = fetcher(spec.symbol, lookback_days=lookback)
                        if bars:
                            points = [
                                MacroPoint(trade_date=b.trade_date, value=b.close)
                                for b in bars
                            ]
                            source = src
                            break
                    except Exception:
                        continue
        elif spec.provider == "fred" and spec.fred_id:
            if not self.fred.available:
                errors.append(f"{spec.series_id}: 跳过（未配置 FRED_API_KEY）")
                return 0
            points = self.fred.fetch_series(spec.fred_id, lookback_days=lookback)
        elif spec.provider == "multpl":
            try:
                points = self.multpl.fetch_series(spec.series_id, lookback_days=lookback)
                source = "multpl"
            except Exception as exc:
                errors.append(f"{spec.series_id}: multpl {exc}")
                return 0
        elif spec.provider == "pe_ttm":
            try:
                points = self.pe_ttm.fetch_series(spec.series_id, lookback_days=lookback)
                source = "multpl+yfinance"
                if points:
                    latest = max(points, key=lambda p: p.trade_date)
                    ym = (latest.trade_date.year, latest.trade_date.month)
                    keep = {
                        p.trade_date
                        for p in points
                        if (p.trade_date.year, p.trade_date.month) == ym
                    }
                    pruned = repo.prune_macro_month(
                        spec.series_id, ym[0], ym[1], keep_dates=keep
                    )
                    if pruned:
                        logger.info(
                            "%s 清理当月陈旧宏观点 %d 条",
                            spec.series_id,
                            pruned,
                        )
            except Exception as exc:
                errors.append(f"{spec.series_id}: pe_ttm {exc}")
                return 0
        elif spec.provider == "cboe_putcall":
            points = self.cboe_putcall.fetch_series(lookback_days=lookback)
            source = "cboe"
        elif spec.provider == "cnn_fear_greed":
            points = self.fear_greed.fetch_daily(lookback_days=lookback)
            source = "cnn"
        elif spec.provider == "index_breadth":
            cfg = spec.symbol or "ndx_constituents.yaml"
            breadth = IndexBreadthProvider(cfg, spec.series_id)
            points = breadth.compute_pct_above_ma200(lookback_days=lookback)
            source = "yfinance_breadth"
        elif spec.provider == "etf_valuation":
            sym = spec.symbol or "QQQ"
            points = self.etf_valuation.fetch_forward_pe(sym)
            source = "yfinance"
        else:
            raise ValueError(f"未知宏观配置: {spec}")

        valid = []
        for pt in points:
            try:
                validate_macro_point(pt)
                valid.append(pt)
            except ValidationError as exc:
                errors.append(f"{spec.series_id} {pt.trade_date}: {exc}")

        if recent_bars and valid:
            valid = sorted(valid, key=lambda p: p.trade_date)[-recent_bars:]

        n = repo.upsert_macro(spec.series_id, valid, source=source)
        logger.info("%s 宏观写入 %d 条", spec.series_id, n)
        return n

    def health_summary(self) -> dict:
        """数据新鲜度摘要."""
        from sqlalchemy import func, select

        from invest.db.models import MacroSeries, Ohlcv

        from invest.db.models import FundNav

        summary: dict = {"instruments": {}, "macro": {}, "funds": {}}
        with get_session() as session:
            for row in session.execute(
                select(
                    Ohlcv.instrument_id,
                    func.min(Ohlcv.trade_date),
                    func.max(Ohlcv.trade_date),
                    func.count(Ohlcv.id),
                ).group_by(Ohlcv.instrument_id)
            ):
                first_d, last_d = row[1], row[2]
                span_years = None
                if first_d and last_d:
                    span_years = round((last_d - first_d).days / 365.25, 2)
                summary["instruments"][row[0]] = {
                    "first_date": first_d.isoformat() if first_d else None,
                    "last_date": last_d.isoformat() if last_d else None,
                    "rows": row[3],
                    "span_years": span_years,
                }
            for row in session.execute(
                select(
                    MacroSeries.series_id,
                    func.max(MacroSeries.trade_date),
                    func.count(MacroSeries.id),
                ).group_by(MacroSeries.series_id)
            ):
                summary["macro"][row[0]] = {
                    "last_date": row[1].isoformat() if row[1] else None,
                    "rows": row[2],
                }
            for row in session.execute(
                select(
                    FundNav.instrument_id,
                    func.min(FundNav.nav_date),
                    func.max(FundNav.nav_date),
                    func.count(FundNav.id),
                ).group_by(FundNav.instrument_id)
            ):
                first_d, last_d = row[1], row[2]
                span_years = None
                if first_d and last_d:
                    span_years = round((last_d - first_d).days / 365.25, 2)
                summary["funds"][row[0]] = {
                    "first_date": first_d.isoformat() if first_d else None,
                    "last_date": last_d.isoformat() if last_d else None,
                    "rows": row[3],
                    "span_years": span_years,
                }
        return summary
