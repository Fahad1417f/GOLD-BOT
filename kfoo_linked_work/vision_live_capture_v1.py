from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path

try:
    from .playwright_chart_reader import PlaywrightChartReader
    from .vision_candle_detector_v1 import detect_candles, DetectorConfig
    from .vision_screen_reconstructor_v1 import PixelCandle, ScaleAnchor, VisionScreenReconstructorV1
except ImportError:
    from playwright_chart_reader import PlaywrightChartReader
    from vision_candle_detector_v1 import detect_candles, DetectorConfig
    from vision_screen_reconstructor_v1 import PixelCandle, ScaleAnchor, VisionScreenReconstructorV1


def _candle_limit() -> int:
    try:
        return max(3, min(60, int(os.getenv("GOLDBOT_VISION_CANDLE_LIMIT", "24"))))
    except ValueError:
        return 24


def _monitor_interval() -> float:
    try:
        return max(3.0, min(300.0, float(os.getenv("GOLDBOT_VISION_INTERVAL_SECONDS", "15"))))
    except ValueError:
        return 15.0


def _limit_recent_candles(candles):
    return sorted(candles, key=lambda candle: candle.x)[-_candle_limit():]


def _build_vision_gate(data: dict) -> dict:
    kfoo = data.get("kfoo") if isinstance(data.get("kfoo"), dict) else {}
    identity_verified = bool(data.get("capture_verified"))
    geometry_verified = bool(data.get("pixel_candles_available")) and int(data.get("pixel_candle_count") or 0) >= 3
    ohlc_verified = bool(data.get("ohlc_verified"))
    kfoo_signal_ready = bool(
        kfoo.get("present")
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
        "reason": "READY_FOR_DECISION_INPUT" if decision_input_ready else "READY_FOR_MONITORING_ONLY" if monitoring_ready else "VISION_GATE_INCOMPLETE",
    }


def _roi_from_plot(reader, screenshot_path, plot_rect):
    if not plot_rect or not screenshot_path or reader.page is None:
        return DetectorConfig(max_candle_count=_candle_limit())
    try:
        from PIL import Image
        with Image.open(screenshot_path) as im:
            sw, sh = im.size
        viewport = reader.page.evaluate("() => ({w:innerWidth,h:innerHeight})")
        sx, sy = sw / float(viewport["w"]), sh / float(viewport["h"])
        x0, y0, x1, y1 = map(float, plot_rect)
        return DetectorConfig(
            roi_left=max(0, round(x0 * sx)), roi_top=max(0, round(y0 * sy)),
            roi_right=min(sw, round(x1 * sx)), roi_bottom=min(sh, round(y1 * sy)),
            max_candle_count=_candle_limit(),
        )
    except Exception:
        return DetectorConfig(max_candle_count=_candle_limit())


def _detect_with_fallbacks(reader, screenshot_path, plot_rect):
    configs = [("plot_rect", _roi_from_plot(reader, screenshot_path, plot_rect))]
    try:
        from PIL import Image
        with Image.open(screenshot_path) as im:
            sw, sh = im.size
        configs += [
            ("wide_chart", DetectorConfig(roi_left=int(sw*.02), roi_top=int(sh*.08), roi_right=int(sw*.98), roi_bottom=int(sh*.72), max_candle_count=_candle_limit())),
            ("price_area", DetectorConfig(roi_left=int(sw*.04), roi_top=int(sh*.05), roi_right=int(sw*.90), roi_bottom=int(sh*.82), price_pane_ratio=.82, max_candle_count=_candle_limit())),
        ]
    except Exception:
        pass
    attempts, best = [], None
    for name, config in configs:
        detection = detect_candles(screenshot_path, config)
        attempts.append({"name": name, "verified": detection.verified, "count": len(detection.candles), "reason": detection.reason, "roi": detection.roi})
        score = (1 if detection.verified else 0, len(detection.candles), detection.reason == "PIXEL_CANDLES_DETECTED")
        if best is None or score > best[0]:
            best = (score, name, detection)
        if detection.verified and len(detection.candles) >= 3:
            break
    return (best[2], attempts, best[1]) if best else (None, attempts, None)


def _parse_price_number(text: str) -> float | None:
    s = (text or "").strip().translate(str.maketrans("٠١٢٣٤٥٦٧٨٩٬٫", "0123456789,."))
    if not s or re.search(r"[%$€£]|USDT|USD", s, re.I):
        return None
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


