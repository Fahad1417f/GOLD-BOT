"""Vision live capture v3: bounded DOM/shadow-root price-scale discovery.

Avoids unbounded document traversal that can stall the continuous monitor.
No anchors are fabricated; OHLC and execution remain fail-closed.
"""
from __future__ import annotations

import re

from . import vision_live_capture_v1 as live
from .vision_screen_reconstructor_v1 import ScaleAnchor


_PRICE_TRANSLATION = str.maketrans("٠١٢٣٤٥٦٧٨٩٬٫", "0123456789,.")
_ATTRS = ("aria-label", "title", "data-value", "data-price", "data-price-value", "data-name")
_ROOT_SELECTORS = (
    "svg text",
    "[aria-label]",
    "[title]",
    "[data-value]",
    "[data-price]",
    "[data-price-value]",
    "[data-name]",
    '[class*="price"]',
    '[class*="scale"]',
    '[class*="axis"]',
    '[id*="price"]',
    '[id*="scale"]',
    '[id*="axis"]',
)


def _parse_price_number(text: str) -> float | None:
    s = (text or "").strip().translate(_PRICE_TRANSLATION)
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
                const seen=new WeakSet();
                const attrs=["aria-label","title","data-value","data-price","data-price-value","data-name"];
                const maxNodes=1800;
                const deadline=performance.now()+350;
                const emit=(text,r,side,source)=>{
                    const t=String(text||'').trim();
                    if(!t || t.length>48 || !r.width || !r.height || r.bottom<y0 || r.top>y1 || r.width>320 || r.height>56) return;
                    const right=r.left>=x1-24 && r.left<=x1+420;
                    const left=r.right>=x0-420 && r.right<=x0+24;
                    if(right||left) out.push({text:t,x:r.left,y:(r.top+r.bottom)/2,w:r.width,h:r.height,side:side||(right?'right':'left'),source});
                };
                const roots=[document];
                while(roots.length && seen.size<maxNodes && performance.now()<deadline){
                    const root=roots.shift();
                    if(!root || !root.querySelectorAll) continue;
                    let elements=[];
                    try {
                        for(const sel of ['svg text','[aria-label]','[title]','[data-value]','[data-price]','[data-price-value]','[data-name]','[class*="price"]','[class*="scale"]','[class*="axis"]','[id*="price"]','[id*="scale"]','[id*="axis"]']){
                            try { elements.push(...root.querySelectorAll(sel)); } catch(_) {}
                        }
                    } catch(_) {}
                    const unique=[];
                    const localSeen=new Set();
                    for(const el of elements){
                        if(localSeen.has(el)) continue;
                        localSeen.add(el);
                        if(seen.has(el)) continue;
                        seen.add(el);
                        const r=el.getBoundingClientRect();
                        if(r.width && r.height && r.bottom>=y0 && r.top<=y1){
                            const right=r.left>=x1-24 && r.left<=x1+420;
                            const left=r.right>=x0-420 && r.right<=x0+24;
                            if(right||left){
                                const values=[];
                                for(const a of attrs){ try{ values.push(el.getAttribute(a)); }catch(_){} }
                                try{ values.push(el.innerText,el.textContent); }catch(_){}
                                for(const v of [...new Set(values.map(v=>String(v||'').trim()).filter(Boolean))]) emit(v,r,null,'element');
                            }
                        }
                        if(el.shadowRoot && roots.length<24) roots.push(el.shadowRoot);
                        if(seen.size>=maxNodes || performance.now()>=deadline) break;
                    }
                }
                const walker=document.createTreeWalker(document,NodeFilter.SHOW_TEXT);
                let n;
                let textNodes=0;
                while((n=walker.nextNode()) && textNodes<500 && performance.now()<deadline){
                    textNodes++;
                    const t=String(n.nodeValue||'').trim();
                    if(!t || t.length>48) continue;
                    try{
                        const rg=document.createRange(); rg.selectNodeContents(n); const r=rg.getBoundingClientRect();
                        const right=r.left>=x1-24 && r.left<=x1+420;
                        const left=r.right>=x0-420 && r.right<=x0+24;
                        if(right||left) emit(t,r,right?'right':'left','text_node');
                    }catch(_){}
                }
                return {items:out,scanned:seen.size,text_nodes:textNodes,truncated:performance.now()>=deadline};
            }""",
            [x0 / sx, y0 / sy, x1 / sx, y1 / sy],
        )

        raw_items = payload.get("items", []) if isinstance(payload, dict) else (payload or [])
        candidates=[]
        for item in raw_items:
            price=_parse_price_number(item.get("text", ""))
            if price is None:
                continue
            y=float(item.get("y",0))*sy
            x=float(item.get("x",0))*sx
            if y0*sy<=y<=y1*sy:
                candidates.append({"y":round(y,2),"price":price,"text":str(item.get("text","")),"x":round(x,2),"side":item.get("side"),"source":item.get("source")})

        dedup=[]
        for c in sorted(candidates,key=lambda v:(v["side"] or "",v["y"],v["x"],v["source"] or "")):
            if any(abs(c["y"]-d["y"])<=2 and c["price"]==d["price"] and c["side"]==d["side"] for d in dedup):
                continue
            dedup.append(c)

        pair_pool=[]
        for side in ("right","left"):
            items=sorted((c for c in dedup if c["side"]==side),key=lambda c:c["y"])
            for a,b in zip(items,items[1:]):
                dy=b["y"]-a["y"]; dp=b["price"]-a["price"]
                if dy>=8 and dp<0:
                    pair_pool.append((dy,abs(dp),a,b))

        selected=[]
        if pair_pool:
            _,_,a,b=max(pair_pool,key=lambda p:(p[0],p[1]))
            selected=[a,b]
            for c in dedup:
                if c["side"]!=a["side"]:
                    continue
                if any(abs(c["y"]-s["y"])<=4 and c["price"]==s["price"] for s in selected):
                    continue
                if all((c["y"]-s["y"])*(c["price"]-s["price"])<0 for s in selected):
                    selected.append(c)

        anchors=[ScaleAnchor(c["y"],c["price"]) for c in selected[:12]]
        return anchors,{
            "reason":"VISIBLE_SCALE_LABEL_PAIRS_FOUND" if len(anchors)>=2 else "NO_VERIFIED_SCALE_LABEL_PAIR",
            "candidate_count":len(candidates),
            "distinct_count":len(anchors),
            "scan_sides":["right","left"],
            "sources":sorted(set(c.get("source") for c in dedup if c.get("source"))),
            "dom_scanned":payload.get("scanned",0) if isinstance(payload,dict) else 0,
            "text_nodes_scanned":payload.get("text_nodes",0) if isinstance(payload,dict) else 0,
            "scan_truncated":bool(payload.get("truncated")) if isinstance(payload,dict) else False,
            "candidates":dedup[:40],
        }
    except Exception as exc:
        return [], {"reason":f"SCALE_ANCHOR_READ_FAILED:{type(exc).__name__}:{exc}","candidate_count":0}


live._read_price_scale_anchors=_read_price_scale_anchors

if __name__=="__main__":
    raise SystemExit(live.main())
