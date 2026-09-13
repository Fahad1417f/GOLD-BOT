from __future__ import annotations
import json
import os
try:
    from .playwright_chart_reader import PlaywrightChartReader
    from .vision_candle_detector_v1 import detect_candles, DetectorConfig
except ImportError:
    from playwright_chart_reader import PlaywrightChartReader
    from vision_candle_detector_v1 import detect_candles, DetectorConfig

def _roi_from_plot(reader, screenshot_path, plot_rect):
    if not plot_rect or not screenshot_path or reader.page is None:return DetectorConfig()
    try:
        from PIL import Image
        with Image.open(screenshot_path) as im: sw,sh=im.size
        v=reader.page.evaluate("() => ({w:innerWidth,h:innerHeight})")
        sx,sy=sw/float(v["w"]),sh/float(v["h"])
        x0,y0,x1,y1=map(float,plot_rect)
        return DetectorConfig(roi_left=max(0,round(x0*sx)),roi_top=max(0,round(y0*sy)),roi_right=min(sw,round(x1*sx)),roi_bottom=min(sh,round(y1*sy)))
    except Exception:return DetectorConfig()

def capture_once(cdp_url: str|None=None, output_dir: str="artifacts/vision") -> dict:
    reader=PlaywrightChartReader(cdp_url=cdp_url,screenshot_dir=output_dir)
    try:
        result=reader.connect()
        if not result.connected:return result.to_dict()
        result.screenshot_path=reader.capture("tradingview_live.png")
        data=result.to_dict()
        detection=detect_candles(result.screenshot_path,_roi_from_plot(reader,result.screenshot_path,result.plot_rect))
        data["pixel_candles_available"]=bool(detection.verified)
        data["pixel_candle_count"]=len(detection.candles)
        data["pixel_candle_reason"]=detection.reason
        data["pixel_candle_roi"]=detection.roi
        data["pixel_candles"]= [{"index":c.index,"x":c.x,"open_y":c.open_y,"high_y":c.high_y,"low_y":c.low_y,"close_y":c.close_y,"body_top":c.body_top,"body_bottom":c.body_bottom,"polarity":c.polarity,"confidence":c.confidence} for c in detection.candles]
        data["ohlc_verified"]=False
        data["ohlc_reason"]="PRICE_SCALE_ANCHORS_NOT_VERIFIED"
        data["capture_verified"]=bool(result.connected and result.symbol and result.timeframe and result.screenshot_path)
        return data
    finally:reader.close()

if __name__=="__main__":
    data=capture_once(os.getenv("TRADINGVIEW_CDP_URL"))
    print(json.dumps(data,ensure_ascii=False,indent=2))
    raise SystemExit(0 if data.get("capture_verified") else 2)
