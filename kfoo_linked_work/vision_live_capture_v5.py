from __future__ import annotations

import json
import os
import re

from . import vision_live_capture_v3 as v3
from . import vision_live_capture_v1 as live
from .vision_screen_reconstructor_v1 import PixelCandle, ScaleAnchor, VisionScreenReconstructorV1

_TRACE_ON = {"1", "ON", "TRUE", "YES"}


def _trace(phase: str, **extra) -> None:
    if os.getenv("GOLDBOT_VISION_TRACE", "OFF").upper() in _TRACE_ON:
        print(json.dumps({"phase": phase, **extra}, ensure_ascii=False), flush=True)


def _parse_num(text: str) -> float | None:
    s = (text or "").strip().translate(str.maketrans("٠١٢٣٤٥٦٧٨٩٬٫", "0123456789,."))
    s = s.replace("\u202a", "").replace("\u202c", "")
    m = re.search(r"[-+]?\d[\d\s,]*(?:\.\d+)?", s)
    if not m:
        return None
    token = m.group(0).replace(" ", "")
    if token.count(".") == 0 and token.count(",") == 1:
        a, b = token.split(",")
        token = a + ("." + b if len(a) <= 4 and len(b) in (1, 2, 3) else b)
    else:
        token = token.replace(",", "")
    try:
        return float(token)
    except ValueError:
        return None


def _header_ohlc(reader) -> dict[str, float] | None:
    try:
        text = reader.page.locator("body").inner_text(timeout=1000)
        lines = [x.strip().replace("\u202a", "").replace("\u202c", "") for x in text.splitlines() if x.strip()]
        out = {}
        for key in ("O", "H", "L", "C"):
            for i, line in enumerate(lines[:-1]):
                if line == key:
                    value = _parse_num(lines[i + 1])
                    if value is not None:
                        out[key.lower()] = value
                        break
        if set(out) == {"o", "h", "l", "c"} and out["h"] >= max(out["o"], out["c"]) and out["l"] <= min(out["o"], out["c"]):
            return out
    except Exception as exc:
        _trace("HEADER_OHLC_ERROR", error=f"{type(exc).__name__}:{exc}")
    return None


def _pixel(c) -> PixelCandle:
    pol = "bullish" if c.polarity == "green" else "bearish" if c.polarity == "red" else c.polarity
    return PixelCandle(c.index, c.x, c.open_y, c.high_y, c.low_y, c.close_y, c.body_top, c.body_bottom, pol, c.confidence)


def _header_match(reader, monitored):
    h = _header_ohlc(reader)
    if not h:
        return [], {"reason": "HEADER_OHLC_UNAVAILABLE"}
    span = h["h"] - h["l"]
    if span <= 0:
        return [], {"reason": "HEADER_OHLC_INVALID"}
    expected_o = (h["h"] - h["o"]) / span
    expected_c = (h["h"] - h["c"]) / span
    best = None
    for c in monitored:
        p = _pixel(c)
        py = p.low_y - p.high_y
        if py < 4 or p.high_y > min(p.open_y, p.close_y) or p.low_y < max(p.open_y, p.close_y):
            continue
        obs_o = (p.open_y - p.high_y) / py
        obs_c = (p.close_y - p.high_y) / py
        error = max(abs(obs_o - expected_o), abs(obs_c - expected_c))
        polarity_ok = (h["c"] <= h["o"] and p.polarity == "bearish") or (h["c"] >= h["o"] and p.polarity == "bullish")
        score = error + (0.25 if not polarity_ok else 0.0)
        if best is None or score < best[0]:
            best = (score, error, polarity_ok, p)
    if best is None or best[1] > 0.10 or not best[2]:
        return [], {"reason": "NO_PIXEL_CANDLE_MATCH_FOR_HEADER_OHLC", "header_ohlc": h, "best_normalized_error": best[1] if best else None}
    p = best[3]
    _trace("HEADER_OHLC_ANCHOR_MATCH", index=p.index, error=round(best[1], 6))
    return [ScaleAnchor(p.high_y, h["h"]), ScaleAnchor(p.low_y, h["l"])], {
        "reason": "HEADER_OHLC_PIXEL_ALIGNMENT_VERIFIED",
        "header_ohlc": h,
        "matched_index": p.index,
        "normalized_error": round(best[1], 6),
    }


def _verify(reader, screenshot_path, plot_rect, monitored):
    _trace("OHLC_VERIFY_START", monitored=len(monitored))
    # First use the established v3 DOM price-scale reader; then use the strict
    # visible-OHLC/pixel alignment fallback. Never fabricate anchors.
    anchors, diag = v3._read_price_scale_anchors(reader, plot_rect, screenshot_path)
    if len(anchors) < 2:
        fallback, fallback_diag = _header_match(reader, monitored)
        if len(fallback) >= 2:
            anchors, diag = fallback, {**diag, "fallback": fallback_diag, "reason": fallback_diag["reason"]}
        else:
            diag = {**diag, "fallback": fallback_diag}
    if len(anchors) < 2:
        _trace("OHLC_VERIFY_END", verified=False, anchor_count=len(anchors), reason=diag.get("reason"))
        return [], anchors, {**diag, "verified": False}
    result = VisionScreenReconstructorV1().map_ohlc([_pixel(c) for c in monitored], anchors)
    _trace("OHLC_VERIFY_END", verified=bool(result.verified), anchor_count=len(anchors), reason=result.reason)
    return list(result.ohlc), anchors, {**diag, "reconstructor_reason": result.reason, "verified": result.verified}


live._verify_ohlc_from_screen = _verify

if __name__ == "__main__":
    raise SystemExit(live.main())
