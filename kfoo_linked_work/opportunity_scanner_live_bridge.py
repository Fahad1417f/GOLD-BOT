from __future__ import annotations

"""Live multi-symbol bridge for Opportunity Scanner V2.

Reads candidate snapshots produced by an upstream KFOO/market collector.
It never collects market data itself and never places orders. When a new
snapshot arrives, it ranks all symbols, selects at most one winner, and
optionally sends the selected opportunity to Telegram.
"""

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from opportunity_scanner_v2 import OpportunityScannerV2
from telegram_notifier import notify_opportunity


def load_snapshot(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("candidates", payload) if isinstance(payload, dict) else payload
    if not isinstance(raw, list):
        raise ValueError("snapshot must contain a JSON list or {candidates:[...]}")
    return [x for x in raw if isinstance(x, dict)]


def run_once(path: Path, scanner: OpportunityScannerV2) -> dict[str, Any]:
    candidates = load_snapshot(path)
    result = scanner.select(candidates)
    output = result.to_dict()
    output["candidate_count"] = len(candidates)
    if result.status == "SELECTED" and result.selected is not None:
        output["telegram"] = notify_opportunity(result.selected.to_dict())
    else:
        output["telegram"] = {"ok": True, "sent": False, "reason": result.status}
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", default=os.getenv("GOLDBOT_OPPORTUNITY_SNAPSHOT", "opportunity_candidates.json"))
    parser.add_argument("--poll-ms", type=int, default=int(os.getenv("GOLDBOT_OPPORTUNITY_POLL_MS", "500")))
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    path = Path(args.snapshot)
    scanner = OpportunityScannerV2()
    last_hash = ""

    while True:
        if path.exists():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != last_hash:
                result = run_once(path, scanner)
                print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
                last_hash = digest
                if args.once:
                    return 0
        elif args.once:
            print(f"OPPORTUNITY_SNAPSHOT_NOT_FOUND={path}")
            return 1
        time.sleep(max(0.05, args.poll_ms / 1000.0))


if __name__ == "__main__":
    raise SystemExit(main())
