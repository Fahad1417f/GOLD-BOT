from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Sequence

@dataclass
class HNSResult:
    detected: bool = False
    pattern: str = 'none'
    neckline: float | None = None
    confirmed: bool = False
    direction: str = 'neutral'
    reason: str = 'insufficient_data'
    confidence: float = 0.0
    def to_dict(self): return asdict(self)

def _close(x: Any) -> float:
    if isinstance(x, dict): return float(x.get('close', x.get('c')))
    return float(x)

def _pivots(values: Sequence[float], span: int = 1):
    highs, lows = [], []
    for i in range(span, len(values)-span):
        w = values[i-span:i+span+1]
        if values[i] == max(w) and values[i] > max(values[i-span:i]): highs.append(i)
        if values[i] == min(w) and values[i] < min(values[i-span:i]): lows.append(i)
    return highs, lows

def detect(candles: Sequence[Any], *, tolerance: float = 0.035, breakout_buffer: float = 0.001, require_closed_break: bool = True) -> HNSResult:
    if len(candles) < 9: return HNSResult(reason='need_at_least_9_candles')
    highs = [float(c.get('high', c.get('h', c.get('close', c.get('c'))))) if isinstance(c,dict) else _close(c) for c in candles]
    lows = [float(c.get('low', c.get('l', c.get('close', c.get('c'))))) if isinstance(c,dict) else _close(c) for c in candles]
    closes = [_close(c) for c in candles]
    hi, lo = _pivots(highs)[0], _pivots(lows)[1]
    for typ in ('bearish','bullish'):
        piv = hi if typ == 'bearish' else lo
        if len(piv) < 3: continue
        a,b,c = piv[-3:]
        if typ == 'bearish':
            head, shoulders = highs[b], (highs[a]+highs[c])/2
            if head <= shoulders or abs(highs[a]-highs[c])/max(head,1e-9) > tolerance: continue
            neckline = (min(lows[a:b+1]) + min(lows[b:c+1]))/2
            last = candles[-1] if isinstance(candles[-1],dict) else {'close':closes[-1],'high':highs[-1],'low':lows[-1]}
            crossed = closes[-1] < neckline*(1-breakout_buffer)
            if require_closed_break and not crossed:
                return HNSResult(True,'bearish_head_shoulders',neckline,False,'neutral','pattern_detected_waiting_for_clean_neckline_break',0.78)
            clean = float(last.get('high',closes[-1])) < neckline
            ok = crossed and clean
            return HNSResult(True,'bearish_head_shoulders',neckline,ok,'short' if ok else 'neutral','clean_closed_break' if ok else 'breakout_touches_or_straddles_neckline',0.95 if ok else 0.78)
        head, shoulders = lows[b], (lows[a]+lows[c])/2
        if head >= shoulders or abs(lows[a]-lows[c])/max(abs(head),1e-9) > tolerance: continue
        neckline = (max(highs[a:b+1]) + max(highs[b:c+1]))/2
        last = candles[-1] if isinstance(candles[-1],dict) else {'close':closes[-1],'high':highs[-1],'low':lows[-1]}
        crossed = closes[-1] > neckline*(1+breakout_buffer)
        if require_closed_break and not crossed:
            return HNSResult(True,'bullish_inverse_head_shoulders',neckline,False,'neutral','pattern_detected_waiting_for_clean_neckline_break',0.78)
        clean = float(last.get('low',closes[-1])) > neckline
        ok = crossed and clean
        return HNSResult(True,'bullish_inverse_head_shoulders',neckline,ok,'long' if ok else 'neutral','clean_closed_break' if ok else 'breakout_touches_or_straddles_neckline',0.95 if ok else 0.78)
    return HNSResult(reason='no_valid_pattern')
