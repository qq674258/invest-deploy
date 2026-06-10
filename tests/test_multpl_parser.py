from invest.data.providers.multpl_provider import _parse_monthly_table


def test_parse_monthly_table_shiller_sample():
    html = """
    <table><tr><th>Date</th><th>Value</th></tr>
    <tr><td>May 27, 2026</td><td>&#x2002;42.32</td></tr>
    <tr><td>Apr 1, 2026</td><td>38.93</td></tr>
    </table>
    """
    pts = _parse_monthly_table(html)
    assert len(pts) == 2
    assert abs(pts[-1].value - 38.93) < 1e-6
