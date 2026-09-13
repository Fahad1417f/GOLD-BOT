"""Safe live-capture bridge for GOLD Vision Agent.

Attaches to an already-running Chromium/TradingView session through CDP.
Read-only: no navigation, clicks, timeframe changes, orders, or broker calls.
"""
from __future__ import annotations
import json
import os
from playwright_chart_reader import PlaywrightChartReader

def capture_once(cdp_url: str | None = None, output_dir: str = "artifacts/vision") -> dict:
    reader = PlaywrightChartReader(cdp_url=cdp_url, screenshot_dir=output_dir)
    try:
        result = reader.connect()
        if not result.connected:
            return result.to_dict()
        result.screenshot_path = reader.capture("tradingview_live.png")
        data = result.to_dict()
        data["capture_verified"] = bool(result.connected and result.symbol and result.timeframe and result.screenshot_path)
        return data
    finally:
        reader.close()

if __name__ == "__main__":
    data = capture_once(os.getenv("TRADINGVIEW_CDP_URL"))
    print(json.dumps(data, ensure_ascii=False, indent=2))
    raise SystemExit(0 if data.get("capture_verified") else 2)
