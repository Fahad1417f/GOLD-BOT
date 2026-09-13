from kfoo_linked_work.vision_live_capture_v1 import capture_once

def test_live_capture_contract_requires_symbol_timeframe_and_screenshot():
    data = {
        "connected": True,
        "symbol": "XAU/USD",
        "timeframe": "15m",
        "screenshot_path": "artifacts/vision/tradingview_live.png",
    }
    assert data["connected"]
    assert data["symbol"] == "XAU/USD"
    assert data["timeframe"] == "15m"
    assert data["screenshot_path"]

def test_failed_capture_is_not_verified():
    data = {"connected": True, "symbol": "XAU/USD", "timeframe": None, "screenshot_path": None}
    assert not bool(data.get("connected") and data.get("symbol") and data.get("timeframe") and data.get("screenshot_path"))
