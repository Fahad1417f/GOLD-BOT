from __future__ import annotations

"""Unified fail-closed decision gate: KFOO hard evidence -> MTF -> R:R.

This module is decision-only. It never places, enables, or manages orders.
"""

from math import isfinite
from typing import Mapping

from .kfoo_hard_gate_v1 import evaluate_hard_gate


REQUIRED_MTF = ("4h", "1h", "15m", "3m")
GRAVITY_TFS = ("4h", "1h")
ENTRY_TFS = ("15m", "3m")


def _side(value: object) -> str:
    value = str(value or "").strip().lower()
    return {"bullish": "buy", "bearish": "sell", "long": "buy", "short": "sell"}.get(value, value)


def _mtf_gate(mtf: Mapping[str, object] | None, direction: str) -> dict:
    if not isinstance(mtf, Mapping):
        return {"status": "DATA_UNAVAILABLE", "ready": False, "missing": list(REQUIRED_MTF),
                "conflicts": [], "reasons": ["MTF_DATA_UNAVAILABLE"]}

    missing = [tf for tf in REQUIRED_MTF if not isinstance(mtf.get(tf), Mapping)]
    if missing:
        return {"status": "DATA_UNAVAILABLE", "ready": False, "missing": missing,
                "conflicts": [], "reasons": ["MTF_MISSING:" + ",".join(missing)]}

    conflicts = []
    for tf in REQUIRED_MTF:
        observed = _side((mtf[tf] or {}).get("direction"))
        if observed not in {"buy", "sell"}:
            conflicts.append(f"{tf}:INVALID_DIRECTION")
        elif observed != direction:
            conflicts.append(f"{tf}:{observed}")

    # Explicit cross-timeframe conflict is a rejection, not a fabricated confirmation.
    if conflicts:
        return {"status": "REJECTED", "ready": False, "missing": [],
                "conflicts": conflicts, "reasons": ["MTF_DIRECTION_CONFLICT"]}

    return {"status": "CONFIRMED", "ready": True, "missing": [],
            "conflicts": [], "reasons": ["MTF_ALIGNED:" + ",".join(REQUIRED_MTF)]}


def _risk_reward(entry: object, stop: object, target: object, direction: str) -> dict:
    values = (entry, stop, target)
    try:
        entry_f, stop_f, target_f = (float(v) for v in values)
    except (TypeError, ValueError):
        return {"status": "DATA_UNAVAILABLE", "valid": False, "risk": None, "reward": None, "rr": None,
                "reasons": ["RR_NUMERIC_INPUT_REQUIRED"]}

    if not all(isfinite(v) for v in (entry_f, stop_f, target_f)):
        return {"status": "DATA_UNAVAILABLE", "valid": False, "risk": None, "reward": None, "rr": None,
                "reasons": ["RR_NON_FINITE_INPUT"]}

    if direction == "buy":
        risk = entry_f - stop_f
        reward = target_f - entry_f
    else:
        risk = stop_f - entry_f
        reward = entry_f - target_f

    if risk <= 0:
        return {"status": "REJECTED", "valid": False, "risk": risk, "reward": reward, "rr": None,
                "reasons": ["INVALID_STOP_DISTANCE"]}
    if reward <= 0:
        return {"status": "REJECTED", "valid": False, "risk": risk, "reward": reward, "rr": None,
                "reasons": ["INVALID_TARGET_DISTANCE"]}

    rr = reward / risk
    if not isfinite(rr) or rr <= 0:
        return {"status": "REJECTED", "valid": False, "risk": risk, "reward": reward, "rr": None,
                "reasons": ["INVALID_RR"]}

    return {"status": "CONFIRMED", "valid": True, "risk": risk, "reward": reward, "rr": rr,
            "reasons": ["RR_VALID"]}


def evaluate_signal(
    evidence: Mapping[str, str] | None,
    mtf: Mapping[str, object] | None,
    *,
    direction: str,
    entry: object,
    stop: object,
    target: object,
) -> dict:
    side = _side(direction)
    hard = evaluate_hard_gate(evidence, direction=side)
    if hard["status"] != "CONFIRMED":
        return {
            "status": hard["status"],
            "ready": False,
            "execution": "OFF",
            "direction": side,
            "kfoo": hard,
            "mtf": None,
            "risk_reward": None,
            "reasons": hard["reasons"],
        }

    mtf_result = _mtf_gate(mtf, side)
    if mtf_result["status"] != "CONFIRMED":
        return {
            "status": mtf_result["status"],
            "ready": False,
            "execution": "OFF",
            "direction": side,
            "kfoo": hard,
            "mtf": mtf_result,
            "risk_reward": None,
            "reasons": mtf_result["reasons"],
        }

    rr = _risk_reward(entry, stop, target, side)
    if rr["status"] != "CONFIRMED":
        return {
            "status": rr["status"],
            "ready": False,
            "execution": "OFF",
            "direction": side,
            "kfoo": hard,
            "mtf": mtf_result,
            "risk_reward": rr,
            "reasons": rr["reasons"],
        }

    return {
        "status": "CONFIRMED",
        "ready": True,
        "execution": "OFF",
        "direction": side,
        "kfoo": hard,
        "mtf": mtf_result,
        "risk_reward": rr,
        "reasons": ["KFOO_MTF_RR_ALL_CONFIRMED"],
    }
