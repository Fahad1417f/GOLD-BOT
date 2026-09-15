from __future__ import annotations

import fast_signal_monitor_v56 as fast


def _analysis():
    def f():
        return {
            "samples": [{"active_kfoo": "long"}] * 3,
            "active_kfoo": "long",
            "analysis": {
                "direction": "long",
                "kfoo_table_detected": True,
                "kfoo_table_direction": {"bias": "long"},
                "kfoo_table": {
                    "aggregates": {
                        "timeframes": {"bullish_pct": 75, "bearish_pct": 25},
                        "indicators": {"bullish_pct": 80, "bearish_pct": 20},
                    },
                    "timeframes": {"15m": {"signal": "long"}},
                },
            },
        }
    return {tf: f() for tf in ("4h", "1h", "15m", "5m", "3m")}


def test_fast_lane_posts_execution_off(monkeypatch):
    seen = {}

    def fake_post(url, payload, timeout=2.0):
        seen["url"] = url
        seen["payload"] = payload
        return {"ok": True, "execution": "OFF"}

    monkeypatch.setattr(fast, "_post", fake_post)
    result = fast.run_once(_analysis(), {"leader_closed": True})
    assert result["signal"]["level"] == "STRONG_ENTRY"
    assert result["signal"]["entry_ready"] is True
    assert seen["payload"]["execution"] == "OFF"
