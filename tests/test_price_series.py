import pandas as pd

from invest.core.price_series import _nav_df_to_close_df


def test_nav_df_to_close_df():
    nav = pd.DataFrame(
        {
            "nav_date": ["2024-01-02", "2024-01-03", "2024-01-04"],
            "nav": [1.0, 1.05, 1.1],
        }
    )
    out = _nav_df_to_close_df(nav)
    assert list(out.columns) == ["trade_date", "close"]
    assert out.iloc[0]["close"] == 1.0
    assert out.iloc[-1]["close"] == 1.1


def test_nav_df_skips_invalid_rows():
    nav = pd.DataFrame(
        {
            "nav_date": ["2024-01-02", "2024-01-03"],
            "nav": [0.0, None],
        }
    )
    assert _nav_df_to_close_df(nav).empty
