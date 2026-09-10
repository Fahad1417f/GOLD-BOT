from __future__ import annotations

import json
import os
import sys

from playwright_chart_reader import PlaywrightChartReader
from tradingview_kfoo_dom_bridge_v56 import inspect_page


def main() -> int:
    reader = PlaywrightChartReader(os.getenv("TRADINGVIEW_CDP_URL", "http://127.0.0.1:9222"))
    chart = reader.connect()
    print(f"PAGE={'PASS' if chart.connected else 'FAIL'}")
    print(f"SYMBOL={chart.symbol}")
    print(f"TIMEFRAME={chart.timeframe}")
    if not chart.connected:
        print("KFOO_PROBE=FAIL PAGE_NOT_CONNECTED")
        return 2
    result = inspect_page(reader.page)
    print("KFOO_PROBE_SOURCE=" + result.get("source", "none"))
    if result.get("payload") is None:
        print("KFOO_PROBE=FAIL LIVE_PUBLISHER_NOT_FOUND")
        reader.close()
        return 3
    payload = result["payload"]
    print("KFOO_PROBE=FOUND")
    print(json.dumps(payload, ensure_ascii=False, indent=2)[:30000])
    reader.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
