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
    def _parse_metadata(title: str, text: str, page=None):
        """Parse TradingView metadata from title first, then visible DOM text.

        TradingView commonly exposes titles such as ``XAUUSD 4,411`` while
        the visible chart identifies the instrument as ``Gold Spot / U.S.
        Dollar``. Timeframe buttons are inspected for an explicitly selected
        state before falling back to a conservative visible-text heuristic.
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
            # Only accept an unambiguous standalone timeframe token. This is
            # deliberately conservative because the body also contains the
            # full list of timeframe buttons.
            matches = re.findall(r"(?<![\w])(?:1m|3m|5m|15m|30m|45m|1h|2h|4h|6h|12h|1d|1w)(?![\w])", body.lower())
            if len(set(matches)) == 1:
                timeframe = matches[0]

        return symbol, timeframe

    @staticmethod
    def _read_selected_timeframe(page):
        """Find a selected TradingView timeframe control when exposed by DOM."""
        try:
            values = page.evaluate(
                """() => {
                    const nodes = Array.from(document.querySelectorAll(
                      '[aria-selected="true"], [aria-pressed="true"], [data-value]'
                    ));
                    const out = [];
                    const re = /^(1m|3m|5m|15m|30m|45m|1h|2h|4h|6h|12h|1d|1w)$/i;
                    for (const n of nodes) {
                      const candidates = [n.getAttribute('data-value'), n.getAttribute('aria-label'), n.getAttribute('title'), n.textContent];
                      for (const v of candidates) {
                        const s = (v || '').trim();
                        const m = s.match(re) || s.match(/^(1|3|5|15|30|45)\s*(min|minutes)$/i) || s.match(/^(1|2|4|6|12)\s*(h|hour|hours)$/i);
                        if (m) out.push(s.toLowerCase());
                      }
                    }
                    return out;
                }"""
            )
            for value in values or []:
                v = str(value).lower().strip()
                v = re.sub(r"\s*(minutes|min)$", "m", v)
                v = re.sub(r"\s*(hours|hour)$", "h", v)
                if v in {"1m","3m","5m","15m","30m","45m","1h","2h","4h","6h","12h","1d","1w"}:
                    return v
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
