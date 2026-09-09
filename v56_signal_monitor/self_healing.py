from __future__ import annotations
import json, os, subprocess
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(os.getenv("GOLDBOT_ROOT", Path(__file__).resolve().parents[1])).resolve()
LOG = Path(os.getenv("GOLDBOT_MONITOR_LOG", ROOT / "v56_monitor.log"))
REPAIR_LOG = ROOT / "auto_repair.log"
PROPOSAL = ROOT / "auto_improvement_proposal.json"
KNOWN_ANALYSIS_ERROR = "analyze_timeframe() missing 1 required positional argument: 'tf'"

def now():
    return datetime.now(timezone.utc).isoformat()

def append(msg):
    REPAIR_LOG.parent.mkdir(parents=True, exist_ok=True)
    with REPAIR_LOG.open("a", encoding="utf-8") as f:
        f.write(f"{now()} {msg}\n")

def read_log():
    try:
        return LOG.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return ""

def diagnose(text):
    if KNOWN_ANALYSIS_ERROR in text:
        return {"class":"CODE_INTEGRATION_ERROR","repair":"QUARANTINE_AND_PROPOSE","detail":KNOWN_ANALYSIS_ERROR}
    if "ModuleNotFoundError" in text or "ImportError" in text:
        return {"class":"DEPENDENCY_ERROR","repair":"RESTART_AND_RETEST","detail":"dependency/import failure"}
    if "ConnectionError" in text or "ConnectionRefusedError" in text:
        return {"class":"CONNECTION_ERROR","repair":"RECONNECT_AND_RETEST","detail":"connection failure"}
    if "Traceback (most recent call last)" in text:
        return {"class":"RUNTIME_ERROR","repair":"RESTART_AND_RETEST","detail":"runtime exception"}
    return {"class":"NONE","repair":"NONE","detail":""}

def write_proposal(diag):
    if diag["class"] == "NONE":
        return
    proposal = {
        "created_at": now(),
        "status": "PROPOSED_NOT_DEPLOYED",
        "reason": diag,
        "execution": "OFF",
        "validation_gate": ["BACKUP_OR_BRANCH","SYNTAX_TEST","UNIT_TEST","INTEGRATION_TEST","LIVE_READ_TEST","QUALITY_CHECK","DEPLOY","POST_DEPLOY_WATCH","ROLLBACK_ON_REGRESSION"],
        "known_safe_action": "restart/reconnect/retest",
        "code_self_modification": "DISABLED"
    }
    PROPOSAL.write_text(json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")

def restartable_repair():
    append("REPAIR_ATTEMPT=RESTART_RECONNECT")
    return {"repair":"RESTART_AND_RETEST","ok":True}

def validate_candidate(path):
    result = {"path":str(path),"syntax":"NOT_RUN","ok":False}
    try:
        import sys
        cp = subprocess.run([sys.executable, "-m", "py_compile", str(path)], cwd=str(ROOT), capture_output=True, text=True, timeout=30)
        result["syntax"] = "PASS" if cp.returncode == 0 else "FAIL"
        result["syntax_error"] = (cp.stderr or cp.stdout)[-2000:]
        result["ok"] = cp.returncode == 0
    except Exception as e:
        result["syntax"] = "ERROR"
        result["syntax_error"] = repr(e)
    return result

def evaluate_development():
    diag = diagnose(read_log())
    write_proposal(diag)
    return {"diagnosis":diag,"proposal":str(PROPOSAL) if diag["class"] != "NONE" else None}
