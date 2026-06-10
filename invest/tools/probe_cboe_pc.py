from invest.http_client import make_httpx_client
import re

u = "https://www.cboe.com/us/options/market_statistics/historical_data/"
html = make_httpx_client().get(u).text
for m in re.finditer(r"https?://[^\s\"'<>]+\.(?:csv|zip|xls)", html, re.I):
    print(m.group(0)[:150])
for m in re.finditer(r"/[^\s\"'<>]+\.(?:csv|zip)", html, re.I):
    s = m.group(0)
    if "put" in s.lower() or "pc" in s.lower() or "ratio" in s.lower() or "total" in s.lower():
        print("rel", s[:120])
