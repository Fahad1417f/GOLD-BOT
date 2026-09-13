"""Read-only TradingView screenshot candle geometry detector.

No price/OHLC values are inferred here. The detector only proposes pixel candles.
Verification is fail-closed and rejects overlays/indicator panes using local
candle geometry plus a center-column continuity check and candle-series spacing.
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
    # The screenshot canvas can include a lower indicator pane. Limit the
    # detector to the upper price pane without inferring any price values.
    price_pane_ratio: float = 0.70
    min_body_height: int = 2
    min_body_width: int = 2
    max_body_width: int = 18
    min_confidence: float = 0.72
    min_wick_extension: int = 2
    min_total_height: int = 5
    min_core_width_ratio: float = 0.50
    max_body_to_total_ratio: float = 0.92
    min_vertical_run: int = 6
    min_span_iou: float = 0.50
    max_x_gap: int = 1
    min_body_coverage_ratio: float = 0.60
    min_center_run_coverage: float = 0.65
    min_center_body_coverage: float = 0.90
    max_series_gap: float = 40.0
    series_gap_lower_ratio: float = 0.45
    series_gap_upper_ratio: float = 1.75
    min_series_length: int = 5


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
    """Recognize TradingView red/green candle colors while rejecting orange/yellow lines."""
    r, g, b = (int(v) for v in rgb)

    # Strong red/pink dominance. Keep the g==0 case explicit so black pixels
    # cannot become red merely because the ratio denominator is zero.
    red = (
        r >= 140
        and r - g >= 90
        and r - b >= 70
        and (g == 0 or r >= int(g * 1.65))
    )

    # Saturated green candle colors.
    green = (
        g >= 105
        and g - r >= 70
        and b >= 40
        and g >= int(b * 0.90)
    )

    # Cyan-green candle variants used by some TradingView themes.
    cyan_green = (
        g >= 105
        and b >= 95
        and g - r >= 50
        and b - r >= 35
        and g >= int(b * 0.90)
    )
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


def _price_pane_bottom(top: int, bottom: int, ratio: float) -> int:
    ratio = min(0.90, max(0.55, float(ratio)))
    return top + int(round((bottom - top) * ratio))


def _retain_series(candidates: list[PixelCandleCandidate], config: DetectorConfig) -> list[PixelCandleCandidate]:
    """Keep dense, regularly spaced x-series and reject isolated overlay shapes."""
    if len(candidates) < config.min_series_length:
        return []
    ordered = sorted(candidates, key=lambda c: c.x)
    gaps = [ordered[i + 1].x - ordered[i].x for i in range(len(ordered) - 1)]
    usable = [g for g in gaps if 0 < g <= config.max_series_gap]
    if not usable:
        return []
    pitch = sorted(usable)[len(usable) // 2]
    if pitch <= 0:
        return []

    low = pitch * config.series_gap_lower_ratio
    high = pitch * config.series_gap_upper_ratio
    chains: list[list[PixelCandleCandidate]] = []
    current = [ordered[0]]
    for cur, gap in zip(ordered[1:], gaps):
        if low <= gap <= high:
            current.append(cur)
        else:
            if len(current) >= config.min_series_length:
                chains.append(current)
            current = [cur]
    if len(current) >= config.min_series_length:
        chains.append(current)

    kept = [c for chain in chains for c in chain]
    return sorted(kept, key=lambda c: c.x)


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
    raw_bottom = min(height, config.roi_bottom if config.roi_bottom is not None else height - 70)
    bottom = min(raw_bottom, _price_pane_bottom(top, raw_bottom, config.price_pane_ratio))
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

    groups: list[list[tuple[int, tuple[int, int]]]] = []
    current: list[tuple[int, tuple[int, int]]] = [columns[0]]
    for item in columns[1:]:
        x, span = item
        prev_x, prev_span = current[-1]
        if x <= prev_x + config.max_x_gap and _span_iou(span, prev_span) >= config.min_span_iou:
            current.append(item)
        else:
            groups.append(current)
            current = [item]
    groups.append(current)

    raw_candidates: list[PixelCandleCandidate] = []
    for idx, group in enumerate(groups):
        x0, x1 = group[0][0], group[-1][0]
        body_width = x1 - x0 + 1
        if body_width < config.min_body_width or body_width > config.max_body_width:
            continue

        spans = [span for _, span in group]
        high = min(a for a, _ in spans)
        low = max(bb for _, bb in spans)
        total_height = low - high + 1
        if total_height < config.min_total_height:
            continue

        core_threshold = max(2, math.ceil(len(spans) * config.min_core_width_ratio))
        core_rows = [
            y
            for y in range(high, low + 1)
            if sum(a <= y <= bb for a, bb in spans) >= core_threshold
        ]
        body_runs = _runs(core_rows)
        if not body_runs:
            continue

        body_top, body_bottom = max(body_runs, key=lambda q: q[1] - q[0])
        body_height = body_bottom - body_top + 1
        upper_wick = body_top - high
        lower_wick = low - body_bottom
        if body_height < config.min_body_height:
            continue
        if max(upper_wick, lower_wick) < config.min_wick_extension:
            continue
        if body_height / total_height > config.max_body_to_total_ratio:
            continue

        body_coverage = max(
            sum(a <= y <= bb for a, bb in spans)
            for y in range(body_top, body_bottom + 1)
        ) / len(spans)
        if body_coverage < config.min_body_coverage_ratio:
            continue

        center_x = int(round((x0 + x1) / 2))
        center_run = _longest_run([y for y in range(high, low + 1) if _candle_color(pix[center_x, y])])
        if center_run is None:
            continue
        center_a, center_b = center_run
        center_overlap = sum(center_a <= y <= center_b for y in range(high, low + 1))
        center_body_overlap = sum(center_a <= y <= center_b for y in range(body_top, body_bottom + 1))
        if center_overlap / total_height < config.min_center_run_coverage:
            continue
        if center_body_overlap / body_height < config.min_center_body_coverage:
            continue

        confidence = min(
            0.99,
            0.72
            + min(0.10, body_height / 50)
            + min(0.10, (upper_wick + lower_wick) / 50)
            + min(0.06, body_coverage * 0.06)
            + min(0.03, (center_overlap / total_height) * 0.03),
        )
        if confidence < config.min_confidence:
            continue

        raw_candidates.append(
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

    out = _retain_series(raw_candidates, config)
    if len(out) < 3:
        return Detection(tuple(out), False, "INSUFFICIENT_VERIFIED_CANDLE_GEOMETRY", roi)
    return Detection(tuple(out), True, "PIXEL_CANDLES_DETECTED", roi)
