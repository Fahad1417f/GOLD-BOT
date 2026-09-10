from __future__ import annotations

"""Verified V56 KFOO publisher bridge.

Purpose:
  Receive the REAL KFOO producer's JSON payload over localhost and publish it
  into the already-open TradingView page as window.__GOLDBOT_KFOO__.

Safety:
  - validates the existing V56 provider schema before publishing
  - never generates, OCRs, infers, or fills KFOO values
  - never navigates, clicks, changes timeframe, or executes trades
  - rejects incomplete/non-verified payloads
"""

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

from tradingview_kfoo_provider_v56 import validate

HOST = os.getenv("GOLDBOT_KFOO_BRIDGE_HOST", "127.0.0.1")
PORT = int(os.getenv("GOLDBOT_KFOO_BRIDGE_PORT", "8765"))
CDP_URL = os.getenv("TRADINGVIEW_CDP_URL", "http://127.0.0.1:9222")
MAX_BODY = 2_000_000
AUDIT = Path(os.getenv("GOLDBOT_KFOO_AUDIT_LOG", "kfoo_publisher.log"))

_state = {"page": None, "pw": None, "browser": None, "last_source": None}


def audit(event: str, detail: str = "") -> None:
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT.open("a", encoding="utf-8") as f:
        f.write(event + ((" " + detail) if detail else "") + "\n")


def connect_page():
    _state["pw"] = sync_playwright().start()
    _state["browser"] = _state["pw"].chromium.connect_over_cdp(CDP_URL)
    pages = [p for c in _state["browser"].contexts for p in c.pages]
    pages = [p for p in pages if "tradingview.com" in (p.url or "").lower()]
    if not pages:
        raise RuntimeError("TRADINGVIEW_PAGE_NOT_FOUND")
    _state["page"] = pages[0]
    audit("PAGE_CONNECTED", _state["page"].url)


def publish(payload: dict) -> None:
    analysis, timing = validate(payload)
    page = _state["page"]
    if page is None or page.is_closed():
        connect_page()

    # Re-validate identity at publish time. The bridge is for the live chart only.
    url = _state["page"].url
    if "tradingview.com" not in (url or "").lower():
        raise RuntimeError("TRADINGVIEW_PAGE_NOT_ACTIVE")

    _state["page"].evaluate(
        """(payload) => {
          window.__GOLDBOT_KFOO__ = payload;
          const marker = document.getElementById('__goldbot_kfoo_bridge_v56__')
              || document.createElement('script');
          marker.id = '__goldbot_kfoo_bridge_v56__';
          marker.type = 'application/json';
          marker.setAttribute('data-goldbot-kfoo', JSON.stringify(payload));
          marker.textContent = JSON.stringify(payload);
          if (!marker.parentNode) document.documentElement.appendChild(marker);
        }""",
        payload,
    )
    _state["last_source"] = "http_verified_publisher"
    audit("PUBLISHED", "source=http_verified_publisher")


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict):
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path != "/health":
            self._send(404, {"ok": False, "error": "NOT_FOUND"})
            return
        page = _state.get("page")
        self._send(200, {
            "ok": bool(page and not page.is_closed()),
            "publisher": "V56_VERIFIED_KFOO_HTTP_BRIDGE",
            "source": _state.get("last_source"),
            "execution": "OFF",
        })

    def do_POST(self):
        if self.path != "/publish":
            self._send(404, {"ok": False, "error": "NOT_FOUND"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY:
                raise RuntimeError("INVALID_BODY_SIZE")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            publish(payload)
            self._send(200, {"ok": True, "source": "http_verified_publisher"})
        except Exception as exc:
            audit("PUBLISH_REJECTED", f"{type(exc).__name__}:{exc}")
            self._send(400, {"ok": False, "error": f"{type(exc).__name__}:{exc}"})

    def log_message(self, *_args):
        return


if __name__ == "__main__":
    connect_page()
    audit("START", f"host={HOST} port={PORT}")
    HTTPServer((HOST, PORT), Handler).serve_forever()
