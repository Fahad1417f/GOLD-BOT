from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

try:
    from .playwright_chart_reader import PlaywrightChartReader
    from .vision_candle_detector_v1 import detect_candles, DetectorConfig
except ImportError:
    from playwright_chart_reader import PlaywrightChartReader
    from vision_candle_detector_v1 import detect_candles, DetectorConfig


def _candle_limit() -> int:
    raw = os.getenv("GOLDBOT_VISION_CANDLE_LIMIT", "24").strip()
    try:
        return max(3, min(60, int(raw)))
    except ValueError:
        return 24


def _monitor_interval() -> float:
    raw = os.getenv("GOLDBOT_VISION_INTERVAL_SECONDS", "15").strip()
    try:
        return max(3.0, min(300.0, float(raw)))
    except ValueError:
        return 15.0


def _limit_recent_candles(candles):
    limit = _candle_limit()
    ordered = sorted(candles, key=lambda candle: candle.x)
    return ordered[-limit:]


def _build_vision_gate(data: dict) -> dict:
    kfoo = data.get("kfoo") if isinstance(data.get("kfoo"), dict) else {}
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
        data["capture_verified"] = bool(result.connected and result.symbol and result.timeframe and result.screenshot_path)
        data["vision_gate"] = _build_vision_gate(data)
        return data
    finally:
        reader.close()


def _write_state(data: dict, output_dir: str) -> None:
    path = Path(output_dir) / "live_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _run_loop(cdp_url: str | None, output_dir: str, interval: float) -> int:
    print("VISION_CONTINUOUS=ON")
    print("EXECUTION=OFF")
    print(f"INTERVAL_SECONDS={interval:g}")
    while True:
        try:
            data = capture_once(cdp_url, output_dir)
            _write_state(data, output_dir)
            gate = data.get("vision_gate") or {}
            summary = {
                "connected": data.get("connected"),
                "verified": data.get("verified"),
                "capture_verified": data.get("capture_verified"),
                "symbol": data.get("symbol"),
                "timeframe": data.get("timeframe"),
                "kfoo_present": (data.get("kfoo") or {}).get("present"),
                "kfoo_signal_ready": gate.get("kfoo_signal_ready"),
                "pixel_geometry_verified": gate.get("pixel_geometry_verified"),
                "ohlc_verified": gate.get("ohlc_verified"),
                "pixel_candles": data.get("pixel_candle_count", 0),
                "vision_reason": gate.get("reason") or data.get("reason"),
            }
            print(json.dumps(summary, ensure_ascii=False), flush=True)
        except KeyboardInterrupt:
            print("VISION_CONTINUOUS=STOP")
            return 0
        except Exception as exc:
            error = {
                "connected": False,
                "verified": False,
                "capture_verified": False,
                "vision_gate": {
                    "identity_verified": False,
                    "pixel_geometry_verified": False,
                    "ohlc_verified": False,
                    "kfoo_signal_ready": False,
                    "monitoring_ready": False,
                    "decision_input_ready": False,
                    "execution_allowed": False,
                    "reason": f"LOOP_ERROR:{type(exc).__name__}",
                },
                "error": str(exc),
            }
            _write_state(error, output_dir)
            print(json.dumps({"error": str(exc), "execution": "OFF"}, ensure_ascii=False), flush=True)
        time.sleep(interval)


def main(capture_fn=None) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--loop", action="store_true", help="continuous read-only monitoring")
    parser.add_argument("--interval", type=float, default=_monitor_interval())
    parser.add_argument("--output-dir", default="artifacts/vision")
    args, _unknown = parser.parse_known_args()
    fn = capture_once if capture_fn is None else capture_fn
    if args.loop and capture_fn is None:
        return _run_loop(os.getenv("TRADINGVIEW_CDP_URL"), args.output_dir, max(3.0, min(300.0, args.interval)))
    data = fn(os.getenv("TRADINGVIEW_CDP_URL"))
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0 if data.get("capture_verified") else 2


if __name__ == "__main__":
    raise SystemExit(main())
