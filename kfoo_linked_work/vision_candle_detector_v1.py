"""Read-only TradingView screenshot candle geometry detector.

The detector proposes pixel geometry only. It never converts pixels to price,
never infers OHLC, and fails closed when candle geometry is not sufficiently
distinct from overlays, labels, or indicator panes.
"""
from __future__ import annotations

import math
import statistics
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
    price_pane_ratio: float = 0.62
    min_body_height: int = 4
    min_body_run_width: int = 4
    max_body_width: int = 18
    min_confidence: float = 0.78
    min_wick_extension: int = 1
    min_total_height: int = 5
    max_wick_extension: int = 120
    min_body_row_coverage: float = 0.70
    body_span_overlap: float = 0.75
    min_series_length: int = 5
    max_series_gap: float = 60.0
    series_gap_lower_ratio: float = 0.72
    series_gap_upper_ratio: float = 1.35
    body_width_tolerance: float = 1.45
    max_candle_count: int = 24
    max_row_gap: int = 1


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


def _kind(rgb: tuple[int, int, int]) -> str | None:
    r, g, b = (int(v) for v in rgb)
    red = r >= 145 and r - g >= 65 and r - b >= 35 and g <= 100
    green = g >= 120 and g - r >= 55 and g - b >= 25 and r <= 90
    if red and green:
        return "red" if r > g else "green"
    if red:
        return "red"
    if green:
        return "green"
    return None


def _runs(values: list[int]) -> list[tuple[int, int]]:
    if not values:
        return []
    out: list[tuple[int, int]] = []
    start = prev = values[0]
    for value in values[1:]:
        if value == prev + 1:
            prev = value
        else:
            out.append((start, prev))
            start = prev = value
    out.append((start, prev))
    return out


def _longest_run(values: list[int]) -> tuple[int, int] | None:
    return max(_runs(values), key=lambda item: item[1] - item[0], default=None)


def _tolerant_run(values: list[int], max_gap: int) -> tuple[int, int] | None:
    """Return the longest span while tolerating tiny gridline/anti-alias gaps."""
    if not values:
        return None
    start = prev = values[0]
    best = (start, start)
    for value in values[1:]:
        if value - prev <= max_gap + 1:
            prev = value
            if prev - start > best[1] - best[0]:
                best = (start, prev)
        else:
            start = prev = value
    return best


def _price_pane_bottom(top: int, bottom: int, ratio: float) -> int:
    ratio = min(0.78, max(0.52, float(ratio)))
    return top + int(round((bottom - top) * ratio))


def _row_runs(pix, left, top, right, bottom, min_width, max_width):
    rows = {}
    for y in range(top, bottom):
        current = []
        x = left
        while x < right:
            kind = _kind(pix[x, y])
            if kind is None:
                x += 1
                continue
            start = x
            x += 1
            while x < right and _kind(pix[x, y]) == kind:
                x += 1
            end = x - 1
            width = end - start + 1
            if min_width <= width <= max_width:
                current.append((start, end, kind))
        if current:
            rows[y] = current
    return rows


def _extract_body_groups(rows, min_overlap, max_row_gap=1):
    """Group body strips while tolerating a one-pixel gridline crossing a body."""
    groups = []
    for y in sorted(rows):
        for start, end, kind in rows[y]:
            best = None
            best_overlap = 0.0
            for group in groups:
                if group["kind"] != kind or y - group["last_y"] > max_row_gap + 1:
                    continue
                gs, ge = group["last_span"]
                intersection = max(0, min(end, ge) - max(start, gs) + 1)
                overlap = intersection / max(1, min(end - start + 1, ge - gs + 1))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best = group
            if best is not None and best_overlap >= min_overlap:
                best["last_y"] = y
                best["last_span"] = (start, end)
                best["ys"].append(y)
                best["spans"].append((start, end))
                best["x0"] = min(best["x0"], start)
                best["x1"] = max(best["x1"], end)
            else:
                groups.append({"last_y": y, "last_span": (start, end), "ys": [y], "spans": [(start, end)], "x0": start, "x1": end, "kind": kind})
    return groups


def _center_color_run(pix, center_x, high, low, kind, max_gap=1):
    values = [y for y in range(high, low + 1) if _kind(pix[center_x, y]) == kind]
    return _tolerant_run(values, max_gap)


