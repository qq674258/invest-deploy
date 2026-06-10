from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone

import httpx

from invest.data.providers.fund_nav import (
    FundHoldingRow,
    FundHoldingsSnapshot,
    FundManagerOnFund,
    FundManagerProfile,
    FundMeta,
    FundNavBar,
    FundPeriodReturn,
    FundResolveResult,
    FundTradingRules,
)
from invest.core.crawl_config import get_defaults, get_endpoint
from invest.settings import settings

logger = logging.getLogger(__name__)

# 东方财富 lsjz：pageSize 过大（如 500）会返回空列表，20 稳定
_NAV_PAGE_SIZE = 20

_LOOKBACK_DAYS = {
    "1y": 370,
    "3y": 370 * 3 + 30,
    "5y": 370 * 5 + 30,
    "since_inception": 365 * 30,
}


class EastmoneyFundProvider:
    def __init__(self) -> None:
        self._base_headers = {
            "User-Agent": settings.crawl_user_agent,
            "Accept": "application/json, text/plain, */*",
        }

    def _headers(self, fund_code: str) -> dict[str, str]:
        return {
            **self._base_headers,
            "Referer": f"http://fundf10.eastmoney.com/jjjz_{fund_code}.html",
        }

    def _client(self, fund_code: str) -> httpx.Client:
        proxy = settings.http_proxy or None
        return httpx.Client(
            headers=self._headers(fund_code),
            timeout=60.0,
            proxy=proxy,
            follow_redirects=True,
        )

    def fetch_meta(self, fund_code: str) -> FundMeta:
        try:
            return self._fetch_meta_mobile(fund_code)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in (404, 403):
                raise
            logger.info("基金 %s 概况走 pingzhongdata 备用", fund_code)
        except Exception as exc:
            logger.warning("基金 %s 概况 mobile 失败: %s", fund_code, exc)
        return self._fetch_meta_pingzhong(fund_code)

    def _fetch_meta_mobile(self, fund_code: str) -> FundMeta:
        url = get_endpoint("eastmoney_fund_brief")
        params = {
            "FCODE": fund_code,
            "deviceid": "WAP",
            "plat": "WAP",
            "product": "EFund",
            "version": "2.0.0",
        }
        with self._client(fund_code) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
        datas = data.get("Datas") or {}
        infos: dict = {}
        if isinstance(datas, dict):
            brief = datas.get("BriefInfos")
            if isinstance(brief, list) and brief:
                infos = brief[0]
            elif isinstance(brief, dict):
                infos = brief
            else:
                infos = datas
        return FundMeta(
            fund_code=fund_code,
            name=infos.get("SHORTNAME") or infos.get("FULLNAME"),
            fund_manager=infos.get("JJJL") or infos.get("FUNDMANAGER"),
            fund_company=infos.get("JJGS") or infos.get("COMPANY"),
            fund_type=infos.get("FTYPE"),
            establish_date=infos.get("ESTABDATE"),
        )

    def _fetch_meta_pingzhong(self, fund_code: str) -> FundMeta:
        js = self._fetch_pingzhong_js(fund_code)

        def var_str(name: str) -> str | None:
            m = re.search(rf'var\s+{name}\s*=\s*"([^"]*)"', js)
            return m.group(1).strip() if m and m.group(1) else None

        return FundMeta(
            fund_code=fund_code,
            name=var_str("fS_name"),
            fund_manager=var_str("fund_manager") or var_str("fund_fundmanager"),
            fund_company=var_str("fund_company"),
            fund_type=var_str("fund_type") or var_str("ftype"),
            establish_date=var_str("fund_setupdate"),
        )

    def _fetch_pingzhong_js(self, fund_code: str) -> str:
        url = get_endpoint("eastmoney_fund_pingzhong", fund_code=fund_code)
        with self._client(fund_code) as client:
            r = client.get(
                url,
                headers={
                    **self._headers(fund_code),
                    "Referer": f"https://fund.eastmoney.com/{fund_code}.html",
                },
            )
            r.raise_for_status()
            return r.text

    @staticmethod
    def _extract_js_array(js: str, var_name: str) -> list:
        marker = f"{var_name}="
        idx = js.find(marker)
        if idx < 0:
            return []
        start = js.find("[", idx)
        if start < 0:
            return []
        depth = 0
        for i in range(start, len(js)):
            ch = js[i]
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    return json.loads(js[start : i + 1])
        return []

    def _nav_crawl_timing(self) -> tuple[int, int, float]:
        defaults = get_defaults()
        retry_n = int(defaults.get("crawl_retry", settings.crawl_retry))
        retry_sec = int(
            defaults.get("crawl_retry_interval_sec", settings.crawl_retry_interval_sec)
        )
        page_sleep = float(defaults.get("fund_nav_page_sleep_sec", 2.0))
        return retry_n, retry_sec, page_sleep

    def fetch_nav_history(
        self,
        fund_code: str,
        lookback: str = "since_inception",
        *,
        max_lookback_days: int | None = None,
        max_pages: int | None = None,
        on_page: Callable[[int, int, date | None], None] | None = None,
    ) -> tuple[list[FundNavBar], bool]:
        """返回 (净值列表, 是否因网络/限流提前截断)。"""
        days = _LOOKBACK_DAYS.get(lookback, _LOOKBACK_DAYS["since_inception"])
        if max_lookback_days is not None and max_lookback_days > 0:
            days = min(days, max_lookback_days)
        cutoff = date.today() - timedelta(days=days)
        bars: list[FundNavBar] = []
        truncated = False
        page = 1
        _, _, page_sleep = self._nav_crawl_timing()
        while True:
            try:
                chunk = self._fetch_nav_page(fund_code, page, _NAV_PAGE_SIZE)
            except Exception as exc:
                if bars:
                    truncated = True
                    logger.warning(
                        "基金 %s 净值第 %d 页失败，保留已拉取 %d 条: %s",
                        fund_code,
                        page,
                        len(bars),
                        exc,
                    )
                    if on_page:
                        on_page(page, 0, None)
                    break
                raise
            if not chunk:
                if page == 1:
                    logger.info("lsjz 无数据，尝试 pingzhongdata: %s", fund_code)
                    pingzhong = self._fetch_nav_pingzhong(
                        fund_code, cutoff=cutoff, on_page=on_page
                    )
                    return pingzhong, False
                if on_page:
                    on_page(page, 0, None)
                break
            for bar in chunk:
                if bar.nav_date >= cutoff:
                    bars.append(bar)
            oldest = min(b.nav_date for b in chunk)
            if on_page:
                on_page(page, len(chunk), oldest)
            if oldest < cutoff or len(chunk) < _NAV_PAGE_SIZE:
                break
            if max_pages is not None and page >= max_pages:
                break
            page += 1
            time.sleep(page_sleep)
        bars.sort(key=lambda b: b.nav_date)
        return bars, truncated

    def _fetch_nav_pingzhong(
        self,
        fund_code: str,
        *,
        cutoff: date,
        on_page: Callable[[int, int, date | None], None] | None = None,
    ) -> list[FundNavBar]:
        js = self._fetch_pingzhong_js(fund_code)
        raw = self._extract_js_array(js, "Data_netWorthTrend")
        bars: list[FundNavBar] = []
        for row in raw:
            if not isinstance(row, (list, tuple)) or len(row) < 2:
                continue
            try:
                ts_ms = int(row[0])
                nav = float(row[1])
                nav_date = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).date()
            except (TypeError, ValueError, OSError):
                continue
            if nav_date < cutoff:
                continue
            acc_nav = float(row[2]) if len(row) > 2 and row[2] not in ("", None) else None
            daily_return = None
            if len(row) > 3 and row[3] not in ("", None):
                try:
                    daily_return = float(row[3]) / 100.0
                except (TypeError, ValueError):
                    daily_return = None
            bars.append(
                FundNavBar(
                    nav_date=nav_date,
                    nav=nav,
                    acc_nav=acc_nav,
                    daily_return=daily_return,
                )
            )
        bars.sort(key=lambda b: b.nav_date)
        if on_page:
            oldest = bars[0].nav_date if bars else None
            on_page(1, len(bars), oldest)
        return bars

    def _fetch_nav_page(
        self, fund_code: str, page_index: int, page_size: int
    ) -> list[FundNavBar]:
        retry_n, retry_sec, _ = self._nav_crawl_timing()
        last_exc: Exception | None = None
        for attempt in range(1, retry_n + 1):
            try:
                return self._fetch_nav_page_once(fund_code, page_index, page_size)
            except (httpx.HTTPError, json.JSONDecodeError, OSError) as exc:
                last_exc = exc
                logger.warning(
                    "基金 %s 净值第 %d 页请求失败 (%d/%d): %s",
                    fund_code,
                    page_index,
                    attempt,
                    retry_n,
                    exc,
                )
                if attempt < retry_n:
                    time.sleep(retry_sec * attempt)
        assert last_exc is not None
        raise last_exc

    def _fetch_nav_page_once(
        self, fund_code: str, page_index: int, page_size: int
    ) -> list[FundNavBar]:
        url = get_endpoint("eastmoney_fund_nav")
        params = {
            "fundCode": fund_code,
            "pageIndex": page_index,
            "pageSize": min(page_size, _NAV_PAGE_SIZE),
        }
        with self._client(fund_code) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            payload = r.json()
        rows = (payload.get("Data") or {}).get("LSJZList") or []
        if not rows and page_size > _NAV_PAGE_SIZE:
            return self._fetch_nav_page_once(fund_code, page_index, _NAV_PAGE_SIZE)
        out: list[FundNavBar] = []
        for row in rows:
            d_str = row.get("FSRQ")
            nav_str = row.get("DWJZ")
            if not d_str or not nav_str or nav_str in ("", "--"):
                continue
            try:
                nav_date = datetime.strptime(d_str[:10], "%Y-%m-%d").date()
                nav = float(nav_str)
            except (ValueError, TypeError):
                continue
            acc = row.get("LJJZ")
            acc_nav = float(acc) if acc and acc not in ("", "--") else None
            dr = row.get("JZZZL")
            daily_return = None
            if dr and dr not in ("", "--"):
                try:
                    daily_return = float(str(dr).replace("%", "")) / 100.0
                except ValueError:
                    daily_return = None
            out.append(
                FundNavBar(
                    nav_date=nav_date,
                    nav=nav,
                    acc_nav=acc_nav,
                    daily_return=daily_return,
                )
            )
        return out

    def resolve_fund(self, fund_code: str) -> FundResolveResult:
        """拉取基金概况 + 现任基金经理 ID（录入前预览用）。"""
        fund_code = str(fund_code).strip()
        meta = self.fetch_meta(fund_code)
        managers = self.fetch_manager_list(fund_code, current_only=True)
        names = [m.name for m in managers if m.name]
        return FundResolveResult(
            fund_code=fund_code,
            display_name=meta.name,
            fund_manager="、".join(names) if names else meta.fund_manager,
            fund_company=meta.fund_company,
            fund_type=meta.fund_type,
            establish_date=meta.establish_date,
            manager_ids=[m.mgr_id for m in managers],
            managers=managers,
        )

    def fetch_manager_list(
        self, fund_code: str, *, current_only: bool = True
    ) -> list[FundManagerOnFund]:
        url = get_endpoint("eastmoney_fund_manager_list")
        params = {
            "FCODE": fund_code,
            "deviceid": "WAP",
            "plat": "WAP",
            "product": "EFund",
            "version": "2.0.0",
        }
        with self._client(fund_code) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            payload = r.json()
        rows = payload.get("Datas") or []
        if isinstance(rows, dict):
            rows = [rows]
        return _parse_manager_list_rows(str(fund_code), rows, current_only=current_only)

    def fetch_manager_detail(
        self, mgr_id: str, fund_code: str | None = None
    ) -> FundManagerProfile:
        """按经理 ID 拉取档案（在管基金、简介等）。"""
        mgr_id = str(mgr_id).strip()
        refer_code = (fund_code or "000001").strip()
        # 天天基金文档：FundMSNMangerInfo 的参数 FCODE = 基金经理 ID（不是基金代码）
        api_attempts: list[tuple[str, dict[str, str]]] = [
            (
                "FundMSNMangerInfo",
                {
                    "FCODE": mgr_id,
                    "version": "6.3.8",
                    "AppVersion": "6.3.8",
                    "plat": "Iphone",
                },
            ),
            ("fundMSNMangerInfo", {"FCODE": mgr_id, "version": "6.3.8"}),
            ("FundMSNMangerInfo", {"mGRID": mgr_id, "version": "2.0.0"}),
            ("FundMSNMangerInfo", {"MGRID": mgr_id, "version": "6.3.8"}),
        ]
        last_exc: Exception | None = None
        for path, extra in api_attempts:
            try:
                payload = self._mobile_json(refer_code, path, **extra)
                info = payload.get("Datas") or {}
                if isinstance(info, list):
                    info = info[0] if info else {}
                if isinstance(info, dict) and _manager_detail_usable(info):
                    return _parse_manager_detail(mgr_id, info)
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code == 404:
                    logger.debug(
                        "经理 %s %s 404 (params=%s)", mgr_id, path, extra
                    )
                    continue
                logger.warning("经理 %s %s HTTP %s", mgr_id, path, exc)
            except Exception as exc:
                last_exc = exc
                logger.debug("经理 %s %s 失败: %s", mgr_id, path, exc)

        try:
            return self._fetch_manager_detail_html(mgr_id)
        except Exception as html_exc:
            logger.warning("经理 %s HTML 备用失败: %s", mgr_id, html_exc)
            if last_exc:
                raise last_exc from html_exc
            raise html_exc

    def _fetch_manager_detail_html(self, mgr_id: str) -> FundManagerProfile:
        """东财经理档案页 HTML 备用（mobile API 404 时）。"""
        url = get_endpoint("eastmoney_fund_manager_page", mgr_id=mgr_id)
        headers = {
            **self._base_headers,
            "Referer": "https://fund.eastmoney.com/",
            "Accept": "text/html,application/xhtml+xml",
        }
        with httpx.Client(
            headers=headers,
            timeout=60.0,
            proxy=settings.http_proxy or None,
            follow_redirects=True,
        ) as client:
            r = client.get(url)
            r.raise_for_status()
            html = r.text

        name = None
        m_title = re.search(r"基金经理[：:]\s*([^<\s_]+)", html) or re.search(
            r"<title>([^_]+)_", html
        )
        if m_title:
            name = m_title.group(1).strip()

        resume = None
        m_resume = re.search(r"基金经理简介[：:]\s*([^<]+?)(?:</|$)", html, re.S)
        if m_resume:
            resume = re.sub(r"\s+", " ", m_resume.group(1)).strip()[:4000]

        company = None
        m_co = re.search(r"现任基金公司[：:]\s*([^<\n]+)", html)
        if m_co:
            company = m_co.group(1).strip()

        experience = None
        m_exp = re.search(r"累计任职时间[：:]\s*([^<\n]+)", html)
        if m_exp:
            experience = m_exp.group(1).strip()

        codes: list[str] = []
        names: list[str] = []
        for row in re.findall(
            r"<tr[^>]*>\s*<td[^>]*>\s*(\d{6})\s*</td>\s*<td[^>]*>([^<]+)</td>",
            html,
            flags=re.I | re.S,
        ):
            codes.append(row[0].strip())
            names.append(re.sub(r"\s+", "", row[1]))

        if not any([name, resume, company, codes]):
            raise ValueError("manager_html_empty")

        return FundManagerProfile(
            mgr_id=mgr_id,
            name=name,
            company=company,
            resume=resume,
            experience_years=experience,
            managed_fund_codes=codes,
            managed_fund_names=names,
            detail={"source": "eastmoney_html", "url": url},
            fetched_at=datetime.now(timezone.utc),
        )

    def _mobile_json(self, fund_code: str, path: str, **params: str) -> dict:
        base = {
            "deviceid": "WAP",
            "plat": "WAP",
            "product": "EFund",
            "version": "2.0.0",
        }
        base.update(params)
        url = get_endpoint("eastmoney_fund_mobapi_template", path=path)
        with self._client(fund_code) as client:
            r = client.get(url, params=base)
            r.raise_for_status()
            return r.json()

    def fetch_period_increase(self, fund_code: str) -> list[FundPeriodReturn]:
        """阶段涨幅（近1周/1月/3月…）— 对齐支付宝历史业绩表。"""
        payload = self._mobile_json(
            fund_code, "FundMNPeriodIncrease", FCODE=fund_code
        )
        rows = payload.get("Datas") or []
        if isinstance(rows, dict):
            rows = [rows]
        return _parse_period_increase(rows)

    def fetch_detail_information(self, fund_code: str) -> dict:
        payload = self._mobile_json(
            fund_code, "FundMNDetailInformation", FCODE=fund_code
        )
        data = payload.get("Datas") or {}
        return data if isinstance(data, dict) else {}

    def fetch_trading_rules(self, fund_code: str) -> FundTradingRules:
        detail = self.fetch_detail_information(fund_code)
        purchase = None
        redeem = None
        min_buy = None
        sub_fee = None
        try:
            basic = self._mobile_json(
                fund_code, "FundMNNBasicInformation", FCODE=fund_code
            )
            b = basic.get("Datas") or {}
            if isinstance(b, list) and b:
                b = b[0]
            if isinstance(b, dict):
                purchase = b.get("SGZT") or b.get("ISBUY")
                redeem = b.get("SHZT")
                min_buy = b.get("MINSG") or b.get("MINRG")
                sub_fee = b.get("RATE") or b.get("SOURCERATE")
        except Exception as exc:
            logger.debug("FundMNNBasicInformation %s: %s", fund_code, exc)
        notes: list[str] = []
        if detail.get("INVTGT"):
            notes.append(str(detail["INVTGT"])[:200])
        return FundTradingRules(
            fund_code=fund_code,
            purchase_status=_str_or_none(purchase),
            redeem_status=_str_or_none(redeem),
            min_purchase=_str_or_none(min_buy),
            management_fee=detail.get("MGREXP"),
            custody_fee=detail.get("TRUSTEXP"),
            sales_fee=detail.get("SALESEXP"),
            performance_benchmark=detail.get("PERFCMP") or detail.get("BENCH"),
            subscription_fee=_str_or_none(sub_fee),
            redemption_fee=None,
            dca_supported=None,
            trade_notes="；".join(notes) if notes else None,
            detail={**detail, "basic_purchase": purchase, "basic_redeem": redeem},
        )

    def fetch_holdings(self, fund_code: str) -> FundHoldingsSnapshot:
        url = get_endpoint("eastmoney_fund_archives")
        params = {
            "type": "jjcc",
            "code": fund_code,
            "topline": "10",
            "year": "",
            "month": "",
        }
        with self._client(fund_code) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            text = r.text
        report_date, holdings = _parse_holdings_archives(text)
        return FundHoldingsSnapshot(
            fund_code=fund_code,
            report_date=report_date,
            holdings=holdings,
        )


