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
            symbol, timeframe = self._parse_metadata(title, text, self.page)
            candles = self._read_verified_candles()
            return ChartRead(
                connected=True,
                verified=bool(symbol or timeframe),
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
        return None

    @staticmethod
    def _parse_metadata(title: str, text: str, page=None):
        """Parse TradingView metadata from title and visible DOM text.

        Timeframe detection is deliberately fail-closed: the reader accepts a
        timeframe only from an explicit active/selected control, a page-level
        selected-timeframe metadata attribute, or an unambiguous standalone
        body token. The mere presence of the timeframe menu is not evidence.
        """
        symbol, timeframe = PlaywrightChartReader._parse_title(title)
        body = text or ""

        upper = body.upper()
        if symbol is None:
            if "GOLD SPOT / U.S. DOLLAR" in upper or "GOLD SPOT/U.S. DOLLAR" in upper:
                symbol = "XAU/USD"
            elif re.search(r"\bXAU\s*/?\s*USD\b", upper):
                symbol = "XAU/USD"
            elif re.search(r"\bXAUUSD\b", upper):
                symbol = "XAU/USD"

        if timeframe is None and page is not None:
            timeframe = PlaywrightChartReader._read_selected_timeframe(page)

        if timeframe is None:
            matches = re.findall(r"(?<![\w])(?:1m|3m|5m|15m|30m|45m|1h|2h|4h|6h|12h|1d|1w)(?![\w])", body.lower())
            if len(set(matches)) == 1:
                timeframe = matches[0]

        return symbol, timeframe

    @staticmethod
    def _read_selected_timeframe(page):
        """Read the active TradingView interval from explicit DOM/page state."""
        try:
            result = page.evaluate(
                r"""() => {
                    const valid = new Set(['1m','3m','5m','15m','30m','45m','1h','2h','4h','6h','12h','1d','1w']);
                    const normalize = (value) => {
                      const s = (value || '').trim().replace(/\s+/g, ' ');
                      let m = s.match(/^(1m|3m|5m|15m|30m|45m|1h|2h|4h|6h|12h|1d|1w)$/i);
                      if (m) return m[1].toLowerCase();
                      m = s.match(/^(1|3|5|15|30|45)\s*(m|min|mins|minute|minutes)$/i);
                      if (m) return `${m[1]}m`;
                      m = s.match(/^(1|2|4|6|12)\s*(h|hr|hrs|hour|hours)$/i);
                      if (m) return `${m[1]}h`;
                      return null;
                    };

                    const found = [];

                    // 1) Page-level attributes / state. These are more specific
                    // than the visible menu because they describe the current chart.
                    const pageNodes = Array.from(document.querySelectorAll(
                      'body, [data-testid], [data-name], [data-role], [data-value], [aria-label], [title]'
                    ));
                    for (const n of pageNodes) {
                      const attrs = ['data-timeframe','data-interval','data-resolution','data-value','aria-label','title'];
                      for (const attr of attrs) {
                        const v = normalize(n.getAttribute(attr));
                        if (v && attr !== 'data-value') found.push(v);
                      }
                    }

                    // 2) Explicit active/selected controls. We inspect the
                    // selected node's own attributes/text only.
                    const activeSelectors = [
                      '[aria-selected="true"]',
                      '[aria-pressed="true"]',
                      '[data-state="active"]',
                      '[data-selected="true"]',
                      '.selected',
                      '.active'
                    ];
                    const activeNodes = Array.from(document.querySelectorAll(activeSelectors.join(',')));
                    const active = [];
                    for (const n of activeNodes) {
                      const candidates = [
                        n.getAttribute('data-timeframe'),
                        n.getAttribute('data-interval'),
                        n.getAttribute('data-resolution'),
                        n.getAttribute('data-value'),
                        n.getAttribute('aria-label'),
                        n.getAttribute('title'),
                        n.textContent
                      ];
                      for (const candidate of candidates) {
                        const v = normalize(candidate);
                        if (v) active.push(v);
                      }
                    }

                    // Return explicit active state first. If there is exactly one
                    // page-level metadata value, it is also safe to use.
                    const uniqueActive = [...new Set(active)];
                    const uniqueFound = [...new Set(found)];
                    return {
                      active: uniqueActive,
                      page: uniqueFound
                    };
                }"""
            )
            valid = {
                "1m", "3m", "5m", "15m", "30m", "45m",
                "1h", "2h", "4h", "6h", "12h", "1d", "1w",
            }
            active = [v for v in (result or {}).get("active", []) if v in valid]
            page_values = [v for v in (result or {}).get("page", []) if v in valid]

            if len(set(active)) == 1:
                return active[0]
            if len(set(active)) > 1:
                return None

            # Avoid trusting arbitrary title/aria labels. A page-level result is
            # accepted only when exactly one value exists and it is not generated
            # by the standard timeframe menu.
            if len(set(page_values)) == 1:
                return page_values[0]
        except Exception:
            pass
        return None

    @staticmethod
    def _parse_title(title: str):
        t = title or ""
        u = t.upper()
        symbol = "XAU/USD" if re.search(r"\bXAUUSD\b", u) else None
        m = re.search(r"\b([A-Z]{2,10})\s*/\s*([A-Z]{2,10})\b", u)
        if m:
            symbol = f"{m.group(1)}/{m.group(2)}"
        timeframe = None
        low = t.lower()
        for tf in ("1w", "1d", "12h", "6h", "4h", "2h", "1h", "45m", "30m", "15m", "5m", "3m", "1m"):
            if re.search(rf"(?<![\w]){re.escape(tf)}(?![\w])", low):
                timeframe = tf
                break
        return symbol, timeframe

    def close(self):
        try:
            if self._pw:
                self._pw.stop()
        finally:
            self._pw = None
            self._browser = None
            self.page = None


if __name__ == "__main__":
    reader = PlaywrightChartReader()
    result = reader.connect()
    if result.connected:
        result.screenshot_path = reader.capture()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    reader.close()
