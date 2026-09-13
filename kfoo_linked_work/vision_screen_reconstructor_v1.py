"""Deterministic chart-image candle geometry extractor.

Price mapping is separate and requires verified scale anchors. Invalid pixel
geometry is rejected before any OHLC mapping is accepted.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class PixelCandle:
    index: int
    x: float
    open_y: float
    high_y: float
    low_y: float
    close_y: float
    body_top: float
    body_bottom: float
    polarity: str
    confidence: float

@dataclass(frozen=True)
class ScaleAnchor:
    y: float
    price: float

@dataclass(frozen=True)
class Reconstruction:
    candles: tuple[PixelCandle, ...]
    anchors: tuple[ScaleAnchor, ...]
    ohlc: tuple[dict[str, float], ...]
    verified: bool
    reason: str

class PriceMapper:
    def __init__(self, anchors: Iterable[ScaleAnchor]):
        a=tuple(anchors)
        if len(a)<2 or a[0].y==a[1].y:
            raise ValueError("TWO_DISTINCT_SCALE_ANCHORS_REQUIRED")
        self.a=a

    def price(self,y:float)->float:
        a,b=self.a[0],self.a[1]
        return a.price+(y-a.y)*(b.price-a.price)/(b.y-a.y)

class VisionScreenReconstructorV1:
    """Converts verified pixel candle geometry into OHLC."""

    @staticmethod
    def _valid_geometry(c: PixelCandle) -> bool:
        if c.high_y > min(c.open_y, c.close_y):
            return False
        if c.low_y < max(c.open_y, c.close_y):
            return False
        if c.body_top > c.body_bottom:
            return False
        if c.polarity == "bullish" and c.close_y > c.open_y:
            return False
        if c.polarity == "bearish" and c.close_y < c.open_y:
            return False
        return True

    def map_ohlc(self,candles:Iterable[PixelCandle],anchors:Iterable[ScaleAnchor])->Reconstruction:
        cs=tuple(candles); a=tuple(anchors)
        if not cs: return Reconstruction((),a,(),False,"NO_PIXEL_CANDLES")
        if len(a)<2: return Reconstruction(cs,a,(),False,"TWO_DISTINCT_SCALE_ANCHORS_REQUIRED")
        try: mapper=PriceMapper(a)
        except ValueError as exc: return Reconstruction(cs,a,(),False,str(exc))
        out=[]
        for c in cs:
            if not self._valid_geometry(c):
                return Reconstruction(cs,a,(),False,"INVALID_CANDLE_GEOMETRY")
            vals={"open":mapper.price(c.open_y),"high":mapper.price(c.high_y),
                  "low":mapper.price(c.low_y),"close":mapper.price(c.close_y)}
            if vals["high"] < max(vals["open"],vals["close"]) or vals["low"] > min(vals["open"],vals["close"]):
                return Reconstruction(cs,a,(),False,"INVALID_CANDLE_GEOMETRY")
            out.append(vals)
        return Reconstruction(cs,a,tuple(out),True,"VERIFIED_PIXEL_TO_OHLC")
