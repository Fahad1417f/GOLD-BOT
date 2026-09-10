from tradingview_kfoo_provider_v56 import validate


def _frame(direction="long"):
    return {
        "active_kfoo": direction,
        "analysis": {
            "direction": direction,
            "kfoo_table_detected": True,
            "kfoo_table_direction": {"bias": direction},
            "kfoo_table": {
                "aggregates": {
                    "timeframes": {"bullish_pct": 75.0, "bearish_pct": 25.0},
                    "indicators": {"bullish_pct": 80.0, "bearish_pct": 20.0},
                }
            },
        },
    }


def test_valid_provider():
    analysis = {tf: _frame() for tf in ("4h", "1h", "15m", "5m", "3m")}
    a, timing = validate({"analysis": analysis, "timing": {"leader_closed": True}})
    assert set(a) == {"4h", "1h", "15m", "5m", "3m"}
    assert timing["leader_closed"] is True


def test_missing_frame_fails_closed():
    analysis = {tf: _frame() for tf in ("4h", "1h", "15m", "5m")}
    try:
        validate({"analysis": analysis})
    except RuntimeError as exc:
        assert "LIVE_KFOO_PROVIDER_INCOMPLETE:3m" in str(exc)
    else:
        raise AssertionError("missing frame must fail closed")


def test_unverified_table_fails_closed():
    analysis = {tf: _frame() for tf in ("4h", "1h", "15m", "5m", "3m")}
    analysis["15m"]["analysis"]["kfoo_table_detected"] = False
    try:
        validate({"analysis": analysis})
    except RuntimeError as exc:
        assert "15m:table_not_verified" in str(exc)
    else:
        raise AssertionError("unverified KFOO must fail closed")
