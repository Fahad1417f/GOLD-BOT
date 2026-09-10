from __future__ import annotations

"""V56 read-only TradingView controller.

The controller owns the CDP-connected Playwright session and the selected
TradingView tab. It cycles the analysis frames in one process/thread and
publishes explicit controller state for the visual agent.
"""

import json
import os
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

REQUIRED_TFS = ("4h", "1h", "15m", "5m", "3m")
CDP_URL = os.getenv("TRADINGVIEW_CDP_URL", "http://127.0.0.1:9222")
HOLD_SECONDS = float(os.getenv("GOLDBOT_TF_HOLD_SECONDS", "18"))
SETTLE_SECONDS = float(os.getenv("GOLDBOT_TF_SETTLE_SECONDS", "2.5"))
STATE_FILE = Path(os.getenv("GOLDBOT_TF_STATE_FILE", "tradingview_timeframe_state.json"))
PAGE_URL = os.getenv("GOLDBOT_TRADINGVIEW_PAGE", "https://ar.tradingview.com/chart/T2r9HHsB/")


def _state(tf: str, status: str, detail: str = "") -> None:
    STATE_FILE.write_text(json.dumps({"active_timeframe": tf, "status": status, "detail": detail, "updated": time.time()}, ensure_ascii=False), encoding="utf-8")


def _find_page(browser):
    pages = [p for c in browser.contexts for p in c.pages if PAGE_URL.split("/chart/")[0] in (p.url or "") and "tradingview.com" in (p.url or "").lower()]
    if not pages:
        pages = [p for c in browser.contexts for p in c.pages if "tradingview.com" in (p.url or "").lower()]
    if not pages:
        raise RuntimeError("TRADINGVIEW_PAGE_NOT_FOUND")
    page = pages[0]
    if PAGE_URL and PAGE_URL not in page.url and "tradingview.com/chart/" not in page.url:
        raise RuntimeError("TRADINGVIEW_TARGET_PAGE_NOT_MATCHED")
    return page


def _set_interval(page, tf: str) -> None:
    # TradingView interval shortcut: focus chart, enter the interval, confirm.
    # Only timeframe is changed; no symbol/navigation/order controls are used.
    page.mouse.click(700, 450)
    page.keyboard.press("Escape")
    page.keyboard.press("0")
    page.keyboard.type(tf)
    page.keyboard.press("Enter")


def run_forever() -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(CDP_URL)
        page = _find_page(browser)
        _state("none", "connected", page.url)
        while True:
            for tf in REQUIRED_TFS:
                _state(tf, "switching")
                _set_interval(page, tf)
                time.sleep(SETTLE_SECONDS)
                _state(tf, "active")
                time.sleep(HOLD_SECONDS)


if __name__ == "__main__":
    run_forever()
