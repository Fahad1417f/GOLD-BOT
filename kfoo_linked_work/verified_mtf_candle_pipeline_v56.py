from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Any

from twelvedata_candle_source_v56 import TwelveDataCandleSourceV56


@dataclass
class MTFFrame:
    timeframe: str
    available: bool = False
    verified: bool = False
    source: str = "none"
    candles: list[dict[str, Any]] | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VerifiedMTFRead:
    symbol: str = "XAU/USD"
    frames: dict[str, MTFFrame] | None = None
    verified: bool = False
    all_required_available: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["frames"] = {k: v.to_dict() for k, v in (self.frames or {}).items()}
        return out


class VerifiedMTFCandlePipelineV56:
    """Read-only verified XAU/USD MTF candle pipeline for V56.

    The source of truth for OHLC is the explicit Twelve Data adapter. TradingView
    remains responsible for live chart identity/timeframe evidence; it is never
    used here to infer candles from DOM text or screenshots.
    """

    REQUIRED_TIMEFRAMES = ("4h", "1h", "15m", "5m", "3m")

    def __init__(self, api_key: str | None = None, timeout: float = 10.0):
        self.source = TwelveDataCandleSourceV56(api_key=api_key, timeout=timeout)

    def read(self, outputsize: int = 100) -> VerifiedMTFRead:
        frames: dict[str, MTFFrame] = {}
        for tf in self.REQUIRED_TIMEFRAMES:
            feed = self.source.read(tf, outputsize=outputsize)
            frames[tf] = MTFFrame(
                timeframe=tf,
                available=feed.available,
                verified=feed.verified,
                source=feed.source,
                candles=feed.candles,
                reason=feed.reason,
            )

        complete = all(
            frames[tf].available and frames[tf].verified and len(frames[tf].candles or []) >= 9
            for tf in self.REQUIRED_TIMEFRAMES
        )
        reasons = [f"{tf}:{frames[tf].reason}" for tf in self.REQUIRED_TIMEFRAMES if not frames[tf].verified]
        return VerifiedMTFRead(
            symbol="XAU/USD",
            frames=frames,
            verified=complete,
            all_required_available=complete,
            reason="VERIFIED_MTF_CANDLES_READ" if complete else "MTF_INCOMPLETE:" + ";".join(reasons),
        )


if __name__ == "__main__":
    result = VerifiedMTFCandlePipelineV56().read(outputsize=int(os.getenv("GOLDBOT_CANDLE_OUTPUTSIZE", "100")))
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