_PERIOD_TITLE_MAP = {
    "Z": ("1w", "近1周"),
    "Y": ("1m", "近1月"),
    "3Y": ("3m", "近3月"),
    "6Y": ("6m", "近6月"),
    "1N": ("1y", "近1年"),
    "2N": ("2y", "近2年"),
    "3N": ("3y", "近3年"),
    "5N": ("5y", "近5年"),
    "JN": ("ytd", "今年以来"),
    "LN": ("si", "成立以来"),
}


def _manager_detail_usable(info: dict) -> bool:
    return bool(
        info.get("MGRNAME")
        or info.get("RESUME")
        or info.get("FCODE")
        or info.get("SHORTNAME")
    )


def _str_or_none(val: object) -> str | None:
    if val is None or val == "" or val == "--":
        return None
    return str(val)


def _strip_html(cell: str) -> str:
    t = re.sub(r"<[^>]+>", "", cell)
    t = t.replace("&nbsp;", " ").strip()
    return t


def _parse_holdings_archives(text: str) -> tuple[str | None, list[FundHoldingRow]]:
    report_date: str | None = None
    m_date = re.search(r"(\d{4}-\d{2}-\d{2})", text[:800])
    if m_date:
        report_date = m_date.group(1)
    content = ""
    m_content = re.search(r'content:"((?:\\.|[^"\\])*)"', text)
    if m_content:
        raw = m_content.group(1)
        try:
            content = json.loads(f'"{raw}"')
        except json.JSONDecodeError:
            content = raw.replace("\\/", "/").replace('\\"', '"')
    else:
        m_alt = re.search(r"content:\s*'([^']*)'", text)
        if m_alt:
            content = m_alt.group(1)
    if not content:
        return report_date, []
    holdings: list[FundHoldingRow] = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", content, flags=re.I | re.S):
        cells = [
            _strip_html(c)
            for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.I | re.S)
        ]
        if len(cells) < 3:
            continue
        if cells[0] in ("序号", "") or "股票" in cells[0]:
            continue
        # 常见列：序号 代码 名称 占比 …
        sym = cells[1] if len(cells) > 1 else ""
        name = cells[2] if len(cells) > 2 else cells[0]
        weight_raw = cells[3] if len(cells) > 3 else ""
        change_raw = cells[4] if len(cells) > 4 else ""
        if not name or name == "--":
            continue
        weight = _parse_float_maybe_percent(weight_raw)
        change = _parse_float_maybe_percent(change_raw)
        holdings.append(
            FundHoldingRow(
                symbol=sym if sym and sym != "--" else None,
                name=name,
                weight_pct=weight,
                change_pct=change,
            )
        )
    return report_date, holdings[:20]


