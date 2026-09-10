from __future__ import annotations

import json
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
    connected: bool = False
    verified: bool = False
    source: str = "none"
    url: str = ""
    title: str = ""
    symbol: str | None = None
    timeframe: str | None = None
    visible_text: str = ""
    screenshot_path: str | None = None
    candles_available: bool = False
    candles: list[dict[str, float]] | None = None
    reason: str = ""

    def to_dict(self):
        return asdict(self)


class PlaywrightChartReader:
    """Chart-only TradingView reader.

    Safety contract: attaches to an existing Chromium CDP session, does not
    navigate, switch tabs, click orders, or execute trades. Candle extraction
    is accepted only from an explicitly exposed/verified page provider; the
    reader never fabricates OHLC data from a screenshot.
    """

    def __init__(self, cdp_url: str | None = None, screenshot_dir: str = "artifacts/chart"):
        self.cdp_url = cdp_url or os.getenv("TRADINGVIEW_CDP_URL", "http://127.0.0.1:9222")
        self.screenshot_dir = Path(screenshot_dir)
        self._pw = None
        self._browser = None
        self.page = None

    def connect(self) -> ChartRead:
        if sync_playwright is None:
            return ChartRead(reason="PLAYWRIGHT_NOT_INSTALLED")
        try:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.connect_over_cdp(self.cdp_url)
            pages = [p for c in self._browser.contexts for p in c.pages]
            tv = [p for p in pages if "tradingview.com" in (p.url or "").lower()]
            if not tv:
                return ChartRead(reason="TRADINGVIEW_PAGE_NOT_FOUND")
            self.page = tv[0]
            return self.read()
        except Exception as exc:
            return ChartRead(reason=f"CDP_CONNECT_FAILED:{type(exc).__name__}:{exc}")

    def read(self) -> ChartRead:
        if self.page is None:
            return ChartRead(reason="NOT_CONNECTED")
        try:
            title = self.page.title()
            url = self.page.url
            text = self.page.locator("body").inner_text(timeout=1500)[:20000]
            symbol = self._parse_symbol(title, text)
            # IMPORTANT: title is not a reliable timeframe source. TradingView titles
            # and study labels can contain unrelated intervals (e.g. 1D/W). Resolve
            # the selected chart interval from the read-only toolbar/metadata first.
            timeframe = self._read_selected_timeframe(self.page)
            if timeframe is None:
                timeframe = self._parse_body_timeframe_only_if_unique(text)
            candles = self._read_verified_candles()
            return ChartRead(
                connected=True,
                verified=bool(symbol and timeframe),
                source="playwright_dom" if (symbol or timeframe) else "playwright",
                url=url,
                title=title,
                symbol=symbol,
                timeframe=timeframe,
                visible_text=text,
                candles_available=bool(candles),
                candles=candles,
                reason="DOM_METADATA_READ" if not candles else "VERIFIED_CANDLES_READ",
            )
        except Exception as exc:
            return ChartRead(reason=f"READ_FAILED:{type(exc).__name__}:{exc}")

    def capture(self, name: str = "tradingview.png") -> str | None:
        if self.page is None:
            return None
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        path = self.screenshot_dir / name
        self.page.screenshot(path=str(path), full_page=False)
        return str(path)

    def _read_verified_candles(self) -> list[dict[str, float]] | None:
        try:
            raw = self.page.evaluate("() => window.__GOLDBOT_CANDLES__ || null")
            if not isinstance(raw, list) or len(raw) < 9:
                return None
            out = []
            for row in raw:
                if not isinstance(row, dict):
                    return None
                item = {k: float(row[k]) for k in ("open", "high", "low", "close")}
                if "time" in row:
                    item["time"] = float(row["time"])
                out.append(item)
            return out
        except Exception:
            return None

    @staticmethod
    def _normalize_timeframe(value: str | None) -> str | None:
        if not value:
            return None
        s = " ".join(str(value).strip().split())
        tf = re.fullmatch(r"(1m|3m|5m|15m|30m|45m|1h|2h|4h|6h|12h|1d|1w)", s, re.I)
        if tf:
            return tf.group(1).lower()
        m = re.fullmatch(r"(1|3|5|15|30|45)\s*(?:m|min|mins|minute|minutes)", s, re.I)
        if m:
            return f"{m.group(1)}m"
        h = re.fullmatch(r"(1|2|4|6|12)\s*(?:h|hr|hrs|hour|hours)", s, re.I)
        if h:
            return f"{h.group(1)}h"
        # TradingView Arabic toolbar labels.
        ar = {
            "1دقيقة": "1m", "3دقيقة": "3m", "5دقيقة": "5m", "15دقيقة": "15m",
            "30دقيقة": "30m", "45دقيقة": "45m", "1ساعة": "1h", "2ساعة": "2h",
            "4ساعة": "4h", "6ساعة": "6h", "12ساعة": "12h", "يوم": "1d", "أسبوع": "1w",
        }
        return ar.get(s)

    @staticmethod
    def _parse_symbol(title: str, text: str) -> str | None:
        t = title or ""
        u = t.upper()
        if re.search(r"\bXAUUSD\b", u):
            return "XAU/USD"
        m = re.search(r"\b([A-Z]{2,10})\s*/\s*([A-Z]{2,10})\b", u)
        if m:
            return f"{m.group(1)}/{m.group(2)}"
        body = (text or "").upper()
        if "GOLD SPOT / U.S. DOLLAR" in body or "GOLD SPOT/U.S. DOLLAR" in body:
            return "XAU/USD"
        if re.search(r"\bXAU\s*/?\s*USD\b", body) or re.search(r"\bXAUUSD\b", body):
            return "XAU/USD"
        return None

    @staticmethod
    def _parse_body_timeframe_only_if_unique(text: str) -> str | None:
        body = text or ""
        candidates = []
        for token in re.findall(r"\b(?:1m|3m|5m|15m|30m|45m|1h|2h|4h|6h|12h|1d|1w)\b", body.lower()):
            candidates.append(token)
        unique = set(candidates)
        return next(iter(unique)) if len(unique) == 1 else None

    @classmethod
    def _parse_metadata(cls, title: str, text: str, page=None):
        symbol = cls._parse_symbol(title, text)
        timeframe = cls._read_selected_timeframe(page) if page is not None else None
        if timeframe is None:
            timeframe = cls._parse_body_timeframe_only_if_unique(text)
        return symbol, timeframe

    @staticmethod
    def _read_selected_timeframe(page):
        """Read the selected chart interval from DOM evidence, read-only.

        Title text is deliberately excluded because TradingView titles/studies can
        contain unrelated intervals. Menu entries alone are also insufficient.
        """
        if page is None:
            return None
        try:
            result = page.evaluate(
                r"""() => {
                    const normalize = (value) => {
                      const s = (value || '').trim().replace(/\s+/g, ' ');
                      const aliases = {
                        '1دقيقة':'1m','3دقيقة':'3m','5دقيقة':'5m','15دقيقة':'15m',
                        '30دقيقة':'30m','45دقيقة':'45m','1ساعة':'1h','2ساعة':'2h',
                        '4ساعة':'4h','6ساعة':'6h','12ساعة':'12h','يوم':'1d','أسبوع':'1w'
                      };
                      if (aliases[s]) return aliases[s];
                      let m = s.match(/^(1m|3m|5m|15m|30m|45m|1h|2h|4h|6h|12h|1d|1w)$/i);
                      if (m) return m[1].toLowerCase();
                      m = s.match(/^(1|3|5|15|30|45)\s*(m|min|mins|minute|minutes)$/i);
                      if (m) return `${m[1]}m`;
                      m = s.match(/^(1|2|4|6|12)\s*(h|hr|hrs|hour|hours)$/i);
                      if (m) return `${m[1]}h`;
                      return null;
                    };
                    const controls = [];
                    const selector = 'button,[role="button"],[role="tab"],input';
                    for (const n of document.querySelectorAll(selector)) {
                      if (n.offsetParent === null) continue;
                      const r = n.getBoundingClientRect();
                      if (!r.width || !r.height || r.y < 0 || r.y > 220) continue;
                      const attrs = {
                        dataValue: n.getAttribute('data-value') || '',
                        dataKey: n.getAttribute('data-key') || '',
                        dataTimeframe: n.getAttribute('data-timeframe') || '',
                        dataInterval: n.getAttribute('data-interval') || '',
                        dataResolution: n.getAttribute('data-resolution') || '',
                        aria: n.getAttribute('aria-label') || '',
                        title: n.getAttribute('title') || '',
                        text: (n.textContent || n.value || '').trim(),
                        ariaPressed: n.getAttribute('aria-pressed'),
                        ariaSelected: n.getAttribute('aria-selected'),
                        dataState: n.getAttribute('data-state'),
                        className: typeof n.className === 'string' ? n.className : ''
                      };
                      const values = [attrs.dataValue,attrs.dataKey,attrs.dataTimeframe,attrs.dataInterval,attrs.dataResolution,attrs.aria,attrs.title,attrs.text];
                      for (const raw of values) {
                        const tf = normalize(raw);
                        if (tf) {
                          controls.push({tf, ...attrs, rect:{x:r.x,y:r.y,w:r.width,h:r.height}});
                          break;
                        }
                      }
                    }
                    const metadata = [];
                    for (const n of document.querySelectorAll('[data-timeframe],[data-interval],[data-resolution],meta[name="timeframe"],meta[name="chart-timeframe"]')) {
                      for (const raw of [n.getAttribute('data-timeframe'),n.getAttribute('data-interval'),n.getAttribute('data-resolution'),n.getAttribute('content')]) {
                        const tf = normalize(raw); if (tf) metadata.push(tf);
                      }
                    }
                    return {controls, metadata:[...new Set(metadata)]};
                }"""
            )
            valid = {"1m","3m","5m","15m","30m","45m","1h","2h","4h","6h","12h","1d","1w"}
            controls = [x for x in (result or {}).get("controls", []) if x.get("tf") in valid]
            metadata = [x for x in (result or {}).get("metadata", []) if x in valid]

            explicit = []
            for x in controls:
                state = " ".join([str(x.get("ariaPressed") or ""),str(x.get("ariaSelected") or ""),str(x.get("dataState") or ""),str(x.get("className") or "")]).lower()
                if x.get("ariaPressed") == "true" or x.get("ariaSelected") == "true" or str(x.get("dataState") or "").lower() in {"active","selected"} or re.search(r"(?:^|[\s_-])(selected|active|is-selected|isactive)(?:$|[\s_-])", state):
                    explicit.append(x["tf"])
            if len(set(explicit)) == 1:
                return explicit[0]
            if len(set(explicit)) > 1:
                return None

            if len(set(metadata)) == 1:
                return metadata[0]

            # Compact toolbar fallback. Require a single unique numeric/short label
            # and reject obvious menu/dropdown option entries.
            compact = []
            for x in controls:
                text = x.get("text", "").strip()
                aria = x.get("aria", "").strip().lower()
                title = x.get("title", "").strip().lower()
                data_key = str(x.get("dataKey") or "").lower()
                data_interval = str(x.get("dataInterval") or "").lower()
                data_resolution = str(x.get("dataResolution") or "").lower()
                if re.fullmatch(r"(?:1|3|5|15|30|45)", text) or PlaywrightChartReader._normalize_timeframe(text):
                    evidence = " ".join([aria,title,data_key,data_interval,data_resolution])
                    if not any(token in evidence for token in ("menu","dropdown","option","listbox")):
                        compact.append(x)
            by_tf = {}
            for x in compact:
                by_tf.setdefault(x["tf"], []).append(x)
            if len(by_tf) == 1:
                return next(iter(by_tf))
        except Exception:
            return None
        return None

    def close(self):
        try:
            if self._pw:
                self._pw.stop()
        finally:
            self._pw = None
            self._browser = None
            self.page = None


def read_tradingview_chart(cdp_url: str | None = None) -> dict:
    reader = PlaywrightChartReader(cdp_url=cdp_url)
    try:
        result = reader.connect()
        if result.connected:
            result.screenshot_path = reader.capture()
        return result.to_dict()
    finally:
        reader.close()


if __name__ == "__main__":
    result = read_tradingview_chart()
    print(json.dumps(result, ensure_ascii=False, indent=2))
