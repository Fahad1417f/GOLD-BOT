from __future__ import annotations

from kfoo_linked_work.kfoo_evidence_adapter_v1 import (
    ABSENT,
    DATA_UNAVAILABLE,
    PRESENT,
    UNREADABLE,
)
from kfoo_linked_work.kfoo_visual_verifier_v1 import verify_region_observations


def test_none_is_data_unavailable():
    result = verify_region_observations(None)
    assert result["status"] == DATA_UNAVAILABLE


def test_present_observation_stays_present():
    result = verify_region_observations({
        "whales_buying": {
            "status": PRESENT,
            "matched_text": "Whales Buying",
            "confidence": 0.98,
        }
    })
    assert result["status"] == "READ"
    assert result["evidence"][0]["status"] == PRESENT


def test_absent_observation_stays_absent():
    result = verify_region_observations({
        "whales_buying": {
            "status": ABSENT,
            "reason": "EXPLICIT_NEGATIVE_OBSERVATION",
        }
    })
    assert result["evidence"][0]["status"] == ABSENT


def test_missing_visual_observation_never_becomes_present():
    result = verify_region_observations({
        "whales_buying": {
            "status": UNREADABLE,
            "confidence": 0.99,
        }
    })
    assert result["status"] == UNREADABLE
    assert result["evidence"][0]["status"] == UNREADABLE


def test_invalid_status_fails_closed():
    result = verify_region_observations({
        "liquidity_table": {
            "status": "MAYBE",
        }
    })
    assert result["evidence"][0]["status"] == UNREADABLE
