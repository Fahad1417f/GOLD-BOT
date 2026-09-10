from __future__ import annotations

"""Read-only TradingView timeframe controller for GOLD-BOT V56.

Uses the already-open Chrome instance exposed through CDP. It changes only the
TradingView interval control and never submits orders or touches execution UI.
The controller cycles the required V56 frames in order and exposes the active
frame to the monitor through a small local state file.

Required frames:
  4h, 1h, 15m, 5m, 3m

The chart symbol/page is not changed. The user must leave the intended
TradingView chart open in the CDP-enabled Chrome instance.
"""

import json
import os
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


REQUIRED_TFS = ("4h", "1h", "15m", "5m", "3m")
CDP_URL = os.getenv("TRADINGVIEW_CDP_URL", "http://127.0.0.1:9222")
INTERVAL_HOLD_SECONDS = float(os.getenv("GOLDBOT_TF_HOLD_SECONDS", "18"))
STATE_FILE = Path(os.getenv("GOLDBOT_TF_STATE_FILE", "tradingview_timeframe_state.json"))


def _write_state(tf: str, status: str, detail: str = "") -> None:
    STATE_FILE.write_text(
        json.dumps(
            {"active_timeframe": tf, "status": status, "detail": detail, "updated": time.time()},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _find_page(browser):
    pages = [
        p
        for c in browser.contexts
        for p in c.pages
        if "tradingview.com" in (p.url or "").lower()
    ]
    if not pages:
        raise RuntimeError("TRADINGVIEW_PAGE_NOT_FOUND")
    return pages[0]


def _set_interval(page, tf: str) -> None:
    # TradingView supports keyboard interval entry when the chart has focus.
    # We first focus the chart, then use the interval shortcut. No navigation,
    # order entry, or other UI action is performed.
    page.mouse.click(700, 450)
    page.keyboard.press("Escape")
    page.keyboard.press("0")
    page.keyboard.type(tf)
    page.keyboard.press("Enter")


def run_forever() -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(CDP_URL)
        page = _find_page(browser)
        if "tradingview.com" not in (page.url or "").lower():
            raise RuntimeError("TRADINGVIEW_PAGE_NOT_ACTIVE")

        while True:
            for tf in REQUIRED_TFS:
                _write_state(tf, "switching")
                _set_interval(page, tf)
                # Allow the TradingView toolbar/chart to settle before the
                # visual agent captures and analyzes this frame.
                time.sleep(2.5)
                _write_state(tf, "active")
                time.sleep(INTERVAL_HOLD_SECONDS)


if __name__ == "__main__":
    run_forever()
