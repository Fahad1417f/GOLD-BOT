from __future__ import annotations
import base64,hashlib,json,os,re,time
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError

REPO=os.getenv("GOLDBOT_REPO","Fahad1417f/GOLD-BOT")
BRANCH=os.getenv("GOLDBOT_BRANCH","main")
STATE_PATH=os.getenv("GOLDBOT_STATE_PATH","website_state.json")
TOKEN=os.getenv("GITHUB_TOKEN","").strip()
ROOT=Path(os.getenv("GOLDBOT_ROOT",Path(__file__).resolve().parents[1])).resolve()
LOG=Path(os.getenv("GOLDBOT_MONITOR_LOG",ROOT/"v56_monitor.log"))
SUPERVISOR_STATE=ROOT/"supervisor_state.json"
INTERVAL=float(os.getenv("GOLDBOT_PUBLISH_INTERVAL","10"))
try:
    import sys
    _MONITOR_DIR=str(Path(__file__).resolve().parent)
    if _MONITOR_DIR not in sys.path: sys.path.insert(0,_MONITOR_DIR)
    from virtual_trade_tracker import run as update_virtual_trades
except Exception:
    update_virtual_trades=None
MIN_PUBLISH=float(os.getenv("GOLDBOT_MIN_PUBLISH_SECONDS","20"))
API=f"https://api.github.com/repos/{REPO}/contents/{STATE_PATH}"
last_hash=""; last_push=0.0

def gh(method,url,body=None):
    h={"Accept":"application/vnd.github+json","Authorization":f"Bearer {TOKEN}","X-GitHub-Api-Version":"2026-03-10","User-Agent":"GOLD-BOT-state-bridge"}
    data=None if body is None else json.dumps(body).encode()
    with urlopen(Request(url,data=data,headers=h,method=method),timeout=20) as r:return json.loads(r.read().decode())

def get_sha():
    try:return gh("GET",API+"?ref="+BRANCH)["sha"]
    except HTTPError as e:
        if e.code==404:return None
        raise

def latest(t,pattern,default="unknown"):
    m=list(re.finditer(pattern,t,re.I|re.M))
    return m[-1].group(1).strip() if m else default

def parse_log(t):
    s={"agent_status":"ONLINE","execution":"OFF","symbol":"XAUUSD","timeframe":"15m",
       "direction":latest(t,r"DIRECTION_15M=([^\s]+)","neutral"),"confidence":0,"level":"WAIT","score":0,
       "gravity":{"4h":latest(t,r"DIRECTION_4H=([^\s]+)","unknown"),"1h":latest(t,r"DIRECTION_1H=([^\s]+)","unknown")},
       "timing":{"5m":latest(t,r"DIRECTION_5M=([^\s]+)","unknown"),"3m":latest(t,r"DIRECTION_3M=([^\s]+)","unknown")},
       "kfoo":{"table":"—","tf_agg":latest(t,r"KFOO_TF_AGG_15M=([^\r\n]+)","—"),"ind_agg":latest(t,r"KFOO_IND_AGG_15M=([^\r\n]+)","—"),"active":latest(t,r"KFOO_ACTIVE_15M=([^\s]+)","—"),"score":"—","indicators":{}},
       "reasons":[],"updated_at":time.time(),"source":"GOLD-BOT V56 local agent -> GitHub state bridge"}
    if re.search(r"KFOO_TABLE_(4H|1H|15M)=PASS",t,re.I): s["kfoo"]["table"]="PASS"
    ind=latest(t,r"KFOO_INDICATORS_15M=([^\r\n]+)","")
    for part in [x.strip() for x in ind.split("|") if "=" in x]:
        k,v=part.split("=",1); s["kfoo"]["indicators"][k.strip()]=v.strip()
    if re.search(r"STRONG_ENTRY|STRONG_SIGNAL|FAST_TRADE_READY=TRUE",t,re.I): s["level"]="STRONG_ENTRY"
    elif re.search(r"STRONG_SETUP|SETUP_READY",t,re.I): s["level"]="STRONG_SETUP"
    if s["direction"]=="neutral" and s["gravity"]["4h"]==s["gravity"]["1h"] and s["gravity"]["4h"] in ("long","short"):
        s["direction"]=s["gravity"]["4h"]
    s["reasons"]=["KFOO="+s["kfoo"]["table"],"TF="+s["kfoo"]["tf_agg"],"IND="+s["kfoo"]["ind_agg"]]
    return s

def merge_supervisor(state):
    try:
        sup=json.loads(SUPERVISOR_STATE.read_text(encoding="utf-8"))
        state["supervisor_status"]=sup.get("status","UNKNOWN")
        state["safe_mode"]=bool(sup.get("safe_mode",True))
        state["repair"]=sup.get("repair","NONE")
        state["development"]=sup.get("development","WATCHING")
        state["supervisor_updated_at"]=sup.get("updated_at")
        if sup.get("status")!="RUNNING":
            state["agent_status"]="DEGRADED"
            state["level"]="WAIT"
            state["reasons"].insert(0,"SUPERVISOR="+str(sup.get("status")))
    except Exception:
        state["supervisor_status"]="UNKNOWN"
    return state

def publish(state):
    global last_hash,last_push
    raw=json.dumps(state,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    h=hashlib.sha256(raw.encode()).hexdigest()
    if h==last_hash or time.time()-last_push<MIN_PUBLISH:return
    sha=get_sha()
    body={"message":"chore: publish live GOLD-BOT monitor state","content":base64.b64encode(raw.encode()).decode(),"branch":BRANCH}
    if sha: body["sha"]=sha
    gh("PUT",API,body); last_hash=h; last_push=time.time(); print("GITHUB_STATE=UPDATED",flush=True)

def main():
    if not TOKEN: raise SystemExit("GITHUB_TOKEN_NOT_SET")
    print("GOLD_BOT_GITHUB_BRIDGE=READY",flush=True)
    while True:
        try:
            if LOG.exists():
                t=LOG.read_text(encoding="utf-8",errors="ignore")
                if t.strip():
                    state=merge_supervisor(parse_log(t))
                    if update_virtual_trades:
                        try:
                            vt=update_virtual_trades()
                            state["virtual_trades"]=vt
                        except Exception as e:
                            state["virtual_trades_error"]=type(e).__name__+":"+str(e)
                    publish(state)
        except Exception as e: print("GITHUB_STATE_ERROR="+type(e).__name__+":"+str(e),flush=True)
        time.sleep(INTERVAL)

if __name__=="__main__": main()
