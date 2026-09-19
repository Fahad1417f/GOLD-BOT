from kfoo_linked_work.unified_signal_bridge_v1 import build_mtf, evaluate_unified_signal


def evidence():
    return {
        "continuity_average": "PRESENT",
        "liquidity_table": "PRESENT",
        "liquidity_net_positive": "PRESENT",
        "ascending_channel": "PRESENT",
        "whales_buying": "PRESENT",
    }


def test_build_mtf_does_not_infer_missing_frames():
    frames = build_mtf({"4h": {"active_kfoo": "long"}, "1h": {}})
    assert frames["4h"]["direction"] == "long"
    assert frames["1h"]["direction"] is None
    assert "15m" not in frames


def test_bridge_is_confirmed_only_with_explicit_layers():
    analysis = {
        "4h": {"active_kfoo": "long"},
        "1h": {"active_kfoo": "long"},
        "15m": {"active_kfoo": "long"},
        "3m": {"active_kfoo": "long"},
    }
    result = evaluate_unified_signal(
        analysis,
        evidence=evidence(),
        direction="buy",
        entry=100,
        stop=95,
        target=110,
    )
    assert result["status"] == "CONFIRMED"
    assert result["execution"] == "OFF"


def test_bridge_never_fabricates_rr():
    analysis = {tf: {"active_kfoo": "long"} for tf in ("4h", "1h", "15m", "3m")}
    result = evaluate_unified_signal(
        analysis,
        evidence=evidence(),
        direction="buy",
        entry=100,
        stop=None,
        target=110,
    )
    assert result["status"] == "DATA_UNAVAILABLE"
    assert result["risk_reward"]["rr"] is None
