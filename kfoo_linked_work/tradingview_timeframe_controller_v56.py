from __future__ import annotations

"""V56 read-only TradingView timeframe controller.

Owns one CDP/Playwright session for the dedicated TradingView tab, changes
only the interval, verifies the interval after every change, and publishes
controller state for the analysis process.
"""

import json
import os
import time
from pathlib import Path

from chart_controller import ChartController

REQUIRED_TFS = ("4h", "1h", "15m", "5m", "3m")
CDP_URL = os.getenv("TRADINGVIEW_CDP_URL", "http://127.0.0.1:9222")
HOLD_SECONDS = float(os.getenv("GOLDBOT_TF_HOLD_SECONDS", "18"))
STATE_FILE = Path(os.getenv("GOLDBOT_TF_STATE_FILE", "tradingview_timeframe_state.json"))
PAGE_URL = os.getenv("GOLDBOT_TRADINGVIEW_PAGE", "https://ar.tradingview.com/chart/T2r9HHsB/")


def _state(tf: str, status: str, detail: str = "") -> None:
    STATE_FILE.write_text(
        json.dumps(
            {"active_timeframe": tf, "status": status, "detail": detail, "updated": time.time()},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def run_forever() -> None:
    controller = ChartController(CDP_URL)
    state = controller.connect()
    if not state.connected:
        _state("none", "error", state.reason)
        raise RuntimeError(state.reason)

    if PAGE_URL and "tradingview.com/chart/" not in state.url:
        _state("none", "error", "TRADINGVIEW_TARGET_PAGE_NOT_MATCHED")
        raise RuntimeError("TRADINGVIEW_TARGET_PAGE_NOT_MATCHED")

    print(f"TRADINGVIEW_TARGET={state.url}", flush=True)
    print(f"TRADINGVIEW_SYMBOL={state.symbol or 'UNKNOWN'}", flush=True)

    try:
        while True:
            for tf in REQUIRED_TFS:
                _state(tf, "switching")
                verified = controller.set_timeframe(tf)
                _state(tf, "active", verified.title)
                print(
                    f"TRADINGVIEW_TIMEFRAME_SET={tf} verified={verified.timeframe} "
                    f"symbol={verified.symbol or 'UNKNOWN'}",
                    flush=True,
                )
                time.sleep(HOLD_SECONDS)
    finally:
        if controller._pw is not None:
            controller._pw.stop()


if __name__ == "__main__":
    run_forever()
