from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from tradingview_kfoo_publisher_v56 import Handler, _state, publish


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


def _payload():
    return {
        "analysis": {tf: _frame() for tf in ("4h", "1h", "15m", "5m", "3m")},
        "timing": {"leader_closed": True},
    }


def test_publish_uses_page_evaluate_and_audits(tmp_path: Path):
    class FakePage:
        url = "https://ar.tradingview.com/chart/T2r9HHsB/"

        def is_closed(self):
            return False

        def evaluate(self, script, payload):
            assert "window.__GOLDBOT_KFOO__" in script
            assert set(payload["analysis"]) == {"4h", "1h", "15m", "5m", "3m"}
            return None

    old = dict(_state)
    try:
        _state.update({"page": FakePage(), "last_source": None})
        with patch("tradingview_kfoo_publisher_v56.AUDIT", tmp_path / "audit.log"):
            publish(_payload())
        assert _state["last_source"] == "http_verified_publisher"
        assert "PUBLISHED source=http_verified_publisher" in (tmp_path / "audit.log").read_text()
    finally:
        _state.clear()
        _state.update(old)


def test_server_class_is_single_threaded():
    import tradingview_kfoo_publisher_v56 as mod

    assert mod.HTTPServer.__name__ == "HTTPServer"
    assert not hasattr(mod, "ThreadingHTTPServer")
