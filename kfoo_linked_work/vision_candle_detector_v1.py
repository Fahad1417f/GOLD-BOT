"""Read-only TradingView screenshot candle geometry detector.

No price/OHLC values are inferred here. The detector only proposes pixel candles.
Verification is fail-closed and rejects flat/degenerate structures.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

try:
    from PIL import Image
except Exception:
    Image = None

@dataclass(frozen=True)
class DetectorConfig:
    roi_left: int = 55
    roi_top: int = 75
    roi_right: int | None = None
    roi_bottom: int | None = None
    min_body_height: int = 2
    max_body_width: int = 30
    min_confidence: float = 0.72
    min_wick_extension: int = 2
    min_total_height: int = 5
    max_flat_ratio: float = 0.70

@dataclass(frozen=True)
class PixelCandleCandidate:
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
class Detection:
    candles: tuple[PixelCandleCandidate, ...]
    verified: bool
    reason: str
    roi: tuple[int, int, int, int] | None

def _signal(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    mx, mn = max(rgb), min(rgb)
    return (mx - mn >= 45 and mx >= 75) or (mx - mn >= 28 and mx >= 150)

def detect_candles(path: str | Path, config: DetectorConfig = DetectorConfig()) -> Detection:
    if Image is None:
        return Detection((), False, "PIL_NOT_INSTALLED", None)
    try:
        im = Image.open(path).convert("RGB")
    except Exception as exc:
        return Detection((), False, f"IMAGE_READ_FAILED:{type(exc).__name__}", None)
    w, h = im.size
    l = max(0, config.roi_left)
    t = max(0, config.roi_top)
    r = min(w, config.roi_right if config.roi_right is not None else w - 55)
    b = min(h, config.roi_bottom if config.roi_bottom is not None else h - 70)
    if r - l < 100 or b - t < 100:
        return Detection((), False, "ROI_TOO_SMALL", (l, t, r, b))

    pix = im.load()
    columns = []
    for x in range(l, r):
        ys = [y for y in range(t, b) if _signal(pix[x, y])]
        if not ys:
            continue
        runs = []
        start = prev = ys[0]
        for y in ys[1:]:
            if y == prev + 1:
                prev = y
            else:
                runs.append((start, prev))
                start = prev = y
        runs.append((start, prev))
        body_runs = [q for q in runs if q[1] - q[0] + 1 >= config.min_body_height]
        if body_runs:
            columns.append((x, runs))

    if not columns:
        return Detection((), False, "NO_CHROMATIC_CANDLE_PIXELS", (l, t, r, b))

    groups = []
    cur = [columns[0]]
    for item in columns[1:]:
        if item[0] <= cur[-1][0] + 2:
            cur.append(item)
        else:
            groups.append(cur)
            cur = [item]
    groups.append(cur)

    out = []
    for idx, group in enumerate(groups):
        x0, x1 = group[0][0], group[-1][0]
        width = x1 - x0 + 1
        if width > config.max_body_width:
            continue
        runs = [run for _, rs in group for run in rs]
        body_runs = [run for run in runs if run[1] - run[0] + 1 >= config.min_body_height]
        if not body_runs:
            continue
        body_top = min(a for a, _ in body_runs)
        body_bottom = max(bb for _, bb in body_runs)
        all_ys = [y for _, rs in group for a, bb in rs for y in range(a, bb + 1)]
        high, low = min(all_ys), max(all_ys)
        body_h = body_bottom - body_top + 1
        total_h = low - high + 1
        upper_wick = body_top - high
        lower_wick = low - body_bottom

        # A valid candle must have meaningful vertical geometry. Flat 1-2px
        # lines, isolated horizontal artifacts, and merged screen elements fail closed.
        if total_h < config.min_total_height:
            continue
        if body_h < config.min_body_height:
            continue
        if upper_wick < config.min_wick_extension and lower_wick < config.min_wick_extension:
            continue
        if total_h > 0 and body_h / total_h > config.max_flat_ratio:
            continue

        x = (x0 + x1) / 2
        confidence = 0.72
        confidence += min(0.10, body_h / 50)
        confidence += min(0.10, (upper_wick + lower_wick) / 50)
        confidence = min(0.99, confidence)
        if confidence < config.min_confidence:
            continue
        out.append(PixelCandleCandidate(
            idx, x, body_bottom, high, low, body_top,
            body_top, body_bottom, "unknown", confidence
        ))

    if len(out) < 3:
        return Detection(tuple(out), False, "INSUFFICIENT_VERIFIED_CANDLE_GEOMETRY", (l, t, r, b))
    return Detection(tuple(out), True, "PIXEL_CANDLES_DETECTED", (l, t, r, b))
