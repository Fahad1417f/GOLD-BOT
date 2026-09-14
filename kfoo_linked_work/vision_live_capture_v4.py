from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time

from . import vision_live_capture_v3 as v3
from . import vision_live_capture_v1 as live
from .vision_screen_reconstructor_v1 import PixelCandle, ScaleAnchor, VisionScreenReconstructorV1


_TRACE_ON = {"1", "ON", "TRUE", "YES"}


def _trace(phase: str, **extra) -> None:
    if os.getenv("GOLDBOT_VISION_TRACE", "OFF").upper() in _TRACE_ON:
        print(json.dumps({"phase": phase, **extra}, ensure_ascii=False), flush=True)


def _parse_num(s: str) -> float | None:
    s = (s or "").strip().translate(str.maketrans("٠١٢٣٤٥٦٧٨٩٬٫", "0123456789,."))
    s = s.replace("\u202a", "").replace("\u202c", "")
    m = re.search(r"[-+]?\d[\d\s,]*(?:\.\d+)?", s)
    if not m:
        return None
    token = m.group(0).replace(" ", "")
    if token.count(".") == 0 and token.count(",") == 1:
        left, right = token.split(",")
        token = left + ("." + right if len(left) <= 4 and len(right) in (1, 2, 3) else right)
    else:
        token = token.replace(",", "")
    try:
        return float(token)
    except ValueError:
        return None


def _read_header_ohlc(reader) -> dict[str, float] | None:
    if reader.page is None:
        return None
    try:
        text = reader.page.locator("body").inner_text(timeout=1000)
        lines = [x.strip().replace("\u202a", "").replace("\u202c", "") for x in text.splitlines() if x.strip()]
        out = {}
        for key in ("O", "H", "L", "C"):
            for i, line in enumerate(lines):
                if line == key and i + 1 < len(lines):
                    value = _parse_num(lines[i + 1])
                    if value is not None:
                        out[key.lower()] = value
                        break
        if set(out) == {"o", "h", "l", "c"} and out["h"] >= max(out["o"], out["c"]) and out["l"] <= min(out["o"], out["c"]):
            return out
    except Exception as exc:
        _trace("HEADER_OHLC_ERROR", error=f"{type(exc).__name__}:{exc}")
    return None


def _to_pixel(c) -> PixelCandle:
    polarity = "bullish" if c.polarity == "green" else "bearish" if c.polarity == "red" else c.polarity
    return PixelCandle(c.index, c.x, c.open_y, c.high_y, c.low_y, c.close_y, c.body_top, c.body_bottom, polarity, c.confidence)


def _header_anchor_match(reader, monitored):
    """Use visible TradingView OHLC only after proving one detected candle has the same normalized geometry.

    This does not fabricate a price scale. It derives two independent price anchors
    (the visible H/L values) only when a pixel candle's H/L/O/C geometry matches the
    same visible bar within a strict normalized tolerance.
    """
    header = _read_header_ohlc(reader)
    if not header or not monitored:
        return [], {"reason": "HEADER_OHLC_UNAVAILABLE"}
    span = header["h"] - header["l"]
    if span <= 0:
        return [], {"reason": "HEADER_OHLC_INVALID"}

    expected = {k: (header["h"] - header[k]) / span for k in ("o", "h", "l", "c")}
    best = None
    for c in monitored:
        p = _to_pixel(c)
        py_span = p.low_y - p.high_y
        if py_span < 4 or p.high_y > min(p.open_y, p.close_y) or p.low_y < max(p.open_y, p.close_y):
            continue
        observed = {
            "o": (p.open_y - p.high_y) / py_span,
            "h": 0.0,
            "l": 1.0,
            "c": (p.close_y - p.high_y) / py_span,
        }
        error = max(abs(observed[k] - expected[k]) for k in ("o", "c"))
        polarity_ok = (header["c"] < header["o"] and p.polarity == "bearish") or (header["c"] > header["o"] and p.polarity == "bullish") or (abs(header["c"] - header["o"]) < 1e-9)
        score = error + (0.25 if not polarity_ok else 0.0)
        if best is None or score < best[0]:
            best = (score, error, polarity_ok, p)

    if best is None or best[1] > 0.10 or not best[2]:
        return [], {"reason": "NO_PIXEL_CANDLE_MATCH_FOR_HEADER_OHLC", "header_ohlc": header, "best_error": best[1] if best else None}

    p = best[3]
    anchors = [ScaleAnchor(p.high_y, header["h"]), ScaleAnchor(p.low_y, header["l"])]
    _trace("HEADER_OHLC_ANCHOR_MATCH", index=p.index, error=round(best[1], 4), high_y=p.high_y, low_y=p.low_y)
    return anchors, {"reason": "HEADER_OHLC_PIXEL_ALIGNMENT_VERIFIED", "header_ohlc": header, "matched_index": p.index, "normalized_error": round(best[1], 6)}


