from __future__ import annotations

"""Low-latency read-only V56 signal lane.

The fast lane watches an upstream KFOO JSON file instead of re-running the full
TradingView verification stack for every tick. The full E2E verifier remains the
source of truth for verified OHLC/H&S. This process only promotes already-supplied
analysis and always posts execution=OFF.
"""

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen

from signal_engine_v56 import promote


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("analysis file must contain a JSON object")
    return value


def _post(url: str, payload: dict, timeout: float = 2.0) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def run_once(analysis: dict, timing: dict | None = None, hns: dict | None = None,
             webhook: str = "http://127.0.0.1:3000/api/webhooks/tradingview") -> dict:
    sig = promote(analysis, timing=timing or {}, verified_hns_mtf=hns)
    payload = {
        "eventKey": sig.event_key or f"fast-{sig.level}-{sig.direction}",
        "eventType": sig.level,
        "level": sig.level,
        "direction": sig.direction,
        "confidence": sig.score,
        "score": sig.score,
        "symbol": "XAUUSD",
        "timeframe": "15m",
        "gravity": {"4h": "from_analysis", "1h": "from_analysis"},
        "leader": {"15m": sig.direction},
        "timing": timing or {},
        "kfoo": {"source": "fast_file_lane", "live": True},
        "head_shoulders": hns or {},
        "market_context": sig.market_context or {},
        "reasons": sig.reasons or [],
        "execution": "OFF",
    }
    response = _post(webhook, payload)
    if response.get("execution") != "OFF":
        raise RuntimeError("WEBHOOK_EXECUTION_GUARD_FAILED")
    return {"signal": sig.to_dict(), "webhook": response}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--analysis-file", default=os.getenv("GOLDBOT_KFOO_ANALYSIS_FILE", "kfoo_analysis.json"))
    p.add_argument("--timing-file", default=os.getenv("GOLDBOT_TIMING_FILE", "kfoo_timing.json"))
    p.add_argument("--hns-file", default=os.getenv("GOLDBOT_VERIFIED_HNS_FILE", "verified_hns_mtf.json"))
    p.add_argument("--webhook", default=os.getenv("GOLDBOT_WEBHOOK_URL", "http://127.0.0.1:3000/api/webhooks/tradingview"))
    p.add_argument("--poll-ms", type=int, default=int(os.getenv("GOLDBOT_FAST_POLL_MS", "500")))
    p.add_argument("--once", action="store_true")
    args = p.parse_args()

    analysis_path = Path(args.analysis_file)
    timing_path = Path(args.timing_file)
    hns_path = Path(args.hns_file)
    last_hash = ""

    while True:
        if analysis_path.exists():
            raw = analysis_path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            if digest != last_hash:
                analysis = json.loads(raw.decode("utf-8"))
                timing = _load(timing_path) if timing_path.exists() else {}
                hns = _load(hns_path) if hns_path.exists() else None
                result = run_once(analysis, timing, hns, args.webhook)
                sig = result["signal"]
                print(
                    f"FAST_SIGNAL=UPDATED level={sig['level']} direction={sig['direction']} "
                    f"entry_ready={sig['entry_ready']}",
                    flush=True,
                )
                last_hash = digest
                if args.once:
                    return 0
        elif args.once:
            raise SystemExit(f"ANALYSIS_FILE_NOT_FOUND={analysis_path}")
        time.sleep(max(0.05, args.poll_ms / 1000.0))


if __name__ == "__main__":
    raise SystemExit(main())
