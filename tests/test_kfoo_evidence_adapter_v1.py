from __future__ import annotations

from kfoo_linked_work.kfoo_evidence_adapter_v1 import (
    ABSENT,
    DATA_UNAVAILABLE,
    PRESENT,
    UNREADABLE,
    extract_kfoo_evidence,
)

def _by_key(result):
    return {item["key"]: item for item in result["evidence"]}

def test_explicit_kfoo_labels_are_present():
    result = extract_kfoo_evidence(
        "KFOO: Whales Buying | Continuity Average | Liquidity Table | Ascending Channel"
    )
    items = _by_key(result)
    assert result["status"] == "READ"
    assert items["whales_buying"]["status"] == PRESENT
    assert items["continuity_average"]["status"] == PRESENT
    assert items["liquidity_table"]["status"] == PRESENT
    assert items["ascending_channel"]["status"] == PRESENT

def test_missing_labels_are_unreadable_not_absent():
    result = extract_kfoo_evidence("RSI 64.9 Volume 1.09")
    items = _by_key(result)
    assert all(item["status"] == UNREADABLE for item in items.values())
    assert not any(item["status"] == ABSENT for item in items.values())

def test_empty_text_is_data_unavailable():
    result = extract_kfoo_evidence("")
    assert result["status"] == DATA_UNAVAILABLE
    assert result["evidence"] == []

def test_generic_indicators_do_not_become_kfoo_evidence():
    result = extract_kfoo_evidence(
        "RSI 70, volume rising, bullish trend, net volume positive"
    )
    items = _by_key(result)
    assert items["continuity_average"]["status"] == UNREADABLE
    assert items["liquidity_table"]["status"] == UNREADABLE
    assert items["liquidity_net_positive"]["status"] == UNREADABLE
    assert items["whales_buying"]["status"] == UNREADABLE

def test_explicit_negative_observation_is_absent():
    result = extract_kfoo_evidence("No Whales Buying")
    items = _by_key(result)
    assert items["whales_buying"]["status"] == ABSENT
