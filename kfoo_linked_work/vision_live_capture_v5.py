from __future__ import annotations

import json
import os
import re
import shutil
import subprocess

from . import vision_live_capture_v3 as v3
from . import vision_live_capture_v1 as live
from .vision_screen_reconstructor_v1 import PixelCandle, ScaleAnchor, VisionScreenReconstructorV1

_TRACE_ON={"1","ON","TRUE","YES"}

def _trace(phase:str,**extra)->None:
    if os.getenv("GOLDBOT_VISION_TRACE","OFF").upper() in _TRACE_ON:
        print(json.dumps({"phase":phase,**extra},ensure_ascii=False),flush=True)

def _parse_num(text:str)->float|None:
    s=(text or "").strip().translate(str.maketrans("٠١٢٣٤٥٦٧٨٩٬٫","0123456789,."))
    s=s.replace("\u202a","").replace("\u202c","")
    m=re.search(r"[-+]?\d[\d\s,]*(?:\.\d+)?",s)
    if not m:return None
    token=m.group(0).replace(" ","")
    if token.count(".")==0 and token.count(",")==1:
        a,b=token.split(","); token=a+("."+b if len(a)<=4 and len(b) in (1,2,3) else b)
    else: token=token.replace(",","")
    try:return float(token)
    except ValueError:return None

def _pixel(c):
    pol="bullish" if c.polarity=="green" else "bearish" if c.polarity=="red" else c.polarity
    return PixelCandle(c.index,c.x,c.open_y,c.high_y,c.low_y,c.close_y,c.body_top,c.body_bottom,pol,c.confidence)

def _header_ohlc(reader):
    try:
        text=reader.page.locator("body").inner_text(timeout=1000)
        lines=[x.strip().replace("\u202a","").replace("\u202c","") for x in text.splitlines() if x.strip()]
        out={}
        for key in ("O","H","L","C"):
            for i,line in enumerate(lines[:-1]):
                if line==key:
                    value=_parse_num(lines[i+1])
                    if value is not None: out[key.lower()]=value; break
        if set(out)=={"o","h","l","c"} and out["h"]>=max(out["o"],out["c"]) and out["l"]<=min(out["o"],out["c"]): return out
    except Exception as exc:_trace("HEADER_OHLC_ERROR",error=f"{type(exc).__name__}:{exc}")
    return None

def _header_match(reader,monitored):
    h=_header_ohlc(reader)
    if not h:return [],{"reason":"HEADER_OHLC_UNAVAILABLE"}
    span=h["h"]-h["l"]
    if span<=0:return [],{"reason":"HEADER_OHLC_INVALID"}
    expected={"o":(h["h"]-h["o"])/span,"c":(h["h"]-h["c"])/span}
    best=None
    for c in monitored:
        p=_pixel(c); py=p.low_y-p.high_y
        if py<4 or p.high_y>min(p.open_y,p.close_y) or p.low_y<max(p.open_y,p.close_y):continue
        obs={"o":(p.open_y-p.high_y)/py,"c":(p.close_y-p.high_y)/py}
        err=max(abs(obs[k]-expected[k]) for k in expected)
        polarity_ok=(h["c"]<=h["o"] and p.polarity=="bearish") or (h["c"]>=h["o"] and p.polarity=="bullish")
        score=err+(0.25 if not polarity_ok else 0)
        if best is None or score<best[0]:best=(score,err,polarity_ok,p)
    if best is None or best[1]>0.10 or not best[2]:
        return [],{"reason":"NO_PIXEL_CANDLE_MATCH_FOR_HEADER_OHLC","header_ohlc":h,"best_normalized_error":best[1] if best else None}
    p=best[3]
    return [ScaleAnchor(p.high_y,h["h"]),ScaleAnchor(p.low_y,h["l"])],{"reason":"HEADER_OHLC_PIXEL_ALIGNMENT_VERIFIED","header_ohlc":h,"matched_index":p.index,"normalized_error":round(best[1],6)}

def _ocr_scale_anchors(screenshot_path,plot_rect):
    exe=shutil.which("tesseract")
    if not exe:return [],{"reason":"TESSERACT_NOT_INSTALLED"}
    try:
        from PIL import Image
        with Image.open(screenshot_path) as im:
            sw,sh=im.size; x0,y0,x1,y1=[int(v) for v in plot_rect]
            left=max(0,min(sw-1,x1+2)); top=max(0,y0); right=sw; bottom=min(sh,y1)
            if left>=right:return [],{"reason":"OCR_SCALE_ROI_EMPTY"}
            tmp=str(screenshot_path)+".scale_ocr.png"; im.crop((left,top,right,bottom)).save(tmp)
        proc=subprocess.run([exe,tmp,"stdout","--psm","6","-c","tessedit_char_whitelist=0123456789.,-","tsv"],capture_output=True,text=True,encoding="utf-8",errors="backslashreplace",timeout=2)
        anchors=[]
        for line in proc.stdout.splitlines()[1:]:
            cols=line.split("\t")
            if len(cols)<12:continue
            price=_parse_num(cols[11].strip())
            if price is None or price<1000:continue
            try:box_top=float(cols[7]); height=float(cols[9])
            except ValueError:continue
            y=top+box_top+height/2
            if y0<=y<=y1:anchors.append(ScaleAnchor(y,price))
        try:os.remove(tmp)
        except OSError:pass
        anchors=sorted(anchors,key=lambda a:a.y)
        for a,b in zip(anchors,anchors[1:]):
            if b.y-a.y>=10 and b.price<a.price:return [a,b],{"reason":"OCR_SCALE_ANCHORS_FOUND","candidate_count":len(anchors)}
        return [],{"reason":"OCR_NO_MONOTONIC_PRICE_PAIR","candidate_count":len(anchors)}
    except Exception as exc:return [],{"reason":f"OCR_SCALE_READ_FAILED:{type(exc).__name__}:{exc}"}

def _verify(reader,screenshot_path,plot_rect,monitored):
    _trace("OHLC_V5_START",monitored=len(monitored))
    anchors,dom_diag=v3._read_price_scale_anchors(reader,plot_rect,screenshot_path)
    source="dom"
    diagnostics={"dom":dom_diag}
    if len(anchors)<2:
        anchors,ocr_diag=_ocr_scale_anchors(screenshot_path,plot_rect); source="ocr" if len(anchors)>=2 else source
        diagnostics["ocr"]=ocr_diag
    if len(anchors)<2:
        anchors,header_diag=_header_match(reader,monitored); source="header_match" if len(anchors)>=2 else source
        diagnostics["header"]=header_diag
    if len(anchors)<2:
        diagnostics.update({"source":source,"reason":"TWO_DISTINCT_SCALE_ANCHORS_REQUIRED","verified":False})
        _trace("OHLC_V5_END",anchor_count=0,verified=False,reason=diagnostics["reason"])
        return [],[],diagnostics
    result=VisionScreenReconstructorV1().map_ohlc([_pixel(c) for c in monitored],anchors)
    diagnostics.update({"source":source,"reconstructor_reason":result.reason,"verified":result.verified})
    _trace("OHLC_V5_END",anchor_count=len(anchors),verified=result.verified,reason=result.reason,source=source)
    return list(result.ohlc),anchors,diagnostics

live._verify_ohlc_from_screen=_verify

if __name__=="__main__":raise SystemExit(live.main())
