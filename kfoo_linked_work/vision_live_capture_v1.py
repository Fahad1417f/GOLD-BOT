from __future__ import annotations
import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from .playwright_chart_reader import PlaywrightChartReader
    from .vision_candle_detector_v1 import detect_candles, DetectorConfig
except ImportError:
    from playwright_chart_reader import PlaywrightChartReader
    from vision_candle_detector_v1 import detect_candles, DetectorConfig


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json_atomic(path: str | Path, payload: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(target)


def _roi_from_plot(reader, screenshot_path, plot_rect):
    if not plot_rect or not screenshot_path or reader.page is None:
        return DetectorConfig()
    try:
        from PIL import Image
        with Image.open(screenshot_path) as im:
            sw, sh = im.size
        v = reader.page.evaluate("() => ({w:innerWidth,h:innerHeight})")
        sx, sy = sw / float(v["w"]), sh / float(v["h"])
        x0, y0, x1, y1 = map(float, plot_rect)
        return DetectorConfig(
            roi_left=max(0, round(x0 * sx)),
            roi_top=max(0, round(y0 * sy)),
            roi_right=min(sw, round(x1 * sx)),
            roi_bottom=min(sh, round(y1 * sy)),
        )
    except Exception:
        return DetectorConfig()


def _capture_with_reader(reader, output_dir: str, sequence: int) -> dict:
    result = reader.read()
    if not result.connected:
        return result.to_dict()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    screenshot_name = f"tradingview_{stamp}_{sequence:08d}.png"
    result.screenshot_path = reader.capture(screenshot_name)
    data = result.to_dict()

    detection = detect_candles(
        result.screenshot_path,
        _roi_from_plot(reader, result.screenshot_path, result.plot_rect),
    )
    data["pixel_candles_available"] = bool(detection.verified)
    data["pixel_candle_count"] = len(detection.candles)
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
        for c in detection.candles
    ]
    data["ohlc_verified"] = False
    data["ohlc_reason"] = "PRICE_SCALE_ANCHORS_NOT_VERIFIED"
    data["capture_verified"] = bool(
        result.connected and result.symbol and result.timeframe and result.screenshot_path
    )
    data["captured_at"] = _utc_now()
    data["capture_sequence"] = sequence
    data["frame_sha256"] = _sha256(result.screenshot_path)
    return data


def capture_once(cdp_url: str | None = None, output_dir: str = "artifacts/vision") -> dict:
    reader = PlaywrightChartReader(cdp_url=cdp_url, screenshot_dir=output_dir)
    try:
        result = reader.connect()
        if not result.connected:
            return result.to_dict()
        # connect() already performed one metadata read; use that connected page
        # directly for the capture so the CDP session is not reopened.
        return _capture_with_reader(reader, output_dir, 1)
    finally:
        reader.close()


