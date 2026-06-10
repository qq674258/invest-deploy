import pandas as pd

from invest.core.chart_macro import _align_macro_to_dates, _yoy_monthly


def test_align_macro_to_dates_accepts_series_index():
    dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])
    macro = pd.Series([20.0, 21.0], index=pd.to_datetime(["2024-01-02", "2024-01-04"]))
    out = _align_macro_to_dates(macro, dates)
    assert len(out) == 3
    assert out.iloc[-1] == 21.0


def test_yoy_monthly():
    idx = pd.date_range("2020-01-01", periods=24, freq="MS")
    values = [100.0 + i * 0.5 for i in range(24)]
    s = pd.Series(values, index=idx)
    out = _yoy_monthly(s)
    assert out is not None
    assert out["value"] is not None
    assert out["unit"] == "%"
