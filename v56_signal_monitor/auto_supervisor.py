from __future__ import annotations
import json, os, subprocess, time
from pathlib import Path
from datetime import datetime, timezone
from self_healing import diagnose, write_proposal, append

ROOT=Path(os.getenv("GOLDBOT_ROOT", Path(__file__).resolve().parents[1])).resolve()
BUILD=ROOT/"v56_build"
LOG=Path(os.getenv("GOLDBOT_MONITOR_LOG", ROOT/"v56_monitor.log"))
STATE=ROOT/"supervisor_state.json"
INTERVAL=float(os.getenv("GOLDBOT_SUPERVISOR_INTERVAL","15"))
STALE=float(os.getenv("GOLDBOT_STALE_SECONDS","180"))
MAX_RESTARTS=int(os.getenv("GOLDBOT_MAX_RESTARTS","3"))
SAFE_MODE=True

def now(): return datetime.now(timezone.utc).isoformat()

def write_state(**extra):
    state={"supervisor":"ONLINE","safe_mode":SAFE_MODE,"execution":"OFF","updated_at":now(),**extra}
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")

def read_log():
    try: return LOG.read_text(encoding="utf-8",errors="ignore")
    except FileNotFoundError: return ""

def launch_monitor():
    bat=BUILD/"run_v56_overnight_readonly.bat"
    if not bat.exists(): return None
    return subprocess.Popen(["cmd.exe","/c",str(bat)],cwd=str(BUILD),creationflags=getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0))

def main():
    write_state(status="STARTING",last_error=None,restarts=0,repair="NONE",development="WATCHING")
    proc=None; restarts=0; last_size=-1; stale_since=None
    while True:
        text=read_log()
        diag=diagnose(text)
        if diag["class"]!="NONE":
            write_proposal(diag)
        if diag["class"]=="CODE_INTEGRATION_ERROR":
            if proc and proc.poll() is None:
                proc.terminate()
                proc=None
            write_state(status="SAFE_MODE",last_error=diag["detail"],restarts=restarts,repair="QUARANTINE_AND_PROPOSE",development="PROPOSAL_ONLY")
            time.sleep(INTERVAL)
            continue
        if proc is None or proc.poll() is not None:
            if restarts>=MAX_RESTARTS:
                write_state(status="SAFE_MODE",last_error=diag["detail"] or "monitor_exit",restarts=restarts,repair="RESTART_LIMIT_REACHED",development="PROPOSAL_ONLY")
                time.sleep(INTERVAL)
                continue
            proc=launch_monitor()
            if proc is None:
                write_state(status="SAFE_MODE",last_error="V56_BUILD_NOT_FOUND",restarts=restarts,repair="BUILD_MISSING")
            else:
                restarts+=1
                append("REPAIR_RESULT=MONITOR_RESTART_PASS")
                write_state(status="RUNNING",last_error=None,restarts=restarts,repair="RESTART_AND_RETEST",development="WATCHING")
        else:
            size=len(text)
            if size==last_size: stale_since=stale_since or time.time()
            else: stale_since=None; last_size=size
            if stale_since and time.time()-stale_since>STALE:
                proc.terminate(); proc=None
                append("REPAIR_RESULT=STALE_RESTART")
                write_state(status="RESTARTING",last_error="STALE_MONITOR_LOG",restarts=restarts,repair="STALE_RESTART")
        time.sleep(INTERVAL)

if __name__=="__main__":
    main()
