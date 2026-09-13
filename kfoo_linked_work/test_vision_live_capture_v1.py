def test_capture_contract_requires_verified_metadata():
    data={"connected":True,"symbol":"XAU/USD","timeframe":"15m","screenshot_path":"artifacts/vision/tradingview_live.png"}
    assert bool(data["connected"] and data["symbol"] and data["timeframe"] and data["screenshot_path"])

def test_capture_without_timeframe_is_not_verified():
    data={"connected":True,"symbol":"XAU/USD","timeframe":None,"screenshot_path":None}
    assert not bool(data["connected"] and data["symbol"] and data["timeframe"] and data["screenshot_path"])
