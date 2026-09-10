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

    def read_live_kfoo(self):
        """Read the explicitly verified live KFOO provider exposed by the chart page.

        No OCR, screenshot inference, menu inference, or synthetic fallback is used.
        The page must expose window.__GOLDBOT_KFOO__ with the strict V56 schema.
        """
        if self.page is None:
            raise RuntimeError("TRADINGVIEW_PAGE_NOT_CONNECTED")
        from tradingview_kfoo_provider_v56 import read_from_page
        return read_from_page(self.page)

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
        """Parse TradingView metadata without treating the timeframe menu as truth."""
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
        """Read the selected chart interval from DOM and chart toolbar evidence.

        This method is read-only. It never clicks, changes the timeframe, or
        executes trades. A candidate is accepted only when its evidence is
        specific enough to distinguish the selected chart interval from the
        complete timeframe menu.
        """
        try:
            result = page.evaluate(
                r"""() => {
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
                    const controls = [];
                    const selector = 'button,[role="button"],[role="tab"]';
                    for (const n of document.querySelectorAll(selector)) {
                      if (n.offsetParent === null) continue;
                      const r = n.getBoundingClientRect();
                      if (!r.width || !r.height || r.y < 0 || r.y > 180) continue;
                      const attrs = {
                        dataValue: n.getAttribute('data-value') || '',
                        dataKey: n.getAttribute('data-key') || '',
                        dataTimeframe: n.getAttribute('data-timeframe') || '',
                        dataInterval: n.getAttribute('data-interval') || '',
                        dataResolution: n.getAttribute('data-resolution') || '',
                        aria: n.getAttribute('aria-label') || '',
                        title: n.getAttribute('title') || '',
                        text: (n.textContent || '').trim(),
                        ariaPressed: n.getAttribute('aria-pressed'),
                        ariaSelected: n.getAttribute('aria-selected'),
                        dataState: n.getAttribute('data-state'),
                        className: typeof n.className === 'string' ? n.className : ''
                      };
                      const values = Object.values(attrs).slice(0, 7);
                      for (const raw of values) {
                        const tf = normalize(raw);
                        if (!tf) continue;
                        controls.push({
                          tf, ...attrs,
                          rect: {x:r.x,y:r.y,w:r.width,h:r.height}
                        });
                        break;
                      }
                    }

                    // Page-level chart metadata, restricted to explicit attributes.
                    const metadata = [];
                    for (const n of document.querySelectorAll('[data-timeframe],[data-interval],[data-resolution],meta[name="timeframe"],meta[name="chart-timeframe"]')) {
                      for (const raw of [
                        n.getAttribute('data-timeframe'), n.getAttribute('data-interval'),
                        n.getAttribute('data-resolution'), n.getAttribute('content')
                      ]) {
                        const tf = normalize(raw);
                        if (tf) metadata.push(tf);
                      }
                    }

                    return {controls, metadata:[...new Set(metadata)]};
                }"""
            )

            valid = {"1m","3m","5m","15m","30m","45m","1h","2h","4h","6h","12h","1d","1w"}
            controls = [x for x in (result or {}).get("controls", []) if x.get("tf") in valid]
            metadata = [x for x in (result or {}).get("metadata", []) if x in valid]

            # 1. Explicit state wins, but only when it resolves to one timeframe.
            explicit = []
            for x in controls:
                state = " ".join([
                    str(x.get("ariaPressed") or ""),
                    str(x.get("ariaSelected") or ""),
                    str(x.get("dataState") or ""),
                    str(x.get("className") or ""),
                ]).lower()
                if (
                    x.get("ariaPressed") == "true"
                    or x.get("ariaSelected") == "true"
                    or str(x.get("dataState") or "").lower() in {"active", "selected"}
                    or re.search(r"(?:^|[\s_-])(selected|active|is-selected|isactive)(?:$|[\s_-])", state)
                ):
                    explicit.append(x["tf"])
            if len(set(explicit)) == 1:
                return explicit[0]
            if len(set(explicit)) > 1:
                return None

            # 2. Explicit page metadata wins over the menu, when unique.
            if len(set(metadata)) == 1:
                return metadata[0]

            # 3. TradingView sometimes exposes the current interval in a compact
            # toolbar control as a numeric label (e.g. "15") while all menu
            # buttons carry their own labels. In that case look for a control
            # whose text is numeric and whose accessible metadata does NOT look
            # like an option list entry. Require a single unique tf.
            compact = []
            for x in controls:
                text = x.get("text", "").strip()
                aria = x.get("aria", "").strip().lower()
                title = x.get("title", "").strip().lower()
                if re.fullmatch(r"(?:1|3|5|15|30|45)", text) or PlaywrightChartReader._normalize_timeframe(text):
                    evidence = " ".join([aria, title, str(x.get("dataKey") or ""), str(x.get("dataInterval") or ""), str(x.get("dataResolution") or "")]).lower()
                    # Do not accept controls explicitly labelled as list/menu options.
                    if not any(token in evidence for token in ("menu", "dropdown", "option")):
                        compact.append(x)

            by_tf = {}
            for x in compact:
                by_tf.setdefault(x["tf"], []).append(x)
            if len(by_tf) == 1:
                only_tf = next(iter(by_tf))
                # More than one duplicate control for the same tf is acceptable;
                # multiple different timeframes are not.
                return only_tf

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