def _ocr_scale_anchors(screenshot_path: str, plot_rect):
    exe = shutil.which("tesseract")
    if not exe:
        return [], {"reason": "TESSERACT_NOT_INSTALLED"}
    try:
        from PIL import Image
        with Image.open(screenshot_path) as im:
            sw, sh = im.size
            x0, y0, x1, y1 = [int(v) for v in plot_rect]
            left = max(0, min(sw - 1, int(x0 * 0.88)))
            top = max(0, min(sh - 1, int(y0 * 0.98)))
            right = sw
            bottom = min(sh, int(y1 * 1.02))
            crop = im.crop((left, top, right, bottom))
            tmp = str(screenshot_path) + ".scale_ocr.png"
            crop.save(tmp)
        cmd = [exe, tmp, "stdout", "--psm", "6", "-c", "tessedit_char_whitelist=0123456789.,-", "tsv"]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="backslashreplace", timeout=2)
        anchors = []
        for line in proc.stdout.splitlines()[1:]:
            cols = line.split("\t")
            if len(cols) < 12:
                continue
            text = cols[11].strip()
            price = _parse_num(text)
            if price is None or price < 1000:
                continue
            try:
                top_box = float(cols[7]); height = float(cols[9])
            except ValueError:
                continue
            y = top + top_box + height / 2.0
            if y0 <= y <= y1:
                anchors.append(ScaleAnchor(y, price))
        try:
            os.remove(tmp)
        except OSError:
            pass
        anchors = sorted(anchors, key=lambda a: a.y)
        pair = None
        for a, b in zip(anchors, anchors[1:]):
            if b.y - a.y >= 10 and b.price < a.price:
                pair = (a, b)
                break
        if pair:
            return [pair[0], pair[1]], {"reason": "OCR_SCALE_ANCHORS_FOUND", "candidate_count": len(anchors)}
        return [], {"reason": "OCR_NO_MONOTONIC_PRICE_PAIR", "candidate_count": len(anchors)}
    except Exception as exc:
        return [], {"reason": f"OCR_SCALE_READ_FAILED:{type(exc).__name__}:{exc}"}


def _verify_ohlc(reader, screenshot_path, plot_rect, monitored):
    anchors, diagnostics = _header_anchor_match(reader, monitored)
    if len(anchors) < 2:
        ocr_anchors, ocr_diag = _ocr_scale_anchors(screenshot_path, plot_rect)
        if len(ocr_anchors) >= 2:
            anchors = ocr_anchors
            diagnostics = {**diagnostics, "ocr_fallback": ocr_diag, "reason": ocr_diag["reason"]}
        else:
            diagnostics = {**diagnostics, "ocr_fallback": ocr_diag, "reason": diagnostics.get("reason", "TWO_DISTINCT_SCALE_ANCHORS_REQUIRED")}
    if len(anchors) < 2:
        return [], anchors, {**diagnostics, "verified": False}
    result = VisionScreenReconstructorV1().map_ohlc([_to_pixel(c) for c in monitored], anchors)
    diagnostics = {**diagnostics, "reconstructor_reason": result.reason, "verified": result.verified}
    return list(result.ohlc), anchors, diagnostics


live._verify_ohlc_from_screen = _verify_ohlc

if __name__ == "__main__":
    raise SystemExit(live.main())
