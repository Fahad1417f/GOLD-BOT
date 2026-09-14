from __future__ import annotations
import json
import os
import subprocess
import sys
import time

MODULE = "kfoo_linked_work.vision_live_capture_v5"
TIMEOUT_SECONDS = float(os.getenv("GOLDBOT_VISION_CYCLE_TIMEOUT", "12"))
INTERVAL_SECONDS = max(3.0, float(os.getenv("GOLDBOT_VISION_INTERVAL_SECONDS", "15")))
OUTPUT_DIR = os.getenv("GOLDBOT_VISION_OUTPUT_DIR", "artifacts/vision")


def relay(pipe, name):
    try:
        for raw in iter(pipe.readline, b""):
            if not raw:
                break
            line = raw.decode("utf-8", "backslashreplace").rstrip("\r\n")
            print(f"CHILD_{name}={line.encode('ascii', 'backslashreplace').decode('ascii')}", flush=True)
    finally:
        try: pipe.close()
        except Exception: pass


def run_cycle(cycle):
    print(json.dumps({"cycle":cycle,"phase":"START","execution":"OFF"}), flush=True)
    env = os.environ.copy()
    env.update({"GOLDBOT_REAL_TRADING":"OFF","GOLDBOT_DEMO_TRADING":"OFF","GOLDBOT_FAST_TRADE":"OFF","GOLDBOT_VISION_TRACE":"ON","PYTHONUTF8":"1","PYTHONIOENCODING":"utf-8"})
    proc = subprocess.Popen([sys.executable,"-u","-m",MODULE,"--output-dir",OUTPUT_DIR], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False, bufsize=0)
    import threading
    threading.Thread(target=relay,args=(proc.stdout,"STDOUT"),daemon=True).start()
    threading.Thread(target=relay,args=(proc.stderr,"STDERR"),daemon=True).start()
    started=time.monotonic()
    try:
        rc=proc.wait(timeout=TIMEOUT_SECONDS)
        print(json.dumps({"cycle":cycle,"phase":"END","returncode":rc,"elapsed_seconds":round(time.monotonic()-started,2),"execution":"OFF"}), flush=True)
    except subprocess.TimeoutExpired:
        proc.kill()
        try: proc.wait(timeout=2)
        except Exception: pass
        print(json.dumps({"cycle":cycle,"phase":"TIMEOUT","timeout_seconds":TIMEOUT_SECONDS,"elapsed_seconds":round(time.monotonic()-started,2),"reason":"VISION_CYCLE_TIMEOUT","execution":"OFF"}), flush=True)


def main():
    print("VISION_WATCHDOG=ON", flush=True)
    print(f"CYCLE_TIMEOUT_SECONDS={TIMEOUT_SECONDS:g}", flush=True)
    print(f"INTERVAL_SECONDS={INTERVAL_SECONDS:g}", flush=True)
    print("EXECUTION=OFF", flush=True)
    cycle=0
    while True:
        cycle+=1
        run_cycle(cycle)
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
