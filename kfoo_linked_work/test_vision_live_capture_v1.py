from kfoo_linked_work.vision_live_capture_v1 import _candle_limit, _limit_recent_candles


def test_capture_contract_requires_verified_metadata():
    data={"connected":True,"symbol":"XAU/USD","timeframe":"15m","screenshot_path":"artifacts/vision/tradingview_live.png"}
    assert bool(data["connected"] and data["symbol"] and data["timeframe"] and data["screenshot_path"])


def test_capture_without_timeframe_is_not_verified():
    data={"connected":True,"symbol":"XAU/USD","timeframe":None,"screenshot_path":None}
    assert not bool(data["connected"] and data["symbol"] and data["timeframe"] and data["screenshot_path"])


def test_default_live_vision_candle_limit_is_24(monkeypatch):
    monkeypatch.delenv("GOLDBOT_VISION_CANDLE_LIMIT", raising=False)
    assert _candle_limit() == 24


def test_live_vision_candle_limit_clamped(monkeypatch):
    monkeypatch.setenv("GOLDBOT_VISION_CANDLE_LIMIT", "1000")
    assert _candle_limit() == 60
    monkeypatch.setenv("GOLDBOT_VISION_CANDLE_LIMIT", "1")
    assert _candle_limit() == 3


def test_recent_candle_limit_keeps_latest_candidates(monkeypatch):
    monkeypatch.setenv("GOLDBOT_VISION_CANDLE_LIMIT", "4")
    candles = [type("C", (), {"x": x})() for x in (10, 20, 30, 40, 50, 60)]
    assert [c.x for c in _limit_recent_candles(candles)] == [30, 40, 50, 60]
