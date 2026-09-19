from kfoo_linked_work.kfoo_signal_gate_v1 import evaluate_signal


def evidence():
    return {
        "continuity_average": "PRESENT",
        "liquidity_table": "PRESENT",
        "liquidity_net_positive": "PRESENT",
        "ascending_channel": "PRESENT",
        "whales_buying": "PRESENT",
    }


def mtf(side="buy"):
    return {tf: {"direction": side} for tf in ("4h", "1h", "15m", "3m")}


def test_confirmed_requires_all_layers():
    result = evaluate_signal(evidence(), mtf(), direction="buy", entry=100, stop=95, target=110)
    assert result["status"] == "CONFIRMED"
    assert result["ready"] is True
    assert result["execution"] == "OFF"
    assert result["risk_reward"]["rr"] == 2.0


def test_kfoo_incomplete_stops_before_mtf():
    e = evidence()
    e["whales_buying"] = "UNREADABLE"
    result = evaluate_signal(e, mtf(), direction="buy", entry=100, stop=95, target=110)
    assert result["status"] == "WAITING_FOR_EVIDENCE"
    assert result["mtf"] is None
    assert result["risk_reward"] is None


def test_missing_mtf_is_data_unavailable():
    result = evaluate_signal(evidence(), {"4h": {"direction": "buy"}}, direction="buy", entry=100, stop=95, target=110)
    assert result["status"] == "DATA_UNAVAILABLE"


def test_mtf_conflict_rejects():
    frames = mtf()
    frames["1h"] = {"direction": "sell"}
    result = evaluate_signal(evidence(), frames, direction="buy", entry=100, stop=95, target=110)
    assert result["status"] == "REJECTED"
    assert "MTF_DIRECTION_CONFLICT" in result["reasons"]


def test_invalid_buy_stop_rejects():
    result = evaluate_signal(evidence(), mtf(), direction="buy", entry=100, stop=101, target=110)
    assert result["status"] == "REJECTED"
    assert result["risk_reward"]["rr"] is None


def test_invalid_sell_target_rejects():
    result = evaluate_signal(evidence(), mtf("sell"), direction="sell", entry=100, stop=105, target=101)
    assert result["status"] == "REJECTED"


def test_missing_rr_inputs_never_fabricates():
    result = evaluate_signal(evidence(), mtf(), direction="buy", entry=100, stop=None, target=110)
    assert result["status"] == "DATA_UNAVAILABLE"
    assert result["risk_reward"]["rr"] is None
