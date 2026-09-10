from __future__ import annotations
import json, os, re, time
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(os.getenv("GOLDBOT_ROOT", Path(__file__).resolve().parents[1])).resolve()
LOG = Path(os.getenv("GOLDBOT_MONITOR_LOG", ROOT / "v56_monitor.log"))
STATE = ROOT / "development_state.json"
PROPOSALS = ROOT / "auto_development_proposals.jsonl"
MIN_INTERVAL = float(os.getenv("GOLDBOT_DEVELOPMENT_INTERVAL", "300"))
MIN_CONFIDENCE = float(os.getenv("GOLDBOT_DEVELOPMENT_MIN_CONFIDENCE", "0.80"))

def now():
    return datetime.now(timezone.utc).isoformat()

def read_log():
    try:
        return LOG.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return ""

def latest(text, pattern, default="unknown"):
    m = list(re.finditer(pattern, text, re.I | re.M))
    return m[-1].group(1).strip() if m else default

def build_metrics(text):
    return {
        "direction_4h": latest(text, r"DIRECTION_4H=([^\s]+)"),
        "direction_1h": latest(text, r"DIRECTION_1H=([^\s]+)"),
        "direction_15m": latest(text, r"DIRECTION_15M=([^\s]+)"),
        "direction_5m": latest(text, r"DIRECTION_5M=([^\s]+)"),
        "direction_3m": latest(text, r"DIRECTION_3M=([^\s]+)"),
        "kfoo_4h": latest(text, r"KFOO_TABLE_4H=([^\s]+)", "UNKNOWN"),
        "kfoo_1h": latest(text, r"KFOO_TABLE_1H=([^\s]+)", "UNKNOWN"),
        "kfoo_15m": latest(text, r"KFOO_TABLE_15M=([^\s]+)", "UNKNOWN"),
        "kfoo_confidence": float(latest(text, r"KFOO_TABLE_(?:4H|1H|15M)=PASS[^\n]*confidence=([0-9.]+)", "0")),
        "tracebacks": len(re.findall(r"Traceback \(most recent call last\)", text)),
        "connection_errors": len(re.findall(r"Connection(?:Error|RefusedError)", text)),
    }

def propose(metrics):
    issues = []
    if metrics["kfoo_4h"] != "PASS" or metrics["kfoo_1h"] != "PASS" or metrics["kfoo_15m"] != "PASS":
        issues.append("KFOO coverage below required gravity/leader set")
    if metrics["kfoo_confidence"] and metrics["kfoo_confidence"] < MIN_CONFIDENCE:
        issues.append("KFOO visual confidence below configured threshold")
    if metrics["tracebacks"]:
        issues.append("runtime exceptions detected")
    if metrics["connection_errors"]:
        issues.append("connection failures detected")
    dirs = [metrics[x] for x in ("direction_4h","direction_1h","direction_15m")]
    if len(set(d for d in dirs if d in ("long","short"))) > 1:
        issues.append("gravity/leader direction disagreement")
    return issues

def evaluate():
    text = read_log()
    metrics = build_metrics(text)
    issues = propose(metrics)
    status = "NO_CHANGE_NEEDED" if not issues else "PROPOSAL_ONLY"
    result = {
        "updated_at": now(),
        "status": status,
        "execution": "OFF",
        "self_modification": "DISABLED",
        "metrics": metrics,
        "issues": issues,
        "validation_gate": [
            "BACKUP_OR_BRANCH",
            "SYNTAX_TEST",
            "UNIT_TEST",
            "INTEGRATION_TEST",
            "LIVE_READ_TEST",
            "QUALITY_CHECK",
            "POST_DEPLOY_WATCH",
            "ROLLBACK_ON_REGRESSION",
        ],
    }
    STATE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if issues:
        PROPOSALS.parent.mkdir(parents=True, exist_ok=True)
        with PROPOSALS.open("a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
    return result

if __name__ == "__main__":
    print(json.dumps(evaluate(), ensure_ascii=False, indent=2))
