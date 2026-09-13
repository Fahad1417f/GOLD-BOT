"""GOLD Vision Agent V1: perception-only, evidence-first chart observer.

Design: live capture -> geometry -> candles -> structure -> confidence.
No broker/execution imports are allowed in this module.
""" 
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Iterable
import time

@dataclass(frozen=True)
class Candle:
    index:int; open:float; high:float; low:float; close:float
    timestamp:float|None=None

@dataclass(frozen=True)
class VisionEvidence:
    timestamp:float
    source:str
    timeframe:str
    candles:tuple[Candle,...]
    trend:str
    swings:tuple[dict[str,Any],...]
    confidence:float
    components:dict[str,float]
    warnings:tuple[str,...]=()

class VisionAgentV1:
    """Pure analysis layer. It consumes normalized OHLC or a future frame adapter."""
    def analyze_ohlc(self, candles:Iterable[dict[str,float]], timeframe:str="unknown",
                    source:str="normalized_ohlc") -> VisionEvidence:
        rows=list(candles)
        cs=tuple(Candle(i,float(r["open"]),float(r["high"]),float(r["low"]),float(r["close"]),r.get("timestamp"))
                 for i,r in enumerate(rows))
        if not cs:
            return VisionEvidence(time.time(),source,timeframe,(),"unknown",(),0.0,
                                   {"data":0.0,"structure":0.0},("NO_CANDLES",))
        swings=[]
        for i in range(1,len(cs)-1):
            if cs[i].high>cs[i-1].high and cs[i].high>=cs[i+1].high:
                swings.append({"index":i,"type":"high","price":cs[i].high})
            if cs[i].low<cs[i-1].low and cs[i].low<=cs[i+1].low:
                swings.append({"index":i,"type":"low","price":cs[i].low})
        closes=[c.close for c in cs]
        trend="up" if closes[-1]>closes[0] else "down" if closes[-1]<closes[0] else "flat"
        data_conf=min(1.0,len(cs)/20.0)
        structure_conf=1.0 if len(swings)>=2 else 0.5 if swings else 0.0
        confidence=round(0.6*data_conf+0.4*structure_conf,4)
        return VisionEvidence(time.time(),source,timeframe,cs,trend,tuple(swings),confidence,
                              {"data":round(data_conf,4),"structure":round(structure_conf,4)})
