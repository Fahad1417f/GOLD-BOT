from __future__ import annotations
from dataclasses import dataclass
import re
from typing import Optional

@dataclass(frozen=True)
class CandleClock:
    timeframe: str
    remaining_seconds: int
    raw: str
    source: str = "kfoo_table"

    @property
    def closed(self) -> bool:
        return self.remaining_seconds <= 0

    @property
    def remaining_hms(self) -> str:
        s=max(0,int(self.remaining_seconds))
        return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"

# KFOO's table clock is preferred for 15M/3M. 4H/1H are deliberately
# excluded here because their existing 210s gravity dwell remains unchanged.
_TABLE_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9])(?P<tf>15m|3m)\s+(?P<mm>\d{1,2}):(?P<ss>\d{2})(?::(?P<hh>\d{1,2}))?(?!\d)", re.I),
    re.compile(r"KFOO_CLOCK_(?P<tf>15M|3M)\s*=\s*(?P<mm>\d{1,2}):(?P<ss>\d{2})(?::(?P<hh>\d{1,2}))?", re.I),
    re.compile(r"(?P<tf>15M|3M)_REMAINING\s*=\s*(?P<seconds>\d+(?:\.\d+)?)", re.I),
)

def parse_kfoo_candle_clock(text: str, timeframe: str) -> Optional[CandleClock]:
    tf=timeframe.lower()
    if tf not in {"15m","3m"}:
        return None
    matches=[]
    for pattern in _TABLE_PATTERNS:
        for m in pattern.finditer(text or ""):
            if m.group("tf").lower()!=tf:
                continue
            if m.groupdict().get("seconds") is not None:
                seconds=round(float(m.group("seconds")))
                raw=m.group(0)
            else:
                mm=int(m.group("mm")); ss=int(m.group("ss")); hh=int(m.group("hh") or 0)
                seconds=hh*3600+mm*60+ss
                raw=m.group(0)
            matches.append(CandleClock(tf, max(0,seconds), raw, "kfoo_table"))
    return matches[-1] if matches else None

def parse_legacy_leader_remaining(text: str) -> Optional[CandleClock]:
    m=list(re.finditer(r"LEADER_15M_REMAINING\s*=\s*([0-9]+(?:\.[0-9]+)?)", text or "", re.I|re.M))
    if not m:
        return None
    return CandleClock("15m", max(0,round(float(m[-1].group(1)))), m[-1].group(0), "legacy_leader_log")