def _raw_candidates(pix, rows, config, top, bottom):
    candidates = []
    for group_index, group in enumerate(_extract_body_groups(rows, config.body_span_overlap, config.max_row_gap)):
        body_top = min(group["ys"])
        body_bottom = max(group["ys"])
        body_height = body_bottom - body_top + 1
        coverage = len(group["ys"]) / max(1, body_height)
        if body_height < config.min_body_height or coverage < config.min_body_row_coverage:
            continue
        x0, x1 = group["x0"], group["x1"]
        body_width = x1 - x0 + 1
        if not config.min_body_run_width <= body_width <= config.max_body_width:
            continue
        widths = [end - start + 1 for start, end in group["spans"]]
        median_width = statistics.median(widths)
        if not config.min_body_run_width <= median_width <= config.max_body_width:
            continue
        width_ratio = max(widths) / max(1, min(widths))
        if width_ratio > config.body_width_tolerance:
            continue
        center_x = int(round((x0 + x1) / 2))
        center_run = _center_color_run(pix, center_x, max(top, body_top - config.max_wick_extension), min(bottom - 1, body_bottom + config.max_wick_extension), group["kind"], config.max_row_gap)
        if center_run is None:
            continue
        high, low = center_run
        if high > body_top or low < body_bottom:
            continue
        upper_wick = body_top - high
        lower_wick = low - body_bottom
        total_height = low - high + 1
        if total_height < config.min_total_height or max(upper_wick, lower_wick) > config.max_wick_extension:
            continue
        if max(upper_wick, lower_wick) < config.min_wick_extension and body_height < 5:
            continue
        polarity = group["kind"]
        open_y, close_y = ((body_bottom, body_top) if polarity == "green" else (body_top, body_bottom))
        confidence = min(0.995, 0.76 + min(0.10, body_height / 60) + min(0.08, (upper_wick + lower_wick) / 60) + min(0.055, coverage * 0.055) + min(0.03, max(0.0, 1.0 - (width_ratio - 1.0)) * 0.03))
        if confidence < config.min_confidence:
            continue
        candidates.append(PixelCandleCandidate(group_index, (x0 + x1) / 2, open_y, high, low, close_y, body_top, body_bottom, polarity, confidence))
    return candidates


def _dedupe_by_x(candidates):
    ordered = sorted(candidates, key=lambda c: c.x)
    if not ordered:
        return []
    clusters = [[ordered[0]]]
    for candle in ordered[1:]:
        if candle.x - clusters[-1][-1].x <= 7.0:
            clusters[-1].append(candle)
        else:
            clusters.append([candle])
    return sorted((max(cluster, key=lambda c: (c.confidence, c.body_bottom - c.body_top)) for cluster in clusters), key=lambda c: c.x)


def _best_series(candidates, config):
    candidates = _dedupe_by_x(candidates)
    if len(candidates) < config.min_series_length:
        return []
    ordered = sorted(candidates, key=lambda c: c.x)
    gaps = [ordered[i + 1].x - ordered[i].x for i in range(len(ordered) - 1)]
    gaps = [g for g in gaps if 0 < g <= config.max_series_gap]
    if not gaps:
        return []
    median_gap = statistics.median(gaps)
    pitch_samples = [g for g in gaps if abs(g - median_gap) <= max(3.0, median_gap * 0.35)]
    pitch = statistics.median(pitch_samples or gaps)
    low = max(5.0, pitch * config.series_gap_lower_ratio)
    high = pitch * config.series_gap_upper_ratio
    chains = []
    current = [ordered[0]]
    for prev, cur in zip(ordered, ordered[1:]):
        gap = cur.x - prev.x
        if low <= gap <= high:
            current.append(cur)
        else:
            if len(current) >= config.min_series_length:
                chains.append(current)
            current = [cur]
    if len(current) >= config.min_series_length:
        chains.append(current)
    if not chains:
        return []
    def chain_score(chain):
        gaps_chain = [b.x - a.x for a, b in zip(chain, chain[1:])]
        dispersion = statistics.pstdev(gaps_chain) if len(gaps_chain) > 1 else 0.0
        alternation = sum(a.polarity != b.polarity for a, b in zip(chain, chain[1:]))
        return (len(chain), -dispersion, alternation / max(1, len(chain) - 1))
    best = max(chains, key=chain_score)
    median_height = statistics.median(max(1.0, c.body_bottom - c.body_top + 1) for c in best)
    filtered = [c for c in best if c.body_bottom - c.body_top + 1 <= median_height * 2.5 + 2]
    return sorted(filtered[-config.max_candle_count:], key=lambda c: c.x)


def detect_candles(path: str | Path, config: DetectorConfig = DetectorConfig()) -> Detection:
    if Image is None:
        return Detection((), False, "PIL_NOT_INSTALLED", None)
    try:
        image = Image.open(path).convert("RGB")
    except Exception as exc:
        return Detection((), False, f"IMAGE_READ_FAILED:{type(exc).__name__}", None)
    width, height = image.size
    left = max(0, config.roi_left)
    top = max(0, config.roi_top)
    right = min(width, config.roi_right if config.roi_right is not None else width - 55)
    raw_bottom = min(height, config.roi_bottom if config.roi_bottom is not None else height - 70)
    bottom = min(raw_bottom, _price_pane_bottom(top, raw_bottom, config.price_pane_ratio))
    roi = (left, top, right, bottom)
    if right - left < 100 or bottom - top < 80:
        return Detection((), False, "ROI_TOO_SMALL", roi)
    pix = image.load()
    rows = _row_runs(pix, left, top, right, bottom, config.min_body_run_width, config.max_body_width)
    if not rows:
        return Detection((), False, "NO_CANDLE_BODY_ROWS", roi)
    raw = _raw_candidates(pix, rows, config, top, bottom)
    retained = _best_series(raw, config)
    if len(retained) < config.min_series_length:
        return Detection(tuple(retained), False, "INSUFFICIENT_VERIFIED_CANDLE_GEOMETRY", roi)
    return Detection(tuple(retained), True, "PIXEL_CANDLES_DETECTED", roi)
