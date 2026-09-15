from __future__ import annotations
import re, time, os
from dataclasses import asdict
from chart_controller import ChartController, TIMEFRAME_KEYS

class VerifiedChartController(ChartController):
    """Controlled TradingView UI adapter: every UI change is followed by verification."""

    def set_timeframe(self, timeframe):
        if timeframe not in TIMEFRAME_KEYS:
            raise ValueError(f"unsupported_timeframe:{timeframe}")
        if self.page is None:
            raise RuntimeError("NOT_CONNECTED")
        key = TIMEFRAME_KEYS[timeframe]
        # Try exact visible timeframe controls first; do not click arbitrary page elements.
        candidates = self.page.locator('button,[role="button"],[role="tab"]').filter(
            has_text=re.compile(rf"^\s*{re.escape(key)}\s*$", re.I)
        )
        count = candidates.count()
        clicked = False
        for i in range(min(count, 8)):
            el = candidates.nth(i)
            try:
                if el.is_visible():
                    el.click(timeout=1200)
                    clicked = True
                    break
            except Exception:
                pass
        if not clicked:
            # Fall back to TradingView's chart keyboard interval shortcut only if the
            # chart canvas is present; this avoids clicking unrelated page elements.
            canvas = self.page.locator("canvas").filter(visible=True)
            if canvas.count() == 0:
                raise RuntimeError("TIMEFRAME_CONTROL_NOT_FOUND")
            canvas.first.click(position={"x":20,"y":20}, timeout=1000)
            self.page.keyboard.press(key)
        deadline=time.time()+2.5
        last=None
        while time.time()<deadline:
            last=self.state()
            if last.timeframe==timeframe:
                return last
            time.sleep(0.15)
        raise RuntimeError(f"TIMEFRAME_VERIFY_FAILED:{timeframe}:observed={getattr(last,'timeframe',None)}")

    def select_symbol(self, display_symbol):
        if self.page is None:
            raise RuntimeError("NOT_CONNECTED")
        # Only use an identified TradingView symbol search control.
        controls=self.page.locator('input[placeholder*="Search" i],input[aria-label*="Search" i]')
        for i in range(min(controls.count(), 8)):
            el=controls.nth(i)
            try:
                if el.is_visible():
                    el.fill(display_symbol, timeout=1000)
                    self.page.keyboard.press("Enter")
                    time.sleep(0.8)
                    state=self.state()
                    if state.symbol and display_symbol.upper() in state.symbol.upper():
                        return state
            except Exception:
                continue
        raise RuntimeError("SYMBOL_SEARCH_CONTROL_NOT_VERIFIED")

    def scan_timeframes(self, timeframes=("4h","1h","15m","5m","3m")):
        results={}
        for tf in timeframes:
            st=self.set_timeframe(tf)
            results[tf]=asdict(st)
        return results
