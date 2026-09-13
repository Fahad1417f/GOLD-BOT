from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

import kfoo_linked_work.vision_live_capture_v1 as live
from kfoo_linked_work.vision_candle_detector_v1 import Detection, PixelCandleCandidate


class _FakePage:
    def evaluate(self, script):
        return {"w": 1000, "h": 500}


class _FakeReader:
    def __init__(self, *args, **kwargs):
        self.page = _FakePage()

    def connect(self):
        return type(
            "R",
            (),
            {
                "connected": True,
                "symbol": "XAU/USD",
                "timeframe": "15m",
                "screenshot_path": None,
                "plot_rect": (100, 50, 900, 450),
                "to_dict": lambda self: {
                    "connected": True,
                    "symbol": "XAU/USD",
                    "timeframe": "15m",
                    "plot_rect": [100, 50, 900, 450],
                },
            },
        )()

    def capture(self, name):
        return self._path

    def close(self):
        pass


class _FakeResult:
    connected = True
    symbol = "XAU/USD"
    timeframe = "15m"
    screenshot_path = None
    plot_rect = (100, 50, 900, 450)

    def to_dict(self):
        return {
            "connected": True,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "plot_rect": list(self.plot_rect),
        }


def test_roi_mapping_uses_plot_rect_and_screenshot_scale(tmp_path: Path):
    image = tmp_path / "chart.png"
    Image.new("RGB", (2000, 1000), "black").save(image)

    reader = _FakeReader()
    cfg = live._roi_from_plot(reader, str(image), (100, 50, 900, 450))

    assert (cfg.roi_left, cfg.roi_top) == (200, 100)
    assert (cfg.roi_right, cfg.roi_bottom) == (1800, 900)


def test_capture_once_keeps_ohlc_fail_closed_and_links_detector(tmp_path: Path, monkeypatch):
    image = tmp_path / "chart.png"
    Image.new("RGB", (2000, 1000), "black").save(image)

    fake_result = _FakeResult()
    fake_result.screenshot_path = str(image)

    class Reader(_FakeReader):
        _path = str(image)

        def connect(self):
            return fake_result

    candle = PixelCandleCandidate(0, 100.0, 120.0, 100.0, 140.0, 110.0, 110.0, 120.0, "unknown", 0.80)
    seen = {}

    monkeypatch.setattr(live, "PlaywrightChartReader", Reader)

    def fake_detect(path, config):
        seen["path"] = path
        seen["roi"] = config
        return Detection((candle, candle, candle), True, "PIXEL_CANDLES_DETECTED", (200, 100, 1800, 900))

    monkeypatch.setattr(live, "detect_candles", fake_detect)

    data = live.capture_once(output_dir=str(tmp_path))

    assert data["capture_verified"] is True
    assert data["pixel_candles_available"] is True
    assert data["pixel_candle_count"] == 3
    assert data["pixel_candle_reason"] == "PIXEL_CANDLES_DETECTED"
    assert data["ohlc_verified"] is False
    assert data["ohlc_reason"] == "PRICE_SCALE_ANCHORS_NOT_VERIFIED"
    assert seen["path"] == str(image)
    assert (seen["roi"].roi_left, seen["roi"].roi_top) == (200, 100)


def test_module_output_is_valid_json(monkeypatch, capsys):
    payload = {"capture_verified": False, "reason": "TRADINGVIEW_PAGE_NOT_FOUND"}
    monkeypatch.setattr(live, "capture_once", lambda *_args, **_kwargs: payload)
    try:
        exec(
            compile(Path(live.__file__).read_text(encoding="utf-8"), str(live.__file__), "exec"),
            {
                "__name__": "__main__",
                "os": __import__("os"),
                "json": json,
                # Inject the already-imported monkeypatched function so the
                # exec'd module does not open a second Playwright/CDP session.
                "capture_once": live.capture_once,
            },
        )
    except SystemExit:
        pass
    assert "capture_verified" in capsys.readouterr().out
