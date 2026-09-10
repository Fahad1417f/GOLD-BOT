from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from head_shoulders_v56 import detect
from verified_mtf_candle_pipeline_v56 import VerifiedMTFCandlePipelineV56


@dataclass
class HNSFrameResult:
    timeframe: str
    available: bool = False
    verified: bool = False
    detected: bool = False
    confirmed: bool = False
    direction: str = "neutral"
    pattern: str = "none"
    neckline: float | None = None
    confidence: float = 0.0
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VerifiedHNSMTFResult:
    verified: bool = False
    aligned: bool = False
    direction: str = "neutral"
    frames: dict[str, HNSFrameResult] | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified": self.verified,
            "aligned": self.aligned,
            "direction": self.direction,
            "frames": {k: v.to_dict() for k, v in (self.frames or {}).items()},
            "reason": self.reason,
        }


class VerifiedHNSMTFV56:
    """Read-only MTF H&S confirmation using verified XAU/USD OHLC candles."""

    TIMEFRAMES = ("4h", "1h", "15m")

    def __init__(self, api_key: str | None = None, timeout: float = 10.0):
        self.pipeline = VerifiedMTFCandlePipelineV56(api_key=api_key, timeout=timeout)

    def read(self, outputsize: int = 100) -> VerifiedHNSMTFResult:
        mtf = self.pipeline.read(outputsize=outputsize)
        frames: dict[str, HNSFrameResult] = {}
        confirmed_dirs: list[str] = []

        for tf in self.TIMEFRAMES:
            frame = (mtf.frames or {}).get(tf)
            candles = frame.candles if frame else None
            if not frame or not frame.available or not frame.verified or len(candles or []) < 9:
                frames[tf] = HNSFrameResult(
                    timeframe=tf,
                    reason=(frame.reason if frame else "FRAME_UNAVAILABLE"),
                )
                continue

            h = detect(candles)
            frames[tf] = HNSFrameResult(
                timeframe=tf,
                available=True,
                verified=True,
                detected=h.detected,
                confirmed=h.confirmed,
                direction=h.direction,
                pattern=h.pattern,
                neckline=h.neckline,
                confidence=h.confidence,
                reason=h.reason,
            )
            if h.confirmed and h.direction in ("long", "short"):
                confirmed_dirs.append(h.direction)

        verified = all(frames[tf].verified for tf in self.TIMEFRAMES)
        aligned = bool(confirmed_dirs) and len(set(confirmed_dirs)) == 1
        direction = confirmed_dirs[0] if aligned else "neutral"

        if not verified:
            bad = ";".join(f"{tf}:{frames[tf].reason}" for tf in self.TIMEFRAMES if not frames[tf].verified)
            reason = f"HNS_MTF_INCOMPLETE:{bad}"
        elif aligned:
            reason = "VERIFIED_HNS_MTF_ALIGNED"
        elif confirmed_dirs:
            reason = "VERIFIED_HNS_MTF_CONFLICT_OR_PARTIAL"
        else:
            reason = "VERIFIED_HNS_MTF_NO_CONFIRMED_PATTERN"

        return VerifiedHNSMTFResult(
            verified=verified,
            aligned=aligned,
            direction=direction,
            frames=frames,
            reason=reason,
        )


if __name__ == "__main__":
    import json
    result = VerifiedHNSMTFV56().read(outputsize=100)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