class PersistentVisionSession:
    """Long-lived, read-only TradingView CDP -> screenshot transport.

    The Chromium/CDP connection stays open across captures. Every frame is
    written as a unique immutable PNG and the latest state is published through
    an atomic heartbeat JSON file. Any broken connection fails closed.
    """

    def __init__(
        self,
        cdp_url: str | None = None,
        output_dir: str = "artifacts/vision",
        heartbeat_path: str | None = None,
    ):
        self.cdp_url = cdp_url or os.getenv("TRADINGVIEW_CDP_URL", "http://127.0.0.1:9222")
        self.output_dir = Path(output_dir)
        self.heartbeat_path = Path(heartbeat_path or self.output_dir / "vision_heartbeat.json")
        self.reader: PlaywrightChartReader | None = None
        self.sequence = 0
        self.last_frame_sha256: str | None = None
        self.consecutive_failures = 0
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def connect(self) -> dict:
        self.reader = PlaywrightChartReader(
            cdp_url=self.cdp_url,
            screenshot_dir=str(self.output_dir),
        )
        result = self.reader.connect()
        if not result.connected:
            self._heartbeat(
                status="DATA_UNAVAILABLE",
                connected=False,
                reason=result.reason,
            )
            return result.to_dict()

        self.consecutive_failures = 0
        self._heartbeat(
            status="RUNNING",
            connected=True,
            symbol=result.symbol,
            timeframe=result.timeframe,
            reason=result.reason,
        )
        return result.to_dict()

    def capture(self) -> dict:
        if self.reader is None or self.reader.page is None:
            return self._failure("NOT_CONNECTED")

        self.sequence += 1
        try:
            data = _capture_with_reader(self.reader, str(self.output_dir), self.sequence)
            if not data.get("connected"):
                return self._failure(data.get("reason", "READ_FAILED"))

            frame_hash = data.get("frame_sha256")
            changed = frame_hash != self.last_frame_sha256
            self.last_frame_sha256 = frame_hash
            data["frame_changed"] = changed
            self.consecutive_failures = 0

            self._heartbeat(
                status="RUNNING",
                connected=True,
                symbol=data.get("symbol"),
                timeframe=data.get("timeframe"),
                last_capture_at=data.get("captured_at"),
                last_capture_path=data.get("screenshot_path"),
                capture_sequence=self.sequence,
                consecutive_failures=0,
                frame_changed=changed,
                frame_sha256=frame_hash,
                reason=data.get("reason"),
            )
            return data
        except Exception as exc:
            return self._failure(f"CAPTURE_FAILED:{type(exc).__name__}:{exc}")

    def run(self, interval_seconds: float = 15.0, max_captures: int | None = None) -> int:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds_must_be_positive")

        connected = self.connect()
        if not connected.get("connected"):
            return 2

        completed = 0
        try:
            while max_captures is None or completed < max_captures:
                data = self.capture()
                print(json.dumps(data, ensure_ascii=False))
                completed += 1
                if not data.get("capture_verified"):
                    # Reconnect on the next cycle, but never emit a false healthy state.
                    self.reconnect()
                if max_captures is not None and completed >= max_captures:
                    break
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            self._heartbeat(
                status="STOPPED",
                connected=self.reader is not None and self.reader.page is not None,
                reason="KEYBOARD_INTERRUPT",
            )
            return 0
        finally:
            self.close()
        return 0

    def reconnect(self) -> dict:
        self.close()
        return self.connect()

    def _failure(self, reason: str) -> dict:
        self.consecutive_failures += 1
        data = {
            "connected": False,
            "capture_verified": False,
            "status": "DATA_UNAVAILABLE",
            "reason": reason,
            "captured_at": _utc_now(),
            "capture_sequence": self.sequence,
        }
        self._heartbeat(
            status="DATA_UNAVAILABLE",
            connected=False,
            consecutive_failures=self.consecutive_failures,
            reason=reason,
            capture_sequence=self.sequence,
        )
        return data

    def _heartbeat(self, **fields) -> None:
        payload = {
            "status": "DATA_UNAVAILABLE",
            "connected": False,
            "execution": "OFF",
            "updated_at": _utc_now(),
            **fields,
        }
        _write_json_atomic(self.heartbeat_path, payload)

    def close(self) -> None:
        if self.reader is not None:
            try:
                self.reader.close()
            finally:
                self.reader = None
        self._heartbeat(
            status="STOPPED",
            connected=False,
            reason="SESSION_CLOSED",
        )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Read-only continuous TradingView vision capture")
    parser.add_argument("--loop", action="store_true", help="Keep the CDP session open and capture continuously")
    parser.add_argument("--interval", type=float, default=float(os.getenv("GOLDBOT_VISION_INTERVAL_SECONDS", "15")))
    parser.add_argument("--output-dir", default=os.getenv("GOLDBOT_VISION_OUTPUT_DIR", "artifacts/vision"))
    parser.add_argument("--heartbeat", default=None)
    args = parser.parse_args(argv)

    if args.loop:
        session = PersistentVisionSession(
            cdp_url=os.getenv("TRADINGVIEW_CDP_URL"),
            output_dir=args.output_dir,
            heartbeat_path=args.heartbeat,
        )
        return session.run(args.interval)

    data = capture_once(os.getenv("TRADINGVIEW_CDP_URL"), args.output_dir)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0 if data.get("capture_verified") else 2


if __name__ == "__main__":
    raise SystemExit(main())
