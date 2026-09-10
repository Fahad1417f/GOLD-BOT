from __future__ import annotations

"""Read-only adapter for the live KFOO markers emitted by the V56 monitor.

The adapter converts only explicit machine-readable monitor markers into the
normalized KFOO analysis contract consumed by the V56 signal engine. It never
creates candle data or infers KFOO values from screenshots/pixels.
"""

import re
from typing import Any

REQUIRED_TFS = ("4h", "1h", "15m", "5m", "3m")


def _latest(text: str, pattern: str, default: str = "neutral") -> str:
    matches = list(re.finditer(pattern, text or "", re.I | re.M))
    return matches[-1].group(1).strip() if matches else default


def _normalize_side(value: str | None) -> str:
    v = (value or "neutral").strip().lower()
    if v in {"buy", "long", "bull", "bullish", "شراء"}:
        return "long"
    if v in {"sell", "short", "bear", "bearish", "بيع"}:
        return "short"
    return "neutral"


def _frame(text: str, tf: str) -> dict[str, Any]:
    upper = tf.upper()
    direction = _latest(text, rf"DIRECTION_{upper}=([^\\s]+)")
    active = _latest(text, rf"KFOO_ACTIVE_{upper}=([^\\s]+)")
    table = _latest(text, rf"KFOO_TABLE_{upper}=([^\\s]+)", "UNKNOWN")
    analysis = {
        "direction": direction,
        "active_kfoo": active,
        "kfoo_table_detected": table.upper() == "PASS",
        "kfoo_table_direction": {"bias": _normalize_side(active)},
        "kfoo_table": {
            "aggregates": {
                "timeframes": {"raw": _latest(text, rf"KFOO_TF_AGG_{upper}=([^\\r\\n]+)", "unknown")},
                "indicators": {"raw": _latest(text, rf"KFOO_IND_AGG_{upper}=([^\\r\\n]+)", "unknown")},
            },
            "timeframes": {tf: {"signal": direction}},
        },
    }
    return {
        "samples": [{"active_kfoo": active, "direction": direction}],
        "active_kfoo": active,
        "analysis": analysis,
        "direction": direction,
        "verified": table.upper() == "PASS" and _normalize_side(direction) != "neutral",
        "source": "v56_monitor_log_markers",
    }


def parse_live_kfoo(text: str) -> tuple[dict[str, dict], dict[str, Any]]:
    frames = {tf: _frame(text, tf) for tf in REQUIRED_TFS}
    missing = [tf for tf, value in frames.items() if not value["verified"]]
    if missing:
        raise ValueError(f"KFOO_LIVE_MARKERS_INCOMPLETE:{','.join(missing)}")

    timing = {
        "leader_closed": _latest(text, r"LEADER_CLOSED=([^\\s]+)", "unknown").lower() == "true",
        "5m": _latest(text, r"DIRECTION_5M=([^\\s]+)", "neutral"),
        "3m": _latest(text, r"DIRECTION_3M=([^\\s]+)", "neutral"),
    }
    return frames, timing
