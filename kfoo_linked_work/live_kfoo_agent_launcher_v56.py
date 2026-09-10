from __future__ import annotations

"""V56 read-only launcher for the existing visual KFOO agent.

It wires the agent's REAL KFOO table publisher to the verified localhost
TradingView publisher without editing or replacing the original agent.
No synthetic KFOO values are created.
"""

import os
import sys
from pathlib import Path

import requests

REQUIRED_TFS = ("4h", "1h", "15m", "5m", "3m")
PUBLISH_URL = os.getenv("GOLDBOT_KFOO_PUBLISH_URL", "http://127.0.0.1:8765/publish")


def _load_agent():
    agent_dir = Path(os.getenv("GOLDBOT_LIVE_AGENT_DIR", Path(__file__).resolve().parent)).resolve()
    if str(agent_dir) not in sys.path:
        sys.path.insert(0, str(agent_dir))
    import live_vision_agent_fixed as agent
    return agent


def _direction(signal: object) -> str:
    s = str(signal or "").strip().lower()
    if s in {"bullish", "buy", "long"}:
        return "long"
    if s in {"bearish", "sell", "short"}:
        return "short"
    if s in {"neutral", "flat", "wait"}:
        return "neutral"
    raise RuntimeError(f"KFOO_VISUAL_SIGNAL_INVALID:{s}")


def _validate_frame(tf: str, row: dict) -> None:
    signal = row.get("signal")
    _direction(signal)
    # Require the two factual table cells used by the existing KFOO schema when
    # present, but do not invent them if the legacy agent does not expose them.
    if "signal" not in row:
        raise RuntimeError(f"KFOO_VISUAL_FRAME_INVALID:{tf}:signal_missing")


def build_payload(kfoo_table, now: str) -> dict:
    if not getattr(kfoo_table, "detected", False):
        raise RuntimeError("KFOO_VISUAL_TABLE_NOT_DETECTED")

    table = kfoo_table.to_dict()
    tfs = table.get("timeframes") or {}
    missing = [tf for tf in REQUIRED_TFS if not isinstance(tfs.get(tf), dict)]
    if missing:
        raise RuntimeError("KFOO_VISUAL_TABLE_INCOMPLETE:" + ",".join(missing))
    for tf in REQUIRED_TFS:
        _validate_frame(tf, tfs[tf])

    agg = table.get("aggregates") or {}
    tfagg = agg.get("timeframes") or {}
    indagg = agg.get("indicators") or {}
    for name, obj in (("timeframes", tfagg), ("indicators", indagg)):
        for key in ("bullish_pct", "bearish_pct"):
            value = obj.get(key)
            if value is None:
                raise RuntimeError(f"KFOO_VISUAL_{name}_AGGREGATE_INCOMPLETE:{key}")
            value = float(value)
            if not 0.0 <= value <= 100.0:
                raise RuntimeError(f"KFOO_VISUAL_{name}_AGGREGATE_RANGE:{key}")

    bp = float(tfagg["bullish_pct"])
    rp = float(tfagg["bearish_pct"])
    table_bias = "bullish" if bp > rp else "bearish" if rp > bp else "neutral"

    analysis = {}
    for tf in REQUIRED_TFS:
        direction = _direction(tfs[tf].get("signal"))
        analysis[tf] = {
            "active_kfoo": direction,
            "analysis": {
                "direction": direction,
                "kfoo_table_detected": True,
                "kfoo_table_direction": {"bias": table_bias},
                "kfoo_table": table,
            },
        }
    return {
        "analysis": analysis,
        "timing": {"published_at": now, "source": "visual_grid"},
    }


def main() -> int:
    agent = _load_agent()
    original = agent.publish_live_kfoo_markers

    def wired_publish(kfoo_table, now):
        # Preserve the original marker publication first; do not alter its data.
        original(kfoo_table, now)
        if not getattr(kfoo_table, "detected", False):
            agent.monitor_marker("KFOO_PUBLISH=SKIP table_not_detected")
            return
        try:
            payload = build_payload(kfoo_table, now)
            response = requests.post(PUBLISH_URL, json=payload, timeout=3)
            if not response.ok:
                agent.monitor_marker(
                    f"KFOO_PUBLISH=FAIL http_{response.status_code} {response.text[:300]}"
                )
                return
            agent.monitor_marker("KFOO_PUBLISH=PASS source=visual_grid")
        except Exception as exc:
            agent.monitor_marker(f"KFOO_PUBLISH=FAIL {type(exc).__name__}:{exc}")

    agent.publish_live_kfoo_markers = wired_publish
    print(f"V56_KFOO_LAUNCHER=WIRED publisher={PUBLISH_URL}", flush=True)
    print("KFOO_SOURCE_POLICY=REAL_VISUAL_TABLE_ONLY", flush=True)

    entry = getattr(agent, "main", None)
    if not callable(entry):
        raise RuntimeError("LIVE_VISION_AGENT_MAIN_NOT_FOUND")
    return int(entry() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