def _parse_period_increase(rows: list) -> list[FundPeriodReturn]:
    out: list[FundPeriodReturn] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "")
        pid, label = _PERIOD_TITLE_MAP.get(title, (title.lower(), title))
        if title and title not in _PERIOD_TITLE_MAP:
            for key, (p, lbl) in _PERIOD_TITLE_MAP.items():
                if lbl in title or title.endswith(key):
                    pid, label = p, lbl
                    break
            else:
                label = title
                pid = title
        out.append(
            FundPeriodReturn(
                period_id=pid,
                label=label,
                return_pct=_parse_float_maybe_percent(row.get("syl")),
                peer_avg_pct=_parse_float_maybe_percent(row.get("avg")),
                benchmark_pct=_parse_float_maybe_percent(row.get("hs300")),
                rank=str(row.get("rank")) if row.get("rank") not in (None, "") else None,
                peer_count=str(row.get("sc")) if row.get("sc") not in (None, "") else None,
            )
        )
    return out


def _split_csv_field(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [p.strip() for p in str(raw).split(",") if p.strip()]


def _parse_float_maybe_percent(val: object) -> float | None:
    if val is None or val == "" or val == "--":
        return None
    try:
        return float(str(val).replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def _parse_manager_list_rows(
    fund_code: str,
    rows: list,
    *,
    current_only: bool,
) -> list[FundManagerOnFund]:
    out: list[FundManagerOnFund] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        ids = _split_csv_field(row.get("MGRID"))
        names = _split_csv_field(row.get("MGRNAME"))
        offices = _split_csv_field(row.get("ISINOFFICE"))
        starts = _split_csv_field(row.get("FEMPDATE"))
        ends = _split_csv_field(row.get("LEMPDATE"))
        days = _split_csv_field(row.get("DAYS"))
        returns = _split_csv_field(row.get("PENAVGROWTH"))
        n = max(len(ids), 1)
        for i in range(n):
            mgr_id = ids[i] if i < len(ids) else ""
            if not mgr_id or mgr_id in seen:
                continue
            is_current = True
            if offices:
                is_current = (offices[i] if i < len(offices) else "1") == "1"
            end_raw = ends[i] if i < len(ends) else None
            if end_raw and end_raw not in ("--", "-", ""):
                is_current = False
            if current_only and not is_current:
                continue
            seen.add(mgr_id)
            tenure_days = None
            if i < len(days) and days[i].isdigit():
                tenure_days = int(days[i])
            out.append(
                FundManagerOnFund(
                    mgr_id=mgr_id,
                    name=names[i] if i < len(names) else None,
                    fund_code=row.get("FCODE") or fund_code,
                    start_date=starts[i] if i < len(starts) else None,
                    end_date=end_raw if end_raw and end_raw != "--" else None,
                    tenure_days=tenure_days,
                    tenure_return_pct=_parse_float_maybe_percent(
                        returns[i] if i < len(returns) else None
                    ),
                    is_current=is_current,
                )
            )
    return out


def _parse_manager_detail(mgr_id: str, info: dict) -> FundManagerProfile:
    codes = _split_csv_field(
        info.get("FCODES") or info.get("FCODE") or info.get("MFCODE")
    )
    names = _split_csv_field(info.get("SHORTNAME") or info.get("MFSHORTNAME"))
    resume = (
        info.get("RESUME")
        or info.get("JJJL")
        or info.get("MGRID_INTRO")
        or info.get("PENAVGROWTHINTRO")
    )
    if resume:
        resume = str(resume).strip() or None
    return FundManagerProfile(
        mgr_id=mgr_id,
        name=info.get("MGRNAME") or info.get("NAME"),
        company=info.get("COMPNAME") or info.get("JJGS") or info.get("COMPANY"),
        resume=resume,
        photo_url=info.get("NEWPHOTOURL") or info.get("PHOTOURL"),
        experience_years=(
            str(info.get("EXPERIENCE") or info.get("LGEAR") or "")
            or None
        ),
        managed_fund_codes=codes,
        managed_fund_names=names,
        detail=info,
        fetched_at=datetime.now(timezone.utc),
    )
