from __future__ import annotations

from kfoo_linked_work.kfoo_evidence_adapter_v1 import (
    DATA_UNAVAILABLE,
    PRESENT,
    UNREADABLE,
)
from kfoo_linked_work.kfoo_visual_observation_bridge_v1 import normalize_provider_output


def test_missing_provider_output_fails_closed():
    result = normalize_provider_output(None)
    assert result["status"] == DATA_UNAVAILABLE


def test_partial_provider_output_marks_missing_features_unreadable():
    result = normalize_provider_output({
        "whales_buying": {
            "status": PRESENT,
            "matched_text": "Whales Buying",
        }
    })
    assert result["status"] == UNREADABLE
    states = {item["key"]: item["status"] for item in result["evidence"]}
    assert states["whales_buying"] == PRESENT
    assert states["liquidity_table"] == UNREADABLE
    assert states["divergence"] == UNREADABLE


def test_provider_cannot_invent_unknown_feature():
    result = normalize_provider_output({
        "made_up": {"status": PRESENT}
    })
    assert all(item["key"] != "made_up" for item in result["evidence"])
