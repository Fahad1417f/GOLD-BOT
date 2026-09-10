from __future__ import annotations
import json, os, re, time
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(os.getenv("GOLDBOT_ROOT",Path(__file__).resolve().parents[1])).resolve()
LOG=Path(os.getenv("GOLDBOT_MONITOR_LOG",ROOT/"v56_monitor.log"))
OUT=Path(os.getenv("GOLDBOT_VIRTUAL_TRADES_PATH",ROOT/"virtual_trades.json"))
TP=float(os.getenv("GOLDBOT_VIRTUAL_TP_POINTS","0"))
SL=float(os.getenv("GOLDBOT_VIRTUAL_SL_POINTS","0"))
MAX_AGE=float(os.getenv("GOLDBOT_VIRTUAL_MAX_AGE_SECONDS","86400"))

def now(): return datetime.now(timezone.utc).isoformat()
def load():
    try:return json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:return {"version":1,"mode":"VIRTUAL_ONLY","open":[],"closed":[],"stats":{"signals":0,"wins":0,"losses":0,"expired":0}}
def save(s):
    OUT.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding="utf-8")
def price(text):
    pats=[r'"price"\s*:\s*([0-9]+(?:\.[0-9]+)?)',r'XAUUSD\s+([0-9]+(?:\.[0-9]+)?)',r'XAU/USD\s+([0-9]+(?:\.[0-9]+)?)']
    vals=[]
    for p in pats:
        vals += [float(x) for x in re.findall(p,text,re.I)]
    return vals[-1] if vals else None
def last(text,pat,default=""):
    m=list(re.finditer(pat,text,re.I|re.M)); return m[-1].group(1) if m else default

def run():
    s=load()
    text=LOG.read_text(encoding="utf-8",errors="ignore") if LOG.exists() else ""
    p=price(text)
    if p is None:return s
    direction=last(text,r'DIRECTION_15M=([^\s]+)',"neutral")
    strong=bool(re.search(r'STRONG_ENTRY|STRONG_SIGNAL',text,re.I))
    kfoo=last(text,r'KFOO_ACTIVE_15M=([^\s]+)',"unknown")
    level=last(text,r'(?:SIGNAL_LEVEL|LEVEL)=([^\s]+)',"")
    key=last(text,r'(?:SIGNAL_ID|eventId)[=:]"?([^"\s,}]+)',"")
    if not key:key=f"{direction}|{p}|{last(text,r'LEADER_15M_REMAINING=([0-9.]+)', '0')}"
    if strong and direction in ("long","short") and not any(x["id"]==key for x in s["open"]+s["closed"]):
        s["open"].append({"id":key,"opened_at":now(),"direction":direction.upper(),"entry_price":p,"tp_points":TP,"sl_points":SL,"status":"OPEN","kfoo":kfoo,"level":level})
        s["stats"]["signals"]+=1
    for x in list(s["open"]):
        age=time.time()-datetime.fromisoformat(x["opened_at"].replace("Z","+00:00")).timestamp()
        if x["direction"]=="LONG":
            mfe=p-x["entry_price"]; mae=x["entry_price"]-p
            tp_hit=TP>0 and mfe>=TP; sl_hit=SL>0 and mae>=SL
        else:
            mfe=x["entry_price"]-p; mae=p-x["entry_price"]
            tp_hit=TP>0 and mfe>=TP; sl_hit=SL>0 and mae>=SL
        x["last_price"]=p;x["mfe_points"]=round(max(0,mfe),3);x["mae_points"]=round(max(0,mae),3)
        if tp_hit or sl_hit or age>=MAX_AGE:
            x["status"]="WIN" if tp_hit and not sl_hit else ("LOSS" if sl_hit else "EXPIRED")
            x["closed_at"]=now();x["exit_price"]=p
            x["pnl_points"]=round((p-x["entry_price"]) if x["direction"]=="LONG" else (x["entry_price"]-p),3)
            s["closed"].append(x);s["open"].remove(x)
            s["stats"][{"WIN":"wins","LOSS":"losses","EXPIRED":"expired"}[x["status"]]]+=1
    total=s["stats"]["wins"]+s["stats"]["losses"]
    s["stats"]["win_rate"]=round(100*s["stats"]["wins"]/total,2) if total else None
    s["updated_at"]=now();s["last_price"]=p;s["configuration"]={"tp_points":TP,"sl_points":SL,"max_age_seconds":MAX_AGE}
    save(s);return s

if __name__=="__main__": print(json.dumps(run(),ensure_ascii=False,indent=2))
