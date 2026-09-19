from __future__ import annotations

"""Fail-closed gate for the explicitly documented KFOO hard evidence."""

from typing import Mapping

from .kfoo_evidence_adapter_v1 import PRESENT, UNREADABLE, DATA_UNAVAILABLE

REQUIRED_BUY_EVIDENCE = (
    "continuity_average",
    "liquidity_table",
    "liquidity_net_positive",
    "ascending_channel",
    "whales_buying",
)

REQUIRED_SELL_EVIDENCE = REQUIRED_BUY_EVIDENCE


def evaluate_hard_gate(
    evidence: Mapping[str, str] | None,
    *,
    direction: str,
) -> dict:
    if evidence is None:
        return {
            "status": "DATA_UNAVAILABLE",
            "ready": False,
            "direction": direction,
            "missing": list(REQUIRED_BUY_EVIDENCE),
            "reasons": ["KFOO_EVIDENCE_UNAVAILABLE"],
        }

    side = str(direction or "").strip().lower()
    if side not in {"buy", "sell", "long", "short"}:
        return {
            "status": "REJECTED",
            "ready": False,
            "direction": side,
            "missing": list(REQUIRED_BUY_EVIDENCE),
            "reasons": ["INVALID_DIRECTION"],
        }

    required = REQUIRED_BUY_EVIDENCE if side in {"buy", "long"} else REQUIRED_SELL_EVIDENCE
    missing = [key for key in required if evidence.get(key) != PRESENT]
    unreadable = [key for key in required if evidence.get(key) == UNREADABLE]
    unavailable = [key for key in required if evidence.get(key) == DATA_UNAVAILABLE]

    if unavailable:
        status = "DATA_UNAVAILABLE"
    elif missing:
        status = "WAITING_FOR_EVIDENCE"
    else:
        status = "CONFIRMED"

    reasons = []
    if missing:
        reasons.append("MISSING_OR_UNCONFIRMED:" + ",".join(missing))
    if unreadable:
        reasons.append("UNREADABLE:" + ",".join(unreadable))
    if unavailable:
        reasons.append("DATA_UNAVAILABLE:" + ",".join(unavailable))
    if not reasons:
        reasons.append("ALL_KFOO_HARD_EVIDENCE_PRESENT")

    return {
        "status": status,
        "ready": status == "CONFIRMED",
        "direction": side,
        "missing": missing,
        "reasons": reasons,
    }
