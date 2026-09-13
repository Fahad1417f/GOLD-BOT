"""Read-only TradingView screenshot candle geometry detector.

No price/OHLC values are inferred here. The detector only proposes pixel candles.
Verification is fail-closed and rejects long overlay groups by requiring local
candle-width geometry, vertical-run continuity, and a broad body core.
"""
from __future__ import annotations

import math
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
    max_body_width: int = 18
    min_confidence: float = 0.72
    min_wick_extension: int = 2
    min_total_height: int = 5
    min_core_width_ratio: float = 0.50
    max_body_to_total_ratio: float = 0.90
    min_vertical_run: int = 6
    min_span_iou: float = 0.50
    max_x_gap: int = 1
    min_body_coverage_ratio: float = 0.60


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


def _candle_color(rgb: tuple[int, int, int]) -> bool:
    """Broad red/green candle palette, excluding grey and yellow plot lines."""
    r, g, b = (int(v) for v in rgb)
    red = r >= 120 and r - g >= 60 and r - b >= 20
    green = g >= 100 and g - r >= 45 and g - b >= -30 and b >= 40
    cyan_green = g >= 105 and b >= 95 and g - r >= 50 and b - r >= 35
    return red or green or cyan_green


def _runs(ys: list[int]) -> list[tuple[int, int]]:
    if not ys:
        return []
    out: list[tuple[int, int]] = []
    start = prev = ys[0]
    for y in ys[1:]:
        if y == prev + 1:
            prev = y
        else:
            out.append((start, prev))
            start = prev = y
    out.append((start, prev))
    return out


def _longest_run(ys: list[int]) -> tuple[int, int] | None:
    return max(_runs(ys), key=lambda q: q[1] - q[0], default=None)


def _span_iou(a: tuple[int, int], b: tuple[int, int]) -> float:
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]) + 1)
    union = max(a[1], b[1]) - min(a[0], b[0]) + 1
    return inter / union if union else 0.0


def detect_candles(path: str | Path, config: DetectorConfig = DetectorConfig()) -> Detection:
    if Image is None:
        return Detection((), False, "PIL_NOT_INSTALLED", None)
    try:
        im = Image.open(path).convert("RGB")
    except Exception as exc:
        return Detection((), False, f"IMAGE_READ_FAILED:{type(exc).__name__}", None)

    width, height = im.size
    left = max(0, config.roi_left)
    top = max(0, config.roi_top)
    right = min(width, config.roi_right if config.roi_right is not None else width - 55)
    bottom = min(height, config.roi_bottom if config.roi_bottom is not None else height - 70)
    roi = (left, top, right, bottom)
    if right - left < 100 or bottom - top < 100:
        return Detection((), False, "ROI_TOO_SMALL", roi)

    pix = im.load()
    columns: list[tuple[int, tuple[int, int]]] = []
    for x in range(left, right):
        ys = [y for y in range(top, bottom) if _candle_color(pix[x, y])]
        run = _longest_run(ys)
        if run and run[1] - run[0] + 1 >= config.min_vertical_run:
            columns.append((x, run))

    if not columns:
        return Detection((), False, "NO_CANDLE_COLOR_VERTICAL_RUNS", roi)

    # Group only adjacent columns whose main vertical spans materially overlap.
    # This prevents horizontal/diagonal overlays from welding unrelated candles.
    groups: list[list[tuple[int, tuple[int, int]]]] = []
    current: list[tuple[int, tuple[int, int]]] = [columns[0]]
    for item in columns[1:]:
        x, span = item
        prev_x, prev_span = current[-1]
        if (
            x <= prev_x + config.max_x_gap
            and _span_iou(span, prev_span) >= config.min_span_iou
        ):
            current.append(item)
        else:
            groups.append(current)
            current = [item]
    groups.append(current)

    out: list[PixelCandleCandidate] = []
    for idx, group in enumerate(groups):
        x0, x1 = group[0][0], group[-1][0]
        body_width = x1 - x0 + 1
        if body_width < 2 or body_width > config.max_body_width:
            continue

        spans = [span for _, span in group]
        high = min(a for a, _ in spans)
        low = max(bb for _, bb in spans)
        total_height = low - high + 1

        core_threshold = max(2, math.ceil(len(spans) * config.min_core_width_ratio))
        core_rows: list[int] = []
        for y in range(high, low + 1):
            covered = sum(a <= y <= bb for a, bb in spans)
            if covered >= core_threshold:
                core_rows.append(y)
        body_runs = _runs(core_rows)
        if not body_runs:
            continue

        body_top, body_bottom = max(body_runs, key=lambda q: q[1] - q[0])
        body_height = body_bottom - body_top + 1
        upper_wick = body_top - high
        lower_wick = low - body_bottom

        if body_height < config.min_body_height or total_height < config.min_total_height:
            continue
        if max(upper_wick, lower_wick) < config.min_wick_extension:
            continue
        if body_height / total_height > config.max_body_to_total_ratio:
            continue

        max_body_coverage = max(
            sum(a <= y <= bb for a, bb in spans)
            for y in range(body_top, body_bottom + 1)
        )
        coverage_ratio = max_body_coverage / len(spans)
        if coverage_ratio < config.min_body_coverage_ratio:
            continue

        confidence = min(
            0.99,
            0.72
            + min(0.10, body_height / 50)
            + min(0.10, (upper_wick + lower_wick) / 50)
            + min(0.06, coverage_ratio * 0.06),
        )
        if confidence < config.min_confidence:
            continue

        out.append(
            PixelCandleCandidate(
                idx,
                (x0 + x1) / 2,
                body_bottom,
                high,
                low,
                body_top,
                body_top,
                body_bottom,
                "unknown",
                confidence,
            )
        )

    if len(out) < 3:
        return Detection(tuple(out), False, "INSUFFICIENT_VERIFIED_CANDLE_GEOMETRY", roi)
    return Detection(tuple(out), True, "PIXEL_CANDLES_DETECTED", roi)
