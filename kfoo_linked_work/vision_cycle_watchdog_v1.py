from __future__ import annotations

import json
import os
import subprocess
import sys
import time

MODULE = "kfoo_linked_work.vision_live_capture_v3"
TIMEOUT_SECONDS = float(os.getenv("GOLDBOT_VISION_CYCLE_TIMEOUT", "12"))
INTERVAL_SECONDS = max(3.0, float(os.getenv("GOLDBOT_VISION_INTERVAL_SECONDS", "15")))
OUTPUT_DIR = os.getenv("GOLDBOT_VISION_OUTPUT_DIR", "artifacts/vision")


def run_cycle(cycle: int) -> None:
    print(json.dumps({"cycle": cycle, "phase": "START", "execution": "OFF"}, ensure_ascii=False), flush=True)
    env = os.environ.copy()
    env["GOLDBOT_REAL_TRADING"] = "OFF"
    env["GOLDBOT_DEMO_TRADING"] = "OFF"
    env["GOLDBOT_FAST_TRADE"] = "OFF"
    cmd = [sys.executable, "-u", "-m", MODULE, "--output-dir", OUTPUT_DIR]
    started = time.monotonic()
    try:
        completed = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        elapsed = round(time.monotonic() - started, 2)
        if completed.stdout:
            print(completed.stdout.rstrip(), flush=True)
        if completed.stderr:
            print(completed.stderr.rstrip(), flush=True)
        print(json.dumps({"cycle": cycle, "phase": "END", "returncode": completed.returncode, "elapsed_seconds": elapsed, "execution": "OFF"}, ensure_ascii=False), flush=True)
    except subprocess.TimeoutExpired:
        elapsed = round(time.monotonic() - started, 2)
        print(json.dumps({"cycle": cycle, "phase": "TIMEOUT", "timeout_seconds": TIMEOUT_SECONDS, "elapsed_seconds": elapsed, "reason": "VISION_CYCLE_TIMEOUT", "execution": "OFF"}, ensure_ascii=False), flush=True)
    except Exception as exc:
        print(json.dumps({"cycle": cycle, "phase": "ERROR", "reason": f"WATCHDOG_ERROR:{type(exc).__name__}:{exc}", "execution": "OFF"}, ensure_ascii=False), flush=True)


def main() -> int:
    print("VISION_WATCHDOG=ON", flush=True)
    print(f"CYCLE_TIMEOUT_SECONDS={TIMEOUT_SECONDS:g}", flush=True)
    print(f"INTERVAL_SECONDS={INTERVAL_SECONDS:g}", flush=True)
    print("EXECUTION=OFF", flush=True)
    cycle = 0
    while True:
        cycle += 1
        run_cycle(cycle)
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
