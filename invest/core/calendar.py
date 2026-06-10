from __future__ import annotations

from datetime import date, timedelta  # noqa: I001

import numpy as np
import pandas as pd

from invest.config_loader import load_yaml

Frequency = str  # DAILY | WEEKLY | BIWEEKLY | MONTHLY | BIMONTHLY

DCA_FREQUENCIES = ("DAILY", "WEEKLY", "BIWEEKLY", "MONTHLY")


def dca_weekday_for_frequency(frequency: Frequency) -> int:
    """配置 1=周一…5=周五 → Python weekday 0=周一。"""
    defaults = load_yaml("dca_defaults.yaml").get("dca", {})
    raw = defaults.get("frequencies", {}).get(frequency.upper(), {}).get("weekday_default", 5)
    wd = int(raw)
    if wd >= 1:
        return wd - 1
    return wd


def is_dca_day(
    check_date: date,
    frequency: Frequency,
    *,
    weekday: int = 4,
    anchor_date: date | None = None,
    nth_trading_day: int = 1,
) -> bool:
    """
    判断是否定投日（简化：按自然日/周/月；交易日历细化可后续接入）。
    weekday: 0=周一 … 4=周五
    """
    freq = frequency.upper()
    if freq == "DAILY":
        return check_date.weekday() < 5
    if freq == "WEEKLY":
        return check_date.weekday() == weekday
    if freq == "BIWEEKLY":
        anchor = anchor_date or date(2020, 1, 3)
        if check_date.weekday() != weekday:
            return False
        weeks = (check_date - anchor).days // 7
        return weeks % 2 == 0
    if freq == "MONTHLY":
        return check_date.day <= nth_trading_day + 4 and check_date.day >= nth_trading_day
    if freq == "BIMONTHLY":
        anchor = anchor_date or date(2020, 1, 1)
        months_diff = (check_date.year - anchor.year) * 12 + (check_date.month - anchor.month)
        if months_diff % 2 != 0:
            return False
        return nth_trading_day <= check_date.day <= nth_trading_day + 4
    return False


def trading_dca_mask(
    dates: pd.DatetimeIndex,
    frequency: Frequency,
    *,
    weekday: int | None = None,
    anchor_date: date | None = None,
) -> np.ndarray:
    """
    在真实交易日序列上标记定投日（每期至多一个交易日）。
    WEEKLY/BIWEEKLY：优先选目标星期几，否则取该 ISO 周最后一个交易日。
    MONTHLY：每月第一个交易日。
    """
    idx = pd.DatetimeIndex(pd.to_datetime(dates))
    n = len(idx)
    mask = np.zeros(n, dtype=bool)
    if n == 0:
        return mask

    freq = frequency.upper()
    if freq == "DAILY":
        mask[:] = True
        return mask

    wd = weekday if weekday is not None else dca_weekday_for_frequency(freq)

    if freq == "WEEKLY":
        ic = idx.isocalendar()
        df = pd.DataFrame(
            {
                "pos": np.arange(n),
                "year": ic.year.to_numpy(dtype=int),
                "week": ic.week.to_numpy(dtype=int),
                "wd": idx.weekday,
            }
        )
        for _, g in df.groupby(["year", "week"], sort=False):
            preferred = g[g["wd"] == wd]
            pick = int(preferred.iloc[-1]["pos"] if len(preferred) else g.iloc[-1]["pos"])
            mask[pick] = True
        return mask

    if freq == "BIWEEKLY":
        weekly = trading_dca_mask(idx, "WEEKLY", weekday=wd, anchor_date=anchor_date)
        anchor = anchor_date or idx[0].date()
        for i in range(n):
            if not weekly[i]:
                continue
            weeks = (idx[i].date() - anchor).days // 7
            if weeks % 2 == 0:
                mask[i] = True
        return mask

    if freq == "MONTHLY":
        periods = idx.to_period("M")
        seen: set = set()
        for i, p in enumerate(periods):
            if p not in seen:
                seen.add(p)
                mask[i] = True
        return mask

    return mask


def next_dca_date(
    after: date,
    frequency: Frequency,
    weekday: int = 4,
    anchor_date: date | None = None,
    max_scan_days: int = 370,
) -> date | None:
    d = after + timedelta(days=1)
    for _ in range(max_scan_days):
        if is_dca_day(d, frequency, weekday=weekday, anchor_date=anchor_date):
            return d
        d += timedelta(days=1)
    return None
