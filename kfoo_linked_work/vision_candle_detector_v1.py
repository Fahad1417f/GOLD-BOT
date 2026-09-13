"""Read-only TradingView screenshot candle geometry detector.

The detector proposes only pixel geometry. It never converts pixels to price,
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
    price_pane_ratio: float = 0.70

    min_body_height: int = 4
    min_body_run_width: int = 4
    max_body_width: int = 18
    min_confidence: float = 0.72

    min_wick_extension: int = 1
    min_total_height: int = 5
    max_wick_extension: int = 180

    min_body_row_coverage: float = 0.65
    min_mean_body_row_coverage: float = 0.80
    body_span_overlap: float = 0.60
    max_body_aspect_ratio: float = 35.0

    min_series_length: int = 3
    max_series_gap: float = 100.0
    series_gap_lower_ratio: float = 0.55
    series_gap_upper_ratio: float = 1.55
    series_pitch_width_ratio: float = 0.004
    body_width_tolerance: float = 1.8


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
    """Recognize saturated TradingView candle colors and reject orange/yellow overlays."""
    r, g, b = (int(v) for v in rgb)
    red = r >= 140 and r - g >= 55 and r - b >= 20 and g <= 110
    green = g >= 110 and g - r >= 45 and b >= 35
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


def _price_pane_bottom(top: int, bottom: int, ratio: float) -> int:
    ratio = min(0.90, max(0.55, float(ratio)))
    return top + int(round((bottom - top) * ratio))


def _row_runs(
    pix,
    left: int,
    top: int,
    right: int,
    bottom: int,
    min_width: int,
    max_width: int,
) -> dict[int, list[tuple[int, int, str]]]:
    rows: dict[int, list[tuple[int, int, str]]] = {}
    for y in range(top, bottom):
        current: list[tuple[int, int, str]] = []
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
            run_width = end - start + 1
            if min_width <= run_width <= max_width:
                current.append((start, end, kind))
        if current:
            rows[y] = current
    return rows


def _extract_body_groups(
    rows: dict[int, list[tuple[int, int, str]]],
    min_overlap: float,
) -> list[dict]:
    active: list[dict] = []
    groups: list[dict] = []
    for y in sorted(rows):
        new_active: list[dict] = []
        for start, end, kind in rows[y]:
            best: dict | None = None
            best_overlap = 0.0
            for group in active:
                if group["last_y"] != y - 1 or group["kind"] != kind:
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
                new_active.append(
                    {
                        "last_y": y,
                        "last_span": (start, end),
                        "ys": [y],
                        "spans": [(start, end)],
                        "x0": start,
                        "x1": end,
                        "kind": kind,
                    }
                )
        groups.extend(group for group in active if group["last_y"] < y)
        active = [group for group in active if group["last_y"] == y] + new_active
    groups.extend(active)
    return groups


def _center_color_run(
    pix,
    center_x: int,
    high: int,
    low: int,
    kind: str,
) -> tuple[int, int] | None:
    values = [y for y in range(high, low + 1) if _kind(pix[center_x, y]) == kind]
    return _longest_run(values)


def _raw_candidates(
    pix,
    rows: dict[int, list[tuple[int, int, str]]],
    config: DetectorConfig,
    top: int,
    bottom: int,
) -> list[PixelCandleCandidate]:
    candidates: list[PixelCandleCandidate] = []
    for group_index, group in enumerate(_extract_body_groups(rows, config.body_span_overlap)):
        body_top = min(group["ys"])
        body_bottom = max(group["ys"])
        body_height = body_bottom - body_top + 1
        if body_height < config.min_body_height:
            continue
        if len(group["ys"]) < math.ceil(body_height * config.min_body_row_coverage):
            continue

        x0, x1 = group["x0"], group["x1"]
        body_width = x1 - x0 + 1
        if not (config.min_body_run_width <= body_width <= config.max_body_width):
            continue

        widths = [end - start + 1 for start, end in group["spans"]]
        if statistics.median(widths) < config.min_body_run_width:
            continue
        width_median = statistics.median(widths)
        if max(widths) / max(1.0, min(widths)) > config.body_width_tolerance:
            continue

        center_x = int(round((x0 + x1) / 2))
        center_run = _center_color_run(
            pix,
            center_x,
            max(top, body_top - config.max_wick_extension),
            min(bottom - 1, body_bottom + config.max_wick_extension),
            group["kind"],
        )
        if center_run is None:
            continue

        high, low = center_run
        if high > body_top or low < body_bottom:
            continue

        upper_wick = body_top - high
        lower_wick = low - body_bottom
        total_height = low - high + 1
        if total_height < config.min_total_height:
            continue
        if max(upper_wick, lower_wick) < config.min_wick_extension and body_height < 5:
            continue
        if max(upper_wick, lower_wick) > config.max_wick_extension:
            continue
        if body_height / max(1, body_width) > config.max_body_aspect_ratio:
            continue

        row_coverages = [
            sum(a <= y <= bb for a, bb in group["spans"]) / len(group["spans"])
            for y in range(body_top, body_bottom + 1)
        ]
        if max(row_coverages) < config.min_body_row_coverage:
            continue
        if sum(row_coverages) / len(row_coverages) < config.min_mean_body_row_coverage:
            continue

        polarity = group["kind"]
        if polarity == "green":
            open_y, close_y = body_bottom, body_top
        else:
            open_y, close_y = body_top, body_bottom

        confidence = min(
            0.99,
            0.74
            + min(0.10, body_height / 50)
            + min(0.10, (upper_wick + lower_wick) / 50)
            + min(0.05, (sum(row_coverages) / len(row_coverages)) * 0.05)
            + min(0.02, width_median / 100),
        )
        if confidence < config.min_confidence:
            continue

        candidates.append(
            PixelCandleCandidate(
                group_index,
                (x0 + x1) / 2,
                open_y,
                high,
                low,
                close_y,
                body_top,
                body_bottom,
                polarity,
                confidence,
            )
        )
    return candidates


def _retain_series(
    candidates: list[PixelCandleCandidate],
    config: DetectorConfig,
    roi_width: int,
) -> list[PixelCandleCandidate]:
    """Keep the dominant, adequately spaced candle chain and reject overlay clusters."""
    if len(candidates) < config.min_series_length:
        return []
    ordered = sorted(candidates, key=lambda candle: candle.x)
    all_gaps = [ordered[i + 1].x - ordered[i].x for i in range(len(ordered) - 1)]
    gaps = [g for g in all_gaps if 0 < g <= config.max_series_gap]
    if not gaps:
        return []

    # Avoid choosing the tiny 10-15 px spacing commonly produced by text/box
    # overlays on Retina screenshots. A real candle series must occupy a
    # material fraction of the chart width per candle pitch.
    pitch = statistics.median(gaps)
    min_pitch = roi_width * config.series_pitch_width_ratio
    if pitch < min_pitch:
        # Try larger gaps as the true bar pitch when the smallest-gap cluster
        # is clearly too dense to be the TradingView candle series.
        larger = [g for g in gaps if g >= min_pitch]
        if not larger:
            return []
        pitch = statistics.median(larger)

    low = pitch * config.series_gap_lower_ratio
    high = pitch * config.series_gap_upper_ratio
    chains: list[list[PixelCandleCandidate]] = []
    for start_index, first in enumerate(ordered):
        current = [first]
        for candidate in ordered[start_index + 1 :]:
            gap = candidate.x - current[-1].x
            if low <= gap <= high:
                current.append(candidate)
            elif gap > high:
                if len(current) >= config.min_series_length:
                    chains.append(current)
                break
        if len(current) >= config.min_series_length:
            chains.append(current)

    if not chains:
        return []

    def score(chain: list[PixelCandleCandidate]) -> tuple[int, float, float, float]:
        chain_gaps = [chain[i + 1].x - chain[i].x for i in range(len(chain) - 1)]
        deviation = statistics.mean(abs(g - pitch) for g in chain_gaps) if chain_gaps else float("inf")
        span_ratio = (chain[-1].x - chain[0].x) / max(1.0, roi_width)
        color_diversity = len({c.polarity for c in chain})
        return len(chain), span_ratio, color_diversity, -deviation

    return sorted(max(chains, key=score), key=lambda candle: candle.x)


def detect_candles(
    path: str | Path,
    config: DetectorConfig = DetectorConfig(),
) -> Detection:
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
    if right - left < 100 or bottom - top < 100:
        return Detection((), False, "ROI_TOO_SMALL", roi)

    pix = image.load()
    rows = _row_runs(pix, left, top, right, bottom, config.min_body_run_width, config.max_body_width)
    if not rows:
        return Detection((), False, "NO_CANDLE_BODY_ROWS", roi)

    raw = _raw_candidates(pix, rows, config, top, bottom)
    retained = _retain_series(raw, config, right - left)
    if len(retained) < config.min_series_length:
        return Detection(tuple(retained), False, "INSUFFICIENT_VERIFIED_CANDLE_GEOMETRY", roi)
    return Detection(tuple(retained), True, "PIXEL_CANDLES_DETECTED", roi)
