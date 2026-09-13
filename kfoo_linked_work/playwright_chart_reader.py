from __future__ import annotations
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except Exception:
    sync_playwright = None

@dataclass
class ChartRead:
    connected: bool=False; verified: bool=False; source: str="none"; url: str=""; title: str=""
    symbol: str|None=None; timeframe: str|None=None; visible_text: str=""; screenshot_path: str|None=None
    candles_available: bool=False; candles: list[dict[str,float]]|None=None; reason: str=""
    diagnostics: dict|None=None
    def to_dict(self): return asdict(self)

class PlaywrightChartReader:
    """Read-only TradingView CDP reader. Never navigates, clicks, changes TF, or trades."""
    def __init__(self, cdp_url=None, screenshot_dir="artifacts/chart"):
        self.cdp_url=cdp_url or os.getenv("TRADINGVIEW_CDP_URL","http://127.0.0.1:9222")
        self.screenshot_dir=Path(screenshot_dir); self._pw=None; self._browser=None; self.page=None

    def connect(self):
        if sync_playwright is None: return ChartRead(reason="PLAYWRIGHT_NOT_INSTALLED")
        try:
            self._pw=sync_playwright().start()
            self._browser=self._pw.chromium.connect_over_cdp(self.cdp_url)
            pages=[p for c in self._browser.contexts for p in c.pages]
            tv=[p for p in pages if "tradingview.com" in (p.url or "").lower()]
            if not tv: return ChartRead(reason="TRADINGVIEW_PAGE_NOT_FOUND")
            self.page=tv[0]; return self.read()
        except Exception as exc: return ChartRead(reason=f"CDP_CONNECT_FAILED:{type(exc).__name__}:{exc}")

    def read(self):
        if self.page is None: return ChartRead(reason="NOT_CONNECTED")
        try:
            title=self.page.title(); url=self.page.url
            text=self.page.locator("body").inner_text(timeout=1500)[:20000]
            symbol,timeframe=self._parse_metadata(title,text,self.page)
            candles=self._read_verified_candles()
            diagnostics=None
            if timeframe is None:
                diagnostics=self._read_timeframe_diagnostics(self.page)
            verified=bool(symbol and timeframe)
            reason="VERIFIED_CANDLES_READ" if candles else ("IDENTITY_VERIFIED" if verified else "IDENTITY_NOT_VERIFIED")
            return ChartRead(connected=True,verified=verified,
                source="playwright_dom" if verified else "playwright",url=url,title=title,
                symbol=symbol,timeframe=timeframe,visible_text=text,candles_available=bool(candles),
                candles=candles,reason=reason,diagnostics=diagnostics)
        except Exception as exc: return ChartRead(reason=f"READ_FAILED:{type(exc).__name__}:{exc}")

    def capture(self,name="tradingview_live.png"):
        if self.page is None: return None
        self.screenshot_dir.mkdir(parents=True,exist_ok=True); path=self.screenshot_dir/name
        self.page.screenshot(path=str(path),full_page=False); return str(path)

    def _read_verified_candles(self):
        try:
            raw=self.page.evaluate("() => window.__GOLDBOT_CANDLES__ || null")
            if not isinstance(raw,list) or len(raw)<9: return None
            out=[]
            for row in raw:
                if not isinstance(row,dict): return None
                item={k:float(row[k]) for k in ("open","high","low","close")}
                if "time" in row: item["time"]=float(row["time"])
                out.append(item)
            return out
        except Exception: return None

    @staticmethod
    def _normalize_timeframe(value):
        if not value: return None
        s=" ".join(str(value).strip().split())
        m=re.fullmatch(r"(1m|3m|5m|15m|30m|45m|1h|2h|4h|6h|12h|1d|1w)",s,re.I)
        if m: return m.group(1).lower()
        m=re.fullmatch(r"(1|3|5|15|30|45)\s*(?:m|min|mins|minute|minutes)",s,re.I)
        if m: return f"{m.group(1)}m"
        m=re.fullmatch(r"(1|2|4|6|12)\s*(?:h|hr|hrs|hour|hours)",s,re.I)
        return f"{m.group(1)}h" if m else None

    @staticmethod
    def _parse_metadata(title,text,page=None):
        symbol,timeframe=PlaywrightChartReader._parse_title(title)
        body=text or ""; upper=body.upper()
        if symbol is None:
            if "GOLD SPOT / U.S. DOLLAR" in upper or "GOLD SPOT/U.S. DOLLAR" in upper or re.search(r"\bXAU\s*/?\s*USD\b|\bXAUUSD\b",upper):
                symbol="XAU/USD"
            else:
                m=re.search(r"\b([A-Z]{2,12}(?:USDT|USD|USDC)\.P)\b",upper)
                if m: symbol=m.group(1)
                elif "NEAR / TETHERUS PERPETUAL CONTRACT" in upper: symbol="NEARUSDT.P"
        if timeframe is None and page is not None: timeframe=PlaywrightChartReader._read_selected_timeframe(page)
        return symbol,timeframe

    @staticmethod
    def _read_selected_timeframe(page):
        try:
            result=page.evaluate(r"""() => {
              const normalize=v => { const s=(v||'').trim().replace(/\s+/g,' ');
                let m=s.match(/^(1m|3m|5m|15m|30m|45m|1h|2h|4h|6h|12h|1d|1w)$/i);
                if(m)return m[1].toLowerCase();
                m=s.match(/^(1|3|5|15|30|45)\s*(m|min|mins|minute|minutes)$/i); if(m)return m[1]+'m';
                m=s.match(/^(1|2|4|6|12)\s*(h|hr|hrs|hour|hours)$/i); if(m)return m[1]+'h'; return null; };
              const controls=[];
              for(const n of document.querySelectorAll('button,[role="button"],[role="tab"]')){
                if(n.offsetParent===null)continue; const r=n.getBoundingClientRect();
                if(!r.width||!r.height||r.y<0||r.y>180)continue;
                const attrs={dataValue:n.getAttribute('data-value')||'',dataKey:n.getAttribute('data-key')||'',
                  dataTimeframe:n.getAttribute('data-timeframe')||'',dataInterval:n.getAttribute('data-interval')||'',
                  dataResolution:n.getAttribute('data-resolution')||'',aria:n.getAttribute('aria-label')||'',
                  title:n.getAttribute('title')||'',text:(n.textContent||'').trim(),
                  ariaPressed:n.getAttribute('aria-pressed'),ariaSelected:n.getAttribute('aria-selected'),
                  dataState:n.getAttribute('data-state'),className:typeof n.className==='string'?n.className:''};
                for(const raw of Object.values(attrs).slice(0,7)){const tf=normalize(raw);if(tf){controls.push({tf,...attrs});break;}}
              }
              const metadata=[];
              for(const n of document.querySelectorAll('[data-timeframe],[data-interval],[data-resolution],meta[name="timeframe"],meta[name="chart-timeframe"]'))
                for(const raw of [n.getAttribute('data-timeframe'),n.getAttribute('data-interval'),n.getAttribute('data-resolution'),n.getAttribute('content')]){
                  const tf=normalize(raw);if(tf)metadata.push(tf);
                }
              return {controls,metadata:[...new Set(metadata)]};
            }""")
            controls=(result or {}).get("controls",[]); metadata=(result or {}).get("metadata",[])
            explicit=[]
            for x in controls:
                if x.get("ariaPressed")=="true" or x.get("ariaSelected")=="true" or str(x.get("dataState") or "").lower() in {"active","selected"} or re.search(r"(?:^|[\s_-])(selected|active|is-selected|isactive)(?:$|[\s_-])",str(x.get("className") or "").lower()):
                    explicit.append(x["tf"])
            if len(set(explicit))==1:return explicit[0]
            if len(set(explicit))>1:return None
            if len(set(metadata))==1:return metadata[0]
            compact=[x for x in controls if re.fullmatch(r"(?:1|3|5|15|30|45)",x.get("text","").strip()) or PlaywrightChartReader._normalize_timeframe(x.get("text"))]
            by_tf={}
            for x in compact: by_tf.setdefault(x["tf"],[]).append(x)
            return next(iter(by_tf)) if len(by_tf)==1 else None
        except Exception: return None

    @staticmethod
    def _read_timeframe_diagnostics(page):
        """Read-only forensic snapshot of visible timeframe controls; never clicks or mutates."""
        try:
            result=page.evaluate(r"""() => {
              const rows=[]; const visible=n=>{if(!n)return false; const r=n.getBoundingClientRect(); const s=getComputedStyle(n);
                return !!(r.width&&r.height&&r.y>=0&&r.y<=220&&s.visibility!=='hidden'&&s.display!=='none');};
              const push=n=>{if(!visible(n))return; const r=n.getBoundingClientRect();
                rows.push({tag:n.tagName,role:n.getAttribute('role'),text:(n.textContent||'').trim().slice(0,80),
                  aria:n.getAttribute('aria-label')||'',title:n.getAttribute('title')||'',
                  ariaPressed:n.getAttribute('aria-pressed'),ariaSelected:n.getAttribute('aria-selected'),
                  dataState:n.getAttribute('data-state'),dataValue:n.getAttribute('data-value')||'',
                  dataKey:n.getAttribute('data-key')||'',dataTimeframe:n.getAttribute('data-timeframe')||'',
                  dataInterval:n.getAttribute('data-interval')||'',dataResolution:n.getAttribute('data-resolution')||'',
                  className:typeof n.className==='string'?n.className:'',rect:{x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height)}})};
              for(const n of document.querySelectorAll('button,[role="button"],[role="tab"],[data-timeframe],[data-interval],[data-resolution]'))push(n);
              return {url:location.href,title:document.title,controls:rows.slice(0,120)};
            }""")
            return {"status":"TIMEFRAME_DIAGNOSTICS_COLLECTED","control_count":len((result or {}).get("controls",[])),"page":result}
        except Exception as exc:
            return {"status":"TIMEFRAME_DIAGNOSTICS_FAILED","error":f"{type(exc).__name__}:{exc}"}

    @staticmethod
    def _parse_title(title):
        u=(title or "").upper()
        m=re.search(r"\b([A-Z]{2,12}(?:USDT|USD|USDC)\.P)\b",u)
        if m:
            tf=re.search(r"(?<![A-Z0-9])(1|3|5|15|30|45)\s*(?:M|MIN|MINS|MINUTE|MINUTES)(?![A-Z0-9])",u)
            return m.group(1), (tf.group(1)+"m" if tf else None)
        if re.search(r"\bXAU\s*/?\s*USD\b|\bXAUUSD\b",u):
            tf=re.search(r"(?<![A-Z0-9])(1|3|5|15|30|45)\s*(?:M|MIN|MINS|MINUTE|MINUTES)(?![A-Z0-9])",u)
            return "XAU/USD", (tf.group(1)+"m" if tf else None)
        m=re.search(r"\b([A-Z]{2,10})\s*/\s*([A-Z]{2,10})\b",u)
        if m:
            tf=re.search(r"(?<![A-Z0-9])(1|3|5|15|30|45)\s*(?:M|MIN|MINS|MINUTE|MINUTES)(?![A-Z0-9])",u)
            return f"{m.group(1)}/{m.group(2)}", (tf.group(1)+"m" if tf else None)
        return None,None

    def close(self):
        try:
            if self._pw:self._pw.stop()
        finally:self._pw=None;self._browser=None;self.page=None
