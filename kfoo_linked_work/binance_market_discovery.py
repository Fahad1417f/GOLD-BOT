from __future__ import annotations

"""Public Binance USDⓈ-M market discovery for Opportunity Scanner.

Discovery only: no API key, no trading, no orders. It fetches tradable
USDT perpetual symbols plus 24h ticker and recent klines, then emits market
metadata for the upstream KFOO enrichment layer. KFOO fields are deliberately
left absent rather than fabricated.
"""

import json, time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://fapi.binance.com"
UA = "GOLD-BOT-Opportunity-Scanner/1.0"


def get_json(path: str, params: dict | None = None, timeout: float = 10.0):
    q = urlencode(params or {})
    url = BASE + path + (("?" + q) if q else "")
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def perpetual_usdt_symbols(limit: int = 40) -> list[str]:
    info = get_json("/fapi/v1/exchangeInfo")
    rows = [
        s for s in info.get("symbols", [])
        if s.get("status") == "TRADING"
        and s.get("contractType") == "PERPETUAL"
        and s.get("quoteAsset") == "USDT"
    ]
    rows.sort(key=lambda s: s.get("symbol", ""))
    return [s["symbol"] for s in rows[:max(1, int(limit))]]


def ticker24() -> dict[str, dict]:
    rows = get_json("/fapi/v1/ticker/24hr")
    return {x["symbol"]: x for x in rows if isinstance(x, dict) and x.get("symbol")}


def klines(symbol: str, interval: str = "5m", limit: int = 30):
    return get_json("/fapi/v1/klines", {"symbol": symbol, "interval": interval, "limit": limit})


def build_candidates(limit: int = 20) -> list[dict]:
    symbols = set(perpetual_usdt_symbols(max(limit * 2, 20)))
    tickers = ticker24()
    rows = []
    for symbol in symbols:
        t = tickers.get(symbol)
        if not t:
            continue
        try:
            pct = float(t.get("priceChangePercent", 0))
            vol = float(t.get("quoteVolume", 0))
            last = float(t.get("lastPrice", 0))
        except (TypeError, ValueError):
            continue
        rows.append((vol, symbol, pct, last, int(t.get("closeTime") or 0)))
    rows.sort(reverse=True)
    out = []
    for vol, symbol, pct, last, close_ms in rows[:limit]:
        direction = "long" if pct > 0 else "short" if pct < 0 else "neutral"
        out.append({
            "symbol": symbol + ".P",
            "binance_symbol": symbol,
            "direction": direction,
            "price": last,
            "change_24h_pct": pct,
            "quote_volume_24h": vol,
            "timestamp": close_ms,
            "source": "BINANCE_PUBLIC_USDM",
            "market_discovery_only": True,
            "kfoo_enrichment_required": True,
        })
    return out


def write_snapshot(path: str = "opportunity_market_discovery.json", limit: int = 20):
    payload = {
        "source": "BINANCE_PUBLIC_USDM",
        "generated_at": int(time.time() * 1000),
        "candidates": build_candidates(limit),
    }
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="opportunity_market_discovery.json")
    p.add_argument("--limit", type=int, default=20)
    args = p.parse_args()
    result = write_snapshot(args.output, args.limit)
    print(json.dumps({"ok": True, "count": len(result["candidates"]), "output": args.output}, indent=2))
