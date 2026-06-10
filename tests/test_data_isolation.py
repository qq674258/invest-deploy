from invest.config_loader import (
    flatten_metric_ids,
    get_metrics_map,
    instruments_for_scoring,
    load_instruments,
)
from invest.core.macro_map import macro_series_map_for_metrics


def test_funds_excluded_from_scoring():
    scoring = instruments_for_scoring(["index_us", "cn_active_fund"])
    ids = {p.instrument_id for p in scoring}
    assert "NDX" in ids
    assert "SPX" in ids
    assert not any(p.instrument_id.startswith("FUND_") for p in scoring)


def test_ndx_spx_macro_series_disjoint():
    profiles = {p.instrument_id: p for p in load_instruments()}
    ndx_map = macro_series_map_for_metrics(
        profiles["NDX"], flatten_metric_ids(get_metrics_map(profiles["NDX"]))
    )
    spx_map = macro_series_map_for_metrics(
        profiles["SPX"], flatten_metric_ids(get_metrics_map(profiles["SPX"]))
    )
    ndx_series = set(ndx_map.values())
    spx_series = set(spx_map.values())
    assert not ndx_series & spx_series
    assert all(s.startswith("macro:ndx:") for s in ndx_series)
    assert all(s.startswith("macro:spx:") for s in spx_series)
