from __future__ import annotations

from kfoo_linked_work.kfoo_evidence_adapter_v1 import PRESENT, UNREADABLE
from kfoo_linked_work.kfoo_hard_gate_v1 import evaluate_hard_gate


def complete():
    return {
        "continuity_average": PRESENT,
        "liquidity_table": PRESENT,
        "liquidity_net_positive": PRESENT,
        "ascending_channel": PRESENT,
        "whales_buying": PRESENT,
    }


def test_complete_buy_evidence_confirms():
    result = evaluate_hard_gate(complete(), direction="buy")
    assert result["status"] == "CONFIRMED"
    assert result["ready"] is True


def test_missing_evidence_waits():
    evidence = complete()
    evidence["whales_buying"] = UNREADABLE
    result = evaluate_hard_gate(evidence, direction="buy")
    assert result["status"] == "WAITING_FOR_EVIDENCE"
    assert result["ready"] is False


def test_none_fails_closed():
    result = evaluate_hard_gate(None, direction="buy")
    assert result["status"] == "DATA_UNAVAILABLE"
    assert result["ready"] is False


def test_invalid_direction_rejected():
    result = evaluate_hard_gate(complete(), direction="maybe")
    assert result["status"] == "REJECTED"
    assert result["ready"] is False
