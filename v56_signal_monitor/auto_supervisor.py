from __future__ import annotations
import json, os, subprocess, time
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(os.getenv('GOLDBOT_ROOT', Path(__file__).resolve().parents[1])).resolve()
BUILD=ROOT/'v56_build'
LOG=Path(os.getenv('GOLDBOT_MONITOR_LOG', ROOT/'v56_monitor.log'))
STATE=ROOT/'supervisor_state.json'
INTERVAL=float(os.getenv('GOLDBOT_SUPERVISOR_INTERVAL','15'))
STALE=float(os.getenv('GOLDBOT_STALE_SECONDS','180'))
MAX_RESTARTS=int(os.getenv('GOLDBOT_MAX_RESTARTS','3'))
SAFE_MODE=True
KNOWN_RUNTIME_ERRORS=('ModuleNotFoundError','ImportError','TypeError','Traceback (most recent call last)')
KNOWN_ANALYSIS_ERROR="analyze_timeframe() missing 1 required positional argument: 'tf'"
def now(): return datetime.now(timezone.utc).isoformat()
def write_state(**extra):
    state={'supervisor':'ONLINE','safe_mode':SAFE_MODE,'execution':'OFF','updated_at':now(),**extra}
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
def read_log():
    try: return LOG.read_text(encoding='utf-8',errors='ignore')
    except FileNotFoundError: return ''
def diagnose(text):
    if KNOWN_ANALYSIS_ERROR in text: return {'class':'CODE_INTEGRATION_ERROR','repair':'BLOCK_AND_REPORT','detail':KNOWN_ANALYSIS_ERROR}
    for e in KNOWN_RUNTIME_ERRORS:
        if e in text: return {'class':'RUNTIME_ERROR','repair':'RESTART_AND_RETEST','detail':e}
    return {'class':'NONE','repair':'NONE','detail':''}
def write_improvement(diag):
    if diag['class']=='NONE': return
    p=ROOT/'auto_improvement_proposal.json'
    proposal={'created_at':now(),'status':'PROPOSED_NOT_DEPLOYED','reason':diag,'execution':'OFF','policy':'No source-code self-modification is permitted; proposed changes require tests before deployment.'}
    p.write_text(json.dumps(proposal,ensure_ascii=False,indent=2),encoding='utf-8')
def launch_monitor():
    bat=BUILD/'run_v56_overnight_readonly.bat'
    if not bat.exists(): return None
    return subprocess.Popen(['cmd.exe','/c',str(bat)],cwd=str(BUILD),creationflags=getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0))
def main():
    write_state(status='STARTING',last_error=None,restarts=0)
    proc=None; restarts=0; last_size=-1; stale_since=None
    while True:
        text=read_log(); diag=diagnose(text); write_improvement(diag)
        if diag['class']=='CODE_INTEGRATION_ERROR':
            if proc and proc.poll() is None: proc.terminate()
            write_state(status='SAFE_MODE',last_error=diag['detail'],restarts=restarts,action='BLOCKED_UNSAFE_SELF_EDIT')
            time.sleep(INTERVAL); continue
        if proc is None or proc.poll() is not None:
            if restarts>=MAX_RESTARTS:
                write_state(status='SAFE_MODE',last_error=diag['detail'] or 'monitor_exit',restarts=restarts,action='RESTART_LIMIT_REACHED')
                time.sleep(INTERVAL); continue
            proc=launch_monitor()
            if proc is None: write_state(status='SAFE_MODE',last_error='V56_BUILD_NOT_FOUND',restarts=restarts)
            else:
                restarts+=1; write_state(status='RUNNING',last_error=None,restarts=restarts,action='MONITOR_STARTED')
        else:
            size=len(text)
            if size==last_size: stale_since=stale_since or time.time()
            else: stale_since=None; last_size=size
            if stale_since and time.time()-stale_since>STALE:
                proc.terminate(); proc=None; write_state(status='RESTARTING',last_error='STALE_MONITOR_LOG',restarts=restarts,action='STALE_RESTART')
        time.sleep(INTERVAL)
if __name__=='__main__': main()