import pandas as pd
import pytest

from invest.core.lump_sum_calc import compute_lump_sum_return, lump_sum_meta


def _ohlcv(closes: list[float], start: str = "2020-01-01") -> pd.DataFrame:
    idx = pd.date_range(start, periods=len(closes), freq="B")
    return pd.DataFrame({"trade_date": idx, "close": closes})


def test_lump_sum_return_basic():
    df = _ohlcv([100.0, 110.0, 120.0, 150.0])
    out = compute_lump_sum_return(df, "2020-01-01", 1000.0)
    assert out["buy_date"] == "2020-01-01"
    assert out["final_value"] == 1500.0
    assert out["return_pct"] == 50.0
    assert out["profit"] == 500.0


def test_lump_sum_snap_to_trading_day():
    df = _ohlcv([100.0, 150.0], start="2020-01-02")
    out = compute_lump_sum_return(df, "2020-01-01", 100.0)
    assert out["date_snapped"] is True
    assert out["buy_price"] == 100.0


def test_lump_sum_meta():
    df = _ohlcv([100.0, 120.0])
    meta = lump_sum_meta(df)
    assert meta["latest_price"] == 120.0
    assert "data_start" in meta


def test_lump_sum_invalid_amount():
    df = _ohlcv([100.0, 120.0])
    with pytest.raises(ValueError, match="invalid_amount"):
        compute_lump_sum_return(df, "2020-01-01", 0)
