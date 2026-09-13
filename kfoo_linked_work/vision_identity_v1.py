"""Evidence-first TradingView identity parser."""
from __future__ import annotations
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class Identity:
    symbol: str | None
    timeframe: str | None
    verified: bool
    reason: str

_VALID_TF = r"(?:1m|3m|5m|15m|30m|45m|1h|2h|4h|6h|12h|1d|1w)"

def parse_visible_identity(title: str, text: str, explicit_timeframe: str | None = None) -> Identity:
    u = (title + "\n" + (text or "")).upper()
    symbol = None
    m = re.search(r"\b([A-Z]{2,12}(?:USDT|USD|USDC)\.P)\b", u)
    if m:
        symbol = m.group(1)
    elif re.search(r"\bXAU\s*/?\s*USD\b|\bXAUUSD\b", u) or "GOLD SPOT / U.S. DOLLAR" in u:
        symbol = "XAU/USD"
    elif "NEAR / TETHERUS PERPETUAL CONTRACT" in u:
        symbol = "NEARUSDT.P"
    else:
        m = re.search(r"\b([A-Z]{2,10})\s*/\s*([A-Z]{2,10})\b", u)
        symbol = f"{m.group(1)}/{m.group(2)}" if m else None
    tf = explicit_timeframe.lower() if explicit_timeframe else None
    if tf and not re.fullmatch(_VALID_TF, tf):
        tf = None
    if symbol is None:
        return Identity(None, tf, False, "SYMBOL_NOT_DETECTED")
    if tf is None:
        return Identity(symbol, None, False, "TIMEFRAME_NOT_VERIFIED")
    return Identity(symbol, tf, True, "IDENTITY_VERIFIED")
