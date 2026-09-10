from __future__ import annotations

"""Read-only adapter for explicit KFOO markers emitted by the V56 monitor."""

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


def _first_present(text: str, patterns: tuple[str, ...], default: str = "neutral") -> str:
    for pattern in patterns:
        value = _latest(text, pattern, "__MISSING__")
        if value != "__MISSING__":
            return value
    return default


def _frame(text: str, tf: str) -> dict[str, Any]:
    upper = tf.upper()
    direction = _latest(text, rf"DIRECTION_{upper}=([^\s]+)")
    active = _first_present(
        text,
        (rf"KFOO_ACTIVE_{upper}=([^\s]+)", rf"ACTIVE_KFOO_{upper}=([^\s]+)"),
    )
    table = _latest(text, rf"KFOO_TABLE_{upper}=([^\s]+)", "UNKNOWN")
    verified = table.upper() == "PASS" and _normalize_side(direction) != "neutral" and _normalize_side(active) != "neutral"

    # The signal engine contract needs component fields. We only populate those
    # components when the runtime has explicitly emitted them; no values are
    # inferred from the aggregate/table marker.
    components = {
        "kfoo_ai": _first_present(text, (rf"KFOO_AI_{upper}=([^\s]+)",), "neutral"),
        "rsi": _first_present(text, (rf"RSI_{upper}=([^\s]+)",), "neutral"),
        "whale": _first_present(text, (rf"KFOO_WHALE_{upper}=([^\s]+)", rf"WHALE_{upper}=([^\s]+)"), "neutral"),
        "table": active if table.upper() == "PASS" else "neutral",
    }
    return {
        "samples": [{"active_kfoo": active, "direction": direction}],
        "active_kfoo": active,
        "analysis": {
            "direction": direction,
            "active_kfoo": active,
            "kfoo_table_detected": table.upper() == "PASS",
            "kfoo_table_direction": {"bias": _normalize_side(active)},
            "kfoo_table": {
                "aggregates": {
                    "timeframes": {"raw": _latest(text, rf"KFOO_TF_AGG_{upper}=([^\r\n]+)", "unknown")},
                    "indicators": {"raw": _latest(text, rf"KFOO_IND_AGG_{upper}=([^\r\n]+)", "unknown")},
                },
                "timeframes": {tf: {"signal": direction}},
            },
            "components": components,
        },
        "direction": direction,
        "strength": 1.0 if verified else 0.0,
        "verified": verified,
        "source": "v56_monitor_log_markers",
    }


def parse_live_kfoo(text: str) -> tuple[dict[str, dict], dict[str, Any]]:
    frames = {tf: _frame(text, tf) for tf in REQUIRED_TFS}
    missing = [tf for tf, value in frames.items() if not value["verified"]]
    if missing:
        raise ValueError(f"KFOO_LIVE_MARKERS_INCOMPLETE:{','.join(missing)}")

    # The 15m leader close marker is optional; absence stays false for safety.
    closed_raw = _latest(text, r"LEADER_CLOSED=([^\s]+)", "false").lower()
    timing = {
        "leader_closed": closed_raw == "true",
        "5m": frames["5m"]["direction"],
        "3m": frames["3m"]["direction"],
    }
    return frames, timing
