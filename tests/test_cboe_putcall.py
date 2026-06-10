from datetime import date

from invest.data.providers.cboe_putcall_provider import _parse_pc_csv, _parse_ratios


def test_parse_totalpc_csv_sample():
    text = """Volume disclaimer
DATE,CALLS,PUTS,TOTAL,P/C Ratio
11/1/2006,1401036,1271445,2672481,0.91
11/2/2006,1348240,1218592,2566832,0.9
"""
    pts = _parse_pc_csv(text, ("P/C Ratio",))
    assert len(pts) == 2
    assert pts[0].trade_date.year == 2006
    assert abs(pts[0].value - 0.91) < 1e-6


def test_parse_pc_ratio_archive_sample():
    text = """Cboe PUT/CALL RATIO ARCHIVE
DATE,TOTAL VOLUME P/C RATIO,INDEX P/C RATIO,EQUITY P/C RATIO
9/27/1995,0.79,,,
9/28/1995,0.61,,,
"""
    pts = _parse_pc_csv(text, ("TOTAL VOLUME P/C RATIO",))
    assert len(pts) == 2
    assert pts[0].trade_date == date(1995, 9, 27)


def test_parse_ratios_from_html():
    html = '{"name":"TOTAL PUT/CALL RATIO","value":"0.82"}'
    ratios = _parse_ratios(html)
    assert ratios["TOTAL PUT/CALL RATIO"] == 0.82
