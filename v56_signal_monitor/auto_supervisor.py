from __future__ import annotations
import json, os, subprocess, time
from pathlib import Path
from datetime import datetime, timezone
from self_healing import diagnose, write_proposal, append
from auto_developer import evaluate as evaluate_development

ROOT=Path(os.getenv("GOLDBOT_ROOT", Path(__file__).resolve().parents[1])).resolve()
BUILD=Path(os.getenv("GOLDBOT_BUILD_PATH",ROOT/"v56_build")).resolve()
LOG=Path(os.getenv("GOLDBOT_MONITOR_LOG", ROOT/"v56_monitor.log"))
BRIDGE_LOG=Path(os.getenv("GOLDBOT_BRIDGE_LOG", ROOT/"github_bridge.log"))
BRIDGE=ROOT/"v56_signal_monitor"/"github_state_bridge.py"
STATE=ROOT/"supervisor_state.json"
INTERVAL=float(os.getenv("GOLDBOT_SUPERVISOR_INTERVAL","15"))
STALE=float(os.getenv("GOLDBOT_STALE_SECONDS","180"))
MAX_RESTARTS=int(os.getenv("GOLDBOT_MAX_RESTARTS","3"))
SAFE_MODE=True

def now(): return datetime.now(timezone.utc).isoformat()

def write_state(**extra):
    state={"supervisor":"ONLINE","safe_mode":SAFE_MODE,"execution":"OFF","updated_at":now(),**extra}
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")

def read_log():
    try: return LOG.read_text(encoding="utf-8",errors="ignore")
    except FileNotFoundError: return ""

def resolve_build():
    candidates=[BUILD]
    parent=ROOT.parent
    for p in sorted(parent.glob("GOLD_BOT_V56*")):
        if (p/"v56_build"/"run_v56_overnight_readonly.bat").exists(): candidates.append(p/"v56_build")
    for p in candidates:
        if (p/"run_v56_overnight_readonly.bat").exists(): return p
    return None

def launch_bridge():
    if not BRIDGE.exists():
        return None
    BRIDGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    handle=open(BRIDGE_LOG,"a",encoding="utf-8",errors="ignore")
    return subprocess.Popen([os.getenv("PYTHON","python"),str(BRIDGE)],cwd=str(ROOT),
        stdout=handle,stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0))

def launch_monitor():
    build=resolve_build()
    if build is None: return None
    bat=build/"run_v56_overnight_readonly.bat"
    # Capture the real monitor stdout/stderr into the supervisor log so health,
    # KFOO and signal tracking are based on actual runtime output.
    log_handle=open(LOG,"a",encoding="utf-8",errors="ignore")
    return subprocess.Popen(["cmd.exe","/c",str(bat)],cwd=str(build),
        stdout=log_handle,stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0))

def main():
    proc=None
    bridge_proc=None
    restarts=0
    last_size=-1
    stale_since=None
    write_state(status="STARTING",last_error=None,restarts=0,repair="NONE",development="WATCHING")
    try:
        dev=evaluate_development()
        development_status=dev.get("status","UNKNOWN")
    except Exception as e:
        development_status="ERROR"
        append("DEVELOPMENT_EVALUATION_ERROR="+type(e).__name__+":"+str(e))
    while True:
        text=read_log()
        if bridge_proc is None or bridge_proc.poll() is not None:
            bridge_proc=launch_bridge()
            if bridge_proc is not None:
                append("REPAIR_RESULT=STATE_BRIDGE_RESTART_PASS")
        diag=diagnose(text)
        try:
            dev=evaluate_development()
            development_status=dev.get("status","UNKNOWN")
        except Exception as e:
            development_status="ERROR"
            append("DEVELOPMENT_EVALUATION_ERROR="+type(e).__name__+":"+str(e))
        if diag["class"]!="NONE":
            write_proposal(diag)
        if diag["class"]=="CODE_INTEGRATION_ERROR":
            if proc and proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=10)
                proc=None
            write_state(status="SAFE_MODE",last_error=diag["detail"],restarts=restarts,repair="QUARANTINE_AND_PROPOSE",development=development_status)
            time.sleep(INTERVAL)
            continue
        if proc is None or proc.poll() is not None:
            if restarts>=MAX_RESTARTS:
                write_state(status="SAFE_MODE",last_error=diag["detail"] or "monitor_exit",restarts=restarts,repair="RESTART_LIMIT_REACHED",development=development_status)
                time.sleep(INTERVAL)
                continue
            proc=launch_monitor()
            if proc is None:
                write_state(status="SAFE_MODE",last_error="V56_BUILD_NOT_FOUND_OR_UNRESOLVED",restarts=restarts,repair="BUILD_MISSING",development=development_status)
            else:
                restarts+=1
                append("REPAIR_RESULT=MONITOR_RESTART_PASS")
                write_state(status="RUNNING",last_error=None,restarts=restarts,repair="RESTART_AND_RETEST",
                            bridge="RUNNING" if bridge_proc and bridge_proc.poll() is None else "DEGRADED",
                            development=development_status)
        else:
            size=len(text)
            if size==last_size:
                stale_since=stale_since or time.time()
            else:
                stale_since=None
                last_size=size
            if stale_since and time.time()-stale_since>STALE:
                proc.terminate()
                proc=None
                append("REPAIR_RESULT=STALE_RESTART")
                write_state(status="RESTARTING",last_error="STALE_MONITOR_LOG",restarts=restarts,repair="STALE_RESTART",development=development_status)
        time.sleep(INTERVAL)

if __name__=="__main__":
    main()
