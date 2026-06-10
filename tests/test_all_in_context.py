import pandas as pd

from invest.core.all_in_context import _match_drawdown_tier, build_all_in_context


def test_match_drawdown_tier():
    assert _match_drawdown_tier(-0.02)[1] == "轻微回撤"
    assert _match_drawdown_tier(-0.08)[1] == "轻度回撤"
    assert _match_drawdown_tier(-0.15)[1] == "中度回撤"
    assert _match_drawdown_tier(-0.25)[1] == "深度回撤"
    assert _match_drawdown_tier(-0.40)[1] == "极端回撤"


class _FakeRepo:
    def __init__(self, macro: dict | None = None):
        self._macro = macro or {}

    def load_macro_series(self, series_ids, **kwargs):
        return {k: v for k, v in self._macro.items() if k in series_ids}


def test_build_all_in_context_drawdown():
    idx = pd.bdate_range("2020-01-01", periods=300)
    close = pd.Series(100.0, index=idx)
    close.iloc[200:] = 80.0
    ohlcv = pd.DataFrame({"trade_date": idx, "close": close.values})
    repo = _FakeRepo()
    out = build_all_in_context(
        repo,
        "NDX",
        ohlcv,
        idx[250].strftime("%Y-%m-%d"),
        idx[-1].strftime("%Y-%m-%d"),
    )
    dd = out["signals"]["drawdown"]
    assert dd["buy_pct"] is not None
    assert dd["buy_high"] is not None
    assert len(dd["tiers"]) == 5
    assert out["drawdown_window"] == "6m"
    assert out["drawdown_window_label"] == "近半年"
    assert "vix" not in out["signals"]


def test_build_all_in_context_only_drawdown_signal():
    idx = pd.bdate_range("2020-01-01", periods=300)
    close = pd.Series(100.0, index=idx)
    ohlcv = pd.DataFrame({"trade_date": idx, "close": close.values})
    out = build_all_in_context(
        _FakeRepo(),
        "NDX",
        ohlcv,
        idx[-1].strftime("%Y-%m-%d"),
        idx[-1].strftime("%Y-%m-%d"),
    )
    assert list(out["signals"].keys()) == ["drawdown"]