def _read_price_scale_anchors(reader, plot_rect, screenshot_path):
    if reader.page is None or not plot_rect or not screenshot_path:
        return [], {"reason": "PLOT_RECT_UNAVAILABLE", "candidate_count": 0}
    try:
        from PIL import Image
        with Image.open(screenshot_path) as im:
            sw, sh = im.size
        viewport = reader.page.evaluate("() => ({w:innerWidth,h:innerHeight})")
        sx, sy = sw / float(viewport["w"]), sh / float(viewport["h"])
        x0, y0, x1, y1 = map(float, plot_rect)
        payload = reader.page.evaluate(
            """([x0,y0,x1,y1]) => [...document.querySelectorAll('*')].flatMap(el => {
                const r=el.getBoundingClientRect(), s=getComputedStyle(el), t=(el.textContent||'').trim();
                if (!r.width || !r.height || r.bottom<y0 || r.top>y1 || r.left<x1-12 || r.left>x1+260 || r.width>220 || r.height>40 || el.children.length>4 || s.display==='none' || s.visibility==='hidden' || Number(s.opacity||1)===0 || !t || t.length>24) return [];
                return [{text:t,x:r.left,y:(r.top+r.bottom)/2,w:r.width,h:r.height}];
            })""",
            [x0 / sx, y0 / sy, x1 / sx, y1 / sy],
        )
        candidates=[]
        for item in payload or []:
            price=_parse_price_number(item.get("text", ""))
            if price is None: continue
            y=float(item["y"])*sy
            if y0*sy <= y <= y1*sy:
                candidates.append({"y":round(y,2),"price":price,"text":item.get("text",""),"x":round(float(item.get("x",0))*sx,2)})
        dedup=[]
        for c in sorted(candidates, key=lambda v:(v["y"],v["x"])):
            if any(abs(c["y"]-d["y"])<=2 and c["price"]==d["price"] for d in dedup): continue
            dedup.append(c)
        distinct=[]
        for c in dedup:
            if not any(abs(c["y"]-d["y"])<=4 or c["price"]==d["price"] for d in distinct):
                distinct.append(c)
        anchors=[ScaleAnchor(c["y"],c["price"]) for c in distinct[:12]]
        return anchors, {"reason":"VISIBLE_SCALE_LABELS_FOUND" if anchors else "NO_VISIBLE_NUMERIC_SCALE_LABELS","candidate_count":len(candidates),"distinct_count":len(anchors),"candidates":candidates[:20]}
    except Exception as exc:
        return [], {"reason":f"SCALE_ANCHOR_READ_FAILED:{type(exc).__name__}:{exc}","candidate_count":0}


def _verify_ohlc_from_screen(reader, screenshot_path, plot_rect, monitored):
    if not monitored:
        return [], [], {"reason":"NO_PIXEL_CANDLES"}
    anchors, diagnostics = _read_price_scale_anchors(reader, plot_rect, screenshot_path)
    if len(anchors) < 2:
        return [], anchors, {**diagnostics, "reason":"TWO_DISTINCT_SCALE_ANCHORS_REQUIRED", "verified":False}
    candles=[]
    for c in monitored:
        candles.append(PixelCandle(c.index,c.x,c.open_y,c.high_y,c.low_y,c.close_y,c.body_top,c.body_bottom,
                                    "bullish" if c.polarity=="green" else "bearish" if c.polarity=="red" else c.polarity,c.confidence))
    result=VisionScreenReconstructorV1().map_ohlc(candles, anchors)
    return list(result.ohlc), anchors, {**diagnostics,"reason":result.reason,"verified":result.verified}


