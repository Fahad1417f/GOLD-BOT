from __future__ import annotations

import json
import os
import subprocess
import sys
import time

MODULE = "kfoo_linked_work.vision_live_capture_v4"
TIMEOUT_SECONDS = float(os.getenv("GOLDBOT_VISION_CYCLE_TIMEOUT", "12"))
INTERVAL_SECONDS = max(3.0, float(os.getenv("GOLDBOT_VISION_INTERVAL_SECONDS", "15")))
OUTPUT_DIR = os.getenv("GOLDBOT_VISION_OUTPUT_DIR", "artifacts/vision")


def _relay_output(pipe, stream_name: str) -> None:
    """Relay child output without trusting the Windows console encoding."""
    try:
        for raw_line in iter(pipe.readline, b""):
            if not raw_line:
                break
            line = raw_line.decode("utf-8", errors="backslashreplace").rstrip("\r\n")
            try:
                print(f"CHILD_{stream_name}={line}", flush=True)
            except UnicodeEncodeError:
                safe = line.encode("ascii", errors="backslashreplace").decode("ascii")
                print(f"CHILD_{stream_name}={safe}", flush=True)
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def run_cycle(cycle: int) -> None:
    print(json.dumps({"cycle": cycle, "phase": "START", "execution": "OFF"}, ensure_ascii=False), flush=True)
    env = os.environ.copy()
    env["GOLDBOT_REAL_TRADING"] = "OFF"
    env["GOLDBOT_DEMO_TRADING"] = "OFF"
    env["GOLDBOT_FAST_TRADE"] = "OFF"
    env["GOLDBOT_VISION_TRACE"] = "ON"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    cmd = [sys.executable, "-u", "-m", MODULE, "--output-dir", OUTPUT_DIR]
    started = time.monotonic()
    try:
        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False, bufsize=0)
        import threading
        stdout_thread = threading.Thread(target=_relay_output, args=(proc.stdout, "STDOUT"), daemon=True)
        stderr_thread = threading.Thread(target=_relay_output, args=(proc.stderr, "STDERR"), daemon=True)
        stdout_thread.start()
        stderr_thread.start()
        try:
            returncode = proc.wait(timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=2)
            except Exception:
                pass
            elapsed = round(time.monotonic() - started, 2)
            print(json.dumps({"cycle": cycle, "phase": "TIMEOUT", "timeout_seconds": TIMEOUT_SECONDS, "elapsed_seconds": elapsed, "reason": "VISION_CYCLE_TIMEOUT", "execution": "OFF"}, ensure_ascii=False), flush=True)
            return
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
        elapsed = round(time.monotonic() - started, 2)
        print(json.dumps({"cycle": cycle, "phase": "END", "returncode": returncode, "elapsed_seconds": elapsed, "execution": "OFF"}, ensure_ascii=False), flush=True)
    except Exception as exc:
        print(json.dumps({"cycle": cycle, "phase": "ERROR", "reason": f"WATCHDOG_ERROR:{type(exc).__name__}:{exc}", "execution": "OFF"}, ensure_ascii=False, default=str), flush=True)


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
