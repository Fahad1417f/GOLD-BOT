"""Vision live capture v2: stricter TradingView price-scale anchor discovery.

This module wraps v1 without changing the fail-closed OHLC or execution gates.
It broadens only the evidence search for visible price-axis labels.
"""
from __future__ import annotations

import re

from . import vision_live_capture_v1 as live
from .vision_screen_reconstructor_v1 import ScaleAnchor


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
        sx = sw / float(viewport["w"])
        sy = sh / float(viewport["h"])
        x0, y0, x1, y1 = map(float, plot_rect)
        payload = reader.page.evaluate(
            """([x0,y0,x1,y1]) => {
                const out=[];
                const selectors=[
                    'svg text','[aria-label]','[title]','[data-value]','[data-price]',
                    '[data-price-value]','[data-name]','[class*="price"]','[class*="scale"]',
                    '[class*="axis"]','[id*="price"]','[id*="scale"]','[id*="axis"]'
                ];
                const nodes=new Set();
                for (const sel of selectors) { try { for (const el of document.querySelectorAll(sel)) nodes.add(el); } catch (_) {} }
                for (const el of document.querySelectorAll('div,span')) nodes.add(el);
                for (const el of nodes) {
                    const r=el.getBoundingClientRect();
                    if (!r.width || !r.height) continue;
                    if (r.bottom < y0 || r.top > y1) continue;
                    const inRight = r.left >= x1-20 && r.left <= x1+360;
                    const inLeft = r.right >= x0-360 && r.right <= x0+20;
                    if (!inRight && !inLeft) continue;
                    if (r.width > 260 || r.height > 50) continue;
                    const s=getComputedStyle(el);
                    if (s.display==='none' || s.visibility==='hidden' || Number(s.opacity||1)===0) continue;
                    const values=[
                        el.innerText||'', el.textContent||'', el.getAttribute('aria-label')||'',
                        el.getAttribute('title')||'', el.getAttribute('data-value')||'',
                        el.getAttribute('data-price')||'', el.getAttribute('data-price-value')||'',
                        el.getAttribute('data-name')||''
                    ];
                    const seenText=new Set();
                    for (const text of values) {
                        const t=String(text).trim();
                        if (!t || t.length>40 || seenText.has(t)) continue;
                        seenText.add(t);
                        out.push({text:t,x:r.left,y:(r.top+r.bottom)/2,w:r.width,h:r.height,side:inRight?'right':'left'});
                    }
                }
                return out;
            }""",
            [x0 / sx, y0 / sy, x1 / sx, y1 / sy],
        )
        candidates=[]
        for item in payload or []:
            price=_parse_price_number(item.get("text", ""))
            if price is None:
                continue
            y=float(item.get("y",0))*sy
            x=float(item.get("x",0))*sx
            if not (y0*sy <= y <= y1*sy):
                continue
            candidates.append({"y":round(y,2),"price":price,"text":str(item.get("text","")),"x":round(x,2),"side":item.get("side")})

        dedup=[]
        for c in sorted(candidates,key=lambda v:(v["side"] or "",v["y"],v["x"])):
            if any(abs(c["y"]-d["y"])<=2 and c["price"]==d["price"] and c["side"]==d["side"] for d in dedup):
                continue
            dedup.append(c)

        # Prefer pairs on the same side with a consistent price-vs-y direction.
        pair_pool=[]
        for side in ("right","left"):
            side_items=[c for c in dedup if c["side"]==side]
            side_items=sorted(side_items,key=lambda c:c["y"])
            for a,b in zip(side_items,side_items[1:]):
                dy=b["y"]-a["y"]
                dp=b["price"]-a["price"]
                if dy < 8 or dp == 0:
                    continue
                # On a conventional vertical price axis, lower screen position means higher price.
                if dp >= 0:
                    continue
                pair_pool.append((dy, abs(dp), a, b))

        selected=[]
        if pair_pool:
            _,_,a,b=max(pair_pool,key=lambda p:(p[0],p[1]))
            selected=[a,b]
            # Add further labels only when they keep the same side and direction.
            for c in (x for x in dedup if x["side"]==a["side"]):
                if any(abs(c["y"]-s["y"])<=4 and c["price"]==s["price"] for s in selected):
                    continue
                if all((c["y"]-s["y"])*(c["price"]-s["price"]) < 0 for s in selected):
                    selected.append(c)
        else:
            selected=dedup[:12]

        anchors=[ScaleAnchor(c["y"],c["price"]) for c in selected[:12]]
        return anchors, {
            "reason":"VISIBLE_SCALE_LABEL_PAIRS_FOUND" if len(anchors)>=2 else "NO_VERIFIED_SCALE_LABEL_PAIR",
            "candidate_count":len(candidates),
            "distinct_count":len(anchors),
            "scan_sides":["right","left"],
            "candidates":dedup[:40],
        }
    except Exception as exc:
        return [], {"reason":f"SCALE_ANCHOR_READ_FAILED:{type(exc).__name__}:{exc}","candidate_count":0}


live._read_price_scale_anchors = _read_price_scale_anchors

if __name__ == "__main__":
    raise SystemExit(live.main())
