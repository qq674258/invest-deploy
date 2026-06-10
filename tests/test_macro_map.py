from invest.config_loader import load_instruments
from invest.core.macro_map import resolve_macro_series_id


def test_resolve_earnings_yield_for_ndx():
    profiles = {p.instrument_id: p for p in load_instruments()}
    ndx = profiles["NDX"]
    assert resolve_macro_series_id(ndx, "earnings_yield") == "macro:ndx:earnings_yield"
    assert resolve_macro_series_id(ndx, "vix") == "macro:ndx:vix"
