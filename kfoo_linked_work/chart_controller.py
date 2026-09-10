from __future__ import annotations
import os, re
from dataclasses import dataclass
try:
    from playwright.sync_api import sync_playwright
except Exception:
    sync_playwright = None

TIMEFRAME_KEYS={"1m":"1","3m":"3","5m":"5","15m":"15","30m":"30","45m":"45","1h":"60","2h":"120","4h":"240","6h":"360","12h":"720","1d":"D","1w":"W"}

@dataclass
class ChartState:
    connected: bool=False; title: str=""; url: str=""; timeframe: str|None=None; symbol: str|None=None; verified: bool=False; reason: str=""

class ChartController:
    def __init__(self, cdp_url=None, chart_point=(700,450), verify_delay=0.8):
        self.cdp_url=cdp_url or os.getenv("TRADINGVIEW_CDP_URL","http://127.0.0.1:9222"); self.chart_point=tuple(chart_point); self.verify_delay=float(verify_delay)
        self._pw=None; self._browser=None; self.page=None

    def connect(self)->ChartState:
        if sync_playwright is None: return ChartState(reason="PLAYWRIGHT_NOT_INSTALLED")
        try:
            self._pw=sync_playwright().start(); self._browser=self._pw.chromium.connect_over_cdp(self.cdp_url)
            pages=[p for c in self._browser.contexts for p in c.pages]; tv=[p for p in pages if "tradingview.com" in (p.url or "").lower()]
            if not tv: return ChartState(reason="TRADINGVIEW_PAGE_NOT_FOUND")
            self.page=tv[0]; return self.state()
        except Exception as exc: return ChartState(reason=f"CDP_CONNECT_FAILED:{type(exc).__name__}:{exc}")

    def state(self)->ChartState:
        if self.page is None: return ChartState(reason="NOT_CONNECTED")
        try:
            title=self.page.title(); url=self.page.url; tf=self._timeframe_from_title(title); symbol=self._symbol_from_title(title)
            return ChartState(True,title,url,tf,symbol,bool(tf or symbol),"TITLE_READ")
        except Exception as exc: return ChartState(reason=f"STATE_READ_FAILED:{type(exc).__name__}:{exc}")

    def read_chart(self):
        """Return the Playwright reader result without changing chart state."""
        from playwright_chart_reader import PlaywrightChartReader
        reader=PlaywrightChartReader(self.cdp_url); result=reader.connect()
        if result.connected: result.screenshot_path=reader.capture()
        reader.close(); return result

    @staticmethod
    def _timeframe_from_title(title):
        t=(title or '').lower()
        for tf in ("1w","1d","12h","6h","4h","2h","1h","45m","30m","15m","5m","3m","1m"):
            if re.search(rf"\b{re.escape(tf)}\b",t): return tf
        return None

    @staticmethod
    def _symbol_from_title(title):
        m=re.search(r"\b([A-Z]{2,10})[/:-]([A-Z]{2,10})\b",(title or '').upper()); return f"{m.group(1)}/{m.group(2)}" if m else None

    def set_timeframe(self, timeframe):
        if timeframe not in TIMEFRAME_KEYS: raise ValueError(f"unsupported_timeframe:{timeframe}")
        if self.page is None: raise RuntimeError("NOT_CONNECTED")
        raise NotImplementedError("CHART_ONLY_ACTION_REQUIRES_VERIFIED_ADAPTER")
