from __future__ import annotations
import os, re
from dataclasses import asdict, dataclass
from pathlib import Path
try:
    from playwright.sync_api import sync_playwright
except Exception:
    sync_playwright=None

@dataclass
class ChartRead:
    connected: bool=False; verified: bool=False; source:str="none"; url:str=""; title:str=""
    symbol:str|None=None; timeframe:str|None=None; visible_text:str=""; screenshot_path:str|None=None
    candles_available:bool=False; candles:list[dict[str,float]]|None=None; reason:str=""
    diagnostics:dict|None=None
    plot_rect:tuple[int,int,int,int]|None=None
    def to_dict(self): return asdict(self)

class PlaywrightChartReader:
    """Read-only TradingView CDP reader. Never navigates, clicks, changes TF, or trades."""
    def __init__(self,cdp_url=None,screenshot_dir="artifacts/chart"):
        self.cdp_url=cdp_url or os.getenv("TRADINGVIEW_CDP_URL","http://127.0.0.1:9222")
        self.screenshot_dir=Path(screenshot_dir); self._pw=None; self._browser=None; self.page=None
    def connect(self):
        if sync_playwright is None:return ChartRead(reason="PLAYWRIGHT_NOT_INSTALLED")
        try:
            self._pw=sync_playwright().start(); self._browser=self._pw.chromium.connect_over_cdp(self.cdp_url)
            pages=[p for c in self._browser.contexts for p in c.pages]; tv=[p for p in pages if "tradingview.com" in (p.url or "").lower()]
            if not tv:return ChartRead(reason="TRADINGVIEW_PAGE_NOT_FOUND")
            self.page=tv[0]; return self.read()
        except Exception as exc:return ChartRead(reason=f"CDP_CONNECT_FAILED:{type(exc).__name__}:{exc}")
    def read(self):
        if self.page is None:return ChartRead(reason="NOT_CONNECTED")
        try:
            title=self.page.title(); url=self.page.url; text=self.page.locator("body").inner_text(timeout=1500)[:20000]
            symbol,timeframe=self._parse_metadata(title,text,self.page)
            candles=self._read_verified_candles(); plot=self._read_plot_rect()
            verified=bool(symbol and timeframe)
            reason="VERIFIED_CANDLES_READ" if candles else ("IDENTITY_VERIFIED" if verified else "IDENTITY_NOT_VERIFIED")
            return ChartRead(True,verified,"playwright_dom" if verified else "playwright",url,title,symbol,timeframe,text,None,bool(candles),candles,reason,None,plot)
        except Exception as exc:return ChartRead(reason=f"READ_FAILED:{type(exc).__name__}:{exc}")
    def _read_plot_rect(self):
        try:
            return self.page.evaluate("""() => {
              const els=[...document.querySelectorAll('canvas')].filter(n=>{const r=n.getBoundingClientRect();return r.width>300&&r.height>200});
              if(!els.length)return null;
              els.sort((a,b)=>b.getBoundingClientRect().width*b.getBoundingClientRect().height-a.getBoundingClientRect().width*a.getBoundingClientRect().height);
              const r=els[0].getBoundingClientRect(); return [Math.round(r.x),Math.round(r.y),Math.round(r.right),Math.round(r.bottom)];
            }""")
        except Exception:return None
    def capture(self,name="tradingview_live.png"):
        if self.page is None:return None
        self.screenshot_dir.mkdir(parents=True,exist_ok=True); path=self.screenshot_dir/name
        self.page.screenshot(path=str(path),full_page=False); return str(path)
    def _read_verified_candles(self):
        try:
            raw=self.page.evaluate("() => window.__GOLDBOT_CANDLES__ || null")
            if not isinstance(raw,list) or len(raw)<9:return None
            out=[]
            for row in raw:
                if not isinstance(row,dict):return None
                item={k:float(row[k]) for k in ("open","high","low","close")}
                if "time" in row:item["time"]=float(row["time"])
                out.append(item)
            return out
        except Exception:return None
    @staticmethod
    def _normalize_timeframe(value):
        if not value:return None
        s=" ".join(str(value).strip().split()); m=re.fullmatch(r"(1m|3m|5m|15m|30m|45m|1h|2h|4h|6h|12h|1d|1w)",s,re.I)
        if m:return m.group(1).lower()
        m=re.fullmatch(r"(1|3|5|15|30|45)\s*(?:m|min|mins|minute|minutes)",s,re.I)
        if m:return m.group(1)+"m"
        m=re.fullmatch(r"(1|2|4|6|12)\s*(?:h|hr|hrs|hour|hours)",s,re.I)
        return m.group(1)+"h" if m else None
    @staticmethod
    def _parse_metadata(title,text,page=None):
        symbol,timeframe=PlaywrightChartReader._parse_title(title); u=(text or "").upper()
        if symbol is None:
            if re.search(r"\bXAU\s*/?\s*USD\b|\bXAUUSD\b",u) or "GOLD SPOT / U.S. DOLLAR" in u:symbol="XAU/USD"
            else:
                m=re.search(r"\b([A-Z]{2,12}(?:USDT|USD|USDC)\.P)\b",u); symbol=m.group(1) if m else ("NEARUSDT.P" if "NEAR / TETHERUS PERPETUAL CONTRACT" in u else None)
        if timeframe is None and page is not None:timeframe=PlaywrightChartReader._read_selected_timeframe(page)
        return symbol,timeframe
    @staticmethod
    def _read_selected_timeframe(page):
        try:
            r=page.evaluate("""() => [...document.querySelectorAll('button,[role="button"],[role="tab"]')].filter(n=>n.offsetParent).map(n=>({t:(n.textContent||'').trim(),a:n.getAttribute('aria-label'),p:n.getAttribute('aria-pressed'),s:n.getAttribute('aria-selected'),c:typeof n.className==='string'?n.className:''})).map(x=>{const v=[x.a,x.t].find(v=>/^(1|3|5|15|30|45)\s*(m|min|minute|minutes)?$/i.test((v||'').trim()));return v?{...x,v}:null}).filter(Boolean)""")
            selected=[x for x in (r or []) if x["p"]=="true" or x["s"]=="true" or re.search(r"selected|active",x["c"],re.I)]
            vals={self._normalize_timeframe(x["v"]) for x in selected if self._normalize_timeframe(x["v"])}
            return next(iter(vals)) if len(vals)==1 else None
        except Exception:return None
    @staticmethod
    def _parse_title(title):
        u=(title or "").upper(); tf=re.search(r"(?<![A-Z0-9])(1|3|5|15|30|45)\s*(?:M|MIN|MINS|MINUTE|MINUTES)(?![A-Z0-9])",u)
        t=(tf.group(1)+"m") if tf else None
        m=re.search(r"\b([A-Z]{2,12}(?:USDT|USD|USDC)\.P)\b",u)
        if m:return m.group(1),t
        if re.search(r"\bXAU\s*/?\s*USD\b|\bXAUUSD\b",u):return "XAU/USD",t
        m=re.search(r"\b([A-Z]{2,10})\s*/\s*([A-Z]{2,10})\b",u)
        return (f"{m.group(1)}/{m.group(2)}",t) if m else (None,None)
    def close(self):
        try:
            if self._pw:self._pw.stop()
        finally:self._pw=None;self._browser=None;self.page=None
