"""Evidence-first TradingView identity parser.

Parses visible page text only. It never assumes the chart is gold and never
changes the TradingView page. Timeframe is accepted only from an explicit
selected/metadata source; the full timeframe menu is not treated as selection.
"""
from __future__ import annotations
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class Identity:
    symbol: str|None
    timeframe: str|None
    verified: bool
    reason: str

_TF_AR={"دقيقة":"m","ساعة":"h","يوم":"d","أسبوع":"w"}
def parse_visible_identity(title: str, text: str, explicit_timeframe: str|None=None)->Identity:
    u=(title+"\n"+(text or "")).upper()
    symbol=None
    if re.search(r"\bXAU\s*/?\s*USD\b|\bXAUUSD\b",u) or "GOLD SPOT / U.S. DOLLAR" in u:
        symbol="XAU/USD"
    else:
        m=re.search(r"\b([A-Z]{2,10})\s*/\s*([A-Z]{2,10})\b",u)
        if m: symbol=f"{m.group(1)}/{m.group(2)}"
        else:
            m=re.search(r"\b([A-Z]{2,12}(?:USDT|USD|USDC)\.P)\b",u)
            if m: symbol=m.group(1)
    tf=explicit_timeframe.lower() if explicit_timeframe else None
    if tf and not re.fullmatch(r"(?:1m|3m|5m|15m|30m|45m|1h|2h|4h|6h|12h|1d|1w)",tf):
        tf=None
    if symbol is None: return Identity(None,tf,False,"SYMBOL_NOT_DETECTED")
    if tf is None: return Identity(symbol,None,False,"TIMEFRAME_NOT_VERIFIED")
    return Identity(symbol,tf,True,"IDENTITY_VERIFIED")
