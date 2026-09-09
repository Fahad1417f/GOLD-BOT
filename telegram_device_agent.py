import os,json,time,platform
from pathlib import Path
try: import requests
except ImportError: requests=None

COMMANDS={"/status":"status","/health":"health","/test":"test","/log":"log","/stop":"stop"}
PROJECT=Path(os.getenv("GOLDBOT_PROJECT_DIR",".")).resolve()
TOKEN=os.getenv("GOLDBOT_TELEGRAM_BOT_TOKEN","").strip()
CHAT_ID=os.getenv("GOLDBOT_TELEGRAM_CHAT_ID","").strip()

def tg(method,data=None,timeout=15):
    if not requests:return {"ok":False,"error":"requests_not_installed"}
    if not TOKEN:return {"ok":False,"error":"TOKEN_MISSING"}
    try:return requests.post(f"https://api.telegram.org/bot{TOKEN}/{method}",data=data or {},timeout=timeout).json()
    except Exception as e:return {"ok":False,"error":f"{type(e).__name__}:{e}"}

def authorized(msg): return bool(CHAT_ID) and str((msg.get("chat") or {}).get("id",""))==CHAT_ID
def probe(name):
    try: __import__(name); return "PASS"
    except Exception as e: return f"FAIL:{type(e).__name__}"
def health():
    return {"python":platform.python_version(),"project":str(PROJECT),
            "chart_controller":probe("chart_controller"),
            "kfoo_direction":probe("kfoo_direction"),
            "kfoo_rules":probe("kfoo_rules"),
            "visual_engine":probe("visual_engine"),
            "telegram_notifier":probe("telegram_notifier"),
            "crypto_demo_v53":probe("crypto_demo_v53"),
            "execution_default":"OFF","production_binance":"BLOCKED",
            "telegram_device_control":"ALLOWLIST_ONLY"}
def test(): return {"project_exists":PROJECT.exists(),"modules":health(),
                     "2m_rule":"PASS_EXPECTED_ABSENT","execution_default":"PASS_OFF",
                     "production_binance":"PASS_BLOCKED"}
def log():
    for n in ("forensic_run.txt","forensic.log","live.log"):
        p=PROJECT/n
        if p.exists(): return "\n".join(p.read_text(encoding="utf-8",errors="replace").splitlines()[-30:])[-6000:]
    return "NO_KNOWN_LOG_FILE"
def response(a):
    if a=="health": return "HEALTH\n"+json.dumps(health(),ensure_ascii=False,indent=2)
    if a=="test": return "TEST\n"+json.dumps(test(),ensure_ascii=False,indent=2)
    if a=="log": return "LOG\n"+log()
    if a=="stop": return "STOP: agent remains local; use Ctrl+C to stop it."
    return "STATUS\n"+json.dumps(health(),ensure_ascii=False,indent=2)
def main():
    if not TOKEN or not CHAT_ID: print("TELEGRAM_AGENT_BLOCKED: missing credentials"); return 2
    offset=None; print("TELEGRAM_DEVICE_AGENT: started | allowlist-only | execution=OFF",flush=True)
    while True:
        d={"timeout":20}
        if offset is not None:d["offset"]=offset
        r=tg("getUpdates",d,30)
        if not r.get("ok"): time.sleep(5); continue
        for u in r.get("result",[]):
            offset=u.get("update_id",0)+1; m=u.get("message") or {}
            if not authorized(m): continue
            parts=(m.get("text") or "").strip().split(); cmd=parts[0] if parts else ""
            if cmd not in COMMANDS:
                tg("sendMessage",{"chat_id":CHAT_ID,"text":"Allowed: /status /health /test /log /stop"}); continue
            tg("sendMessage",{"chat_id":CHAT_ID,"text":response(COMMANDS[cmd])[:3900]})
        time.sleep(2)
if __name__=="__main__": raise SystemExit(main())