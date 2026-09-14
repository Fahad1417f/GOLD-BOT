from __future__ import annotations

import json
import os

try:
    from .playwright_chart_reader import PlaywrightChartReader
    from .vision_candle_detector_v1 import detect_candles, DetectorConfig
except ImportError:
    from playwright_chart_reader import PlaywrightChartReader
    from vision_candle_detector_v1 import detect_candles, DetectorConfig


def _candle_limit() -> int:
    """Limit visual candle monitoring depth; KFOO itself remains the signal source."""
    raw = os.getenv("GOLDBOT_VISION_CANDLE_LIMIT", "24").strip()
    try:
        return max(3, min(60, int(raw)))
    except ValueError:
        return 24


def _limit_recent_candles(candles):
    """Keep only the most recent x-ordered candidates for live monitoring."""
    limit = _candle_limit()
    ordered = sorted(candles, key=lambda candle: candle.x)
    return ordered[-limit:]


def _build_vision_gate(data: dict) -> dict:
    """Combine chart identity, visual geometry, OHLC and KFOO readiness without promoting pixels to prices."""
    kfoo = data.get("kfoo") if isinstance(data.get("kfoo"), dict) else {}
    visual = kfoo.get("visual_monitoring") if isinstance(kfoo.get("visual_monitoring"), dict) else {}
    identity_verified = bool(data.get("capture_verified"))
    geometry_verified = bool(data.get("pixel_candles_available")) and int(data.get("pixel_candle_count") or 0) >= 3
    ohlc_verified = bool(data.get("ohlc_verified"))
    kfoo_present = bool(kfoo.get("present"))
    kfoo_signal_ready = bool(
        kfoo_present
        and kfoo.get("active_15m") not in (None, "", "unknown")
        and kfoo.get("direction_15m") in ("long", "short", "bullish", "bearish")
        and kfoo.get("table_15m") not in (None, "", "—", "-")
    )
    monitoring_ready = identity_verified and geometry_verified
    decision_input_ready = identity_verified and geometry_verified and ohlc_verified and kfoo_signal_ready
    return {
        "identity_verified": identity_verified,
        "pixel_geometry_verified": geometry_verified,
        "ohlc_verified": ohlc_verified,
        "kfoo_signal_ready": kfoo_signal_ready,
        "monitoring_ready": monitoring_ready,
        "decision_input_ready": decision_input_ready,
        "execution_allowed": False,
        "reason": "READY_FOR_MONITORING_ONLY" if monitoring_ready and not decision_input_ready else ("READY_FOR_DECISION_INPUT" if decision_input_ready else "VISION_GATE_INCOMPLETE"),
    }


def _roi_from_plot(reader, screenshot_path, plot_rect):
    if not plot_rect or not screenshot_path or reader.page is None:
        return DetectorConfig(max_candle_count=_candle_limit())
    try:
        from PIL import Image

        with Image.open(screenshot_path) as im:
            sw, sh = im.size
        viewport = reader.page.evaluate("() => ({w:innerWidth,h:innerHeight})")
        sx = sw / float(viewport["w"])
        sy = sh / float(viewport["h"])
        x0, y0, x1, y1 = map(float, plot_rect)
        return DetectorConfig(
            roi_left=max(0, round(x0 * sx)),
            roi_top=max(0, round(y0 * sy)),
            roi_right=min(sw, round(x1 * sx)),
            roi_bottom=min(sh, round(y1 * sy)),
            max_candle_count=_candle_limit(),
        )
    except Exception:
        return DetectorConfig(max_candle_count=_candle_limit())


def capture_once(cdp_url: str | None = None, output_dir: str = "artifacts/vision") -> dict:
    reader = PlaywrightChartReader(cdp_url=cdp_url, screenshot_dir=output_dir)
    try:
        result = reader.connect()
        if not result.connected:
            return result.to_dict()

        result.screenshot_path = reader.capture("tradingview_live.png")
        data = result.to_dict()
        config = _roi_from_plot(reader, result.screenshot_path, result.plot_rect)
        detection = detect_candles(result.screenshot_path, config)
        monitored = _limit_recent_candles(detection.candles)
        data["pixel_candles_available"] = bool(detection.verified and monitored)
        data["pixel_candle_count"] = len(monitored)
        data["pixel_candle_limit"] = config.max_candle_count
        data["pixel_candle_raw_count"] = len(detection.candles)
        data["pixel_candle_reason"] = detection.reason
        data["pixel_candle_roi"] = detection.roi
        data["pixel_candles"] = [
            {
                "index": c.index,
                "x": c.x,
                "open_y": c.open_y,
                "high_y": c.high_y,
                "low_y": c.low_y,
                "close_y": c.close_y,
                "body_top": c.body_top,
                "body_bottom": c.body_bottom,
                "polarity": c.polarity,
                "confidence": c.confidence,
            }
            for c in monitored
        ]
        data["ohlc_verified"] = False
        data["ohlc_reason"] = "PRICE_SCALE_ANCHORS_NOT_VERIFIED"
        data["capture_verified"] = bool(
            result.connected and result.symbol and result.timeframe and result.screenshot_path
        )
        data["vision_gate"] = _build_vision_gate(data)
        return data
    finally:
        reader.close()


def main(capture_fn=None) -> int:
    """CLI entrypoint; accepts an injectable capture function for deterministic tests."""
    fn = capture_once if capture_fn is None else capture_fn
    data = fn(os.getenv("TRADINGVIEW_CDP_URL"))
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0 if data.get("capture_verified") else 2


if __name__ == "__main__":
    raise SystemExit(main())