def capture_once(cdp_url: str | None = None, output_dir: str = "artifacts/vision") -> dict:
    reader=PlaywrightChartReader(cdp_url=cdp_url,screenshot_dir=output_dir)
    try:
        result=reader.connect()
        if not result.connected: return result.to_dict()
        result.screenshot_path=reader.capture("tradingview_live.png")
        data=result.to_dict()
        detection,attempts,selected_roi=_detect_with_fallbacks(reader,result.screenshot_path,result.plot_rect)
        monitored=_limit_recent_candles(detection.candles) if detection else []
        data.update({"pixel_candles_available":bool(detection and detection.verified and monitored),"pixel_candle_count":len(monitored),
                     "pixel_candle_limit":_candle_limit(),"pixel_candle_raw_count":len(detection.candles) if detection else 0,
                     "pixel_candle_reason":detection.reason if detection else "NO_DETECTOR_RESULT","pixel_candle_roi":detection.roi if detection else None,
                     "pixel_detector_attempts":attempts,"pixel_detector_selected_roi":selected_roi,
                     "pixel_candles":[{"index":c.index,"x":c.x,"open_y":c.open_y,"high_y":c.high_y,"low_y":c.low_y,"close_y":c.close_y,
                                      "body_top":c.body_top,"body_bottom":c.body_bottom,"polarity":c.polarity,"confidence":c.confidence} for c in monitored]})
        ohlc,anchors,anchor_diag=_verify_ohlc_from_screen(reader,result.screenshot_path,result.plot_rect,monitored)
        data["scale_anchors"]=[{"y":a.y,"price":a.price} for a in anchors]
        data["scale_anchor_diagnostics"]=anchor_diag
        data["ohlc"]=ohlc
        data["ohlc_verified"]=bool(ohlc and anchor_diag.get("verified") and len(anchors)>=2)
        data["ohlc_reason"]=anchor_diag.get("reason","PRICE_SCALE_ANCHORS_NOT_VERIFIED")
        data["capture_verified"]=bool(result.connected and result.symbol and result.timeframe and result.screenshot_path)
        data["vision_gate"]=_build_vision_gate(data)
        return data
    finally: reader.close()


def _write_state(data: dict, output_dir: str) -> None:
    path=Path(output_dir)/"live_state.json"; path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(".tmp"); tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8"); tmp.replace(path)


def _run_loop(cdp_url,output_dir,interval):
    print("VISION_CONTINUOUS=ON"); print("EXECUTION=OFF"); print(f"INTERVAL_SECONDS={interval:g}")
    cycle=0
    while True:
        cycle+=1
        try:
            data=capture_once(cdp_url,output_dir); _write_state(data,output_dir); gate=data.get("vision_gate") or {}
            print(json.dumps({"cycle":cycle,"connected":data.get("connected"),"verified":data.get("verified"),"capture_verified":data.get("capture_verified"),
                              "symbol":data.get("symbol"),"timeframe":data.get("timeframe"),"kfoo_present":(data.get("kfoo") or {}).get("present"),
                              "kfoo_signal_ready":gate.get("kfoo_signal_ready"),"pixel_geometry_verified":gate.get("pixel_geometry_verified"),
                              "ohlc_verified":gate.get("ohlc_verified"),"pixel_candles":data.get("pixel_candle_count",0),
                              "vision_reason":gate.get("reason") or data.get("reason"),"pixel_candle_reason":data.get("pixel_candle_reason"),
                              "pixel_detector_selected_roi":data.get("pixel_detector_selected_roi"),"ohlc_reason":data.get("ohlc_reason"),
                              "scale_anchor_count":len(data.get("scale_anchors") or [])},ensure_ascii=False),flush=True)
        except KeyboardInterrupt:
            print("VISION_CONTINUOUS=STOP"); return 0
        except Exception as exc:
            error={"connected":False,"verified":False,"capture_verified":False,"vision_gate":{"identity_verified":False,"pixel_geometry_verified":False,"ohlc_verified":False,"kfoo_signal_ready":False,"monitoring_ready":False,"decision_input_ready":False,"execution_allowed":False,"reason":f"LOOP_ERROR:{type(exc).__name__}"},"error":str(exc)}
            _write_state(error,output_dir); print(json.dumps({"error":str(exc),"execution":"OFF"},ensure_ascii=False),flush=True)
        time.sleep(interval)


def main(capture_fn=None):
    parser=argparse.ArgumentParser(add_help=True); parser.add_argument("--loop",action="store_true"); parser.add_argument("--interval",type=float,default=_monitor_interval()); parser.add_argument("--output-dir",default="artifacts/vision")
    args,_unknown=parser.parse_known_args(); fn=capture_once if capture_fn is None else capture_fn
    if args.loop and capture_fn is None: return _run_loop(os.getenv("TRADINGVIEW_CDP_URL"),args.output_dir,max(3.0,min(300.0,args.interval)))
    data=fn(os.getenv("TRADINGVIEW_CDP_URL")); print(json.dumps(data,ensure_ascii=False,indent=2)); return 0 if data.get("capture_verified") else 2


if __name__=="__main__": raise SystemExit(main())
