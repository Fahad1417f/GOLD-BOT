from __future__ import annotations
import unittest
from unittest.mock import patch
import fast_signal_monitor_v56 as fast

def analysis():
    def frame():
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
    return {tf: frame() for tf in ("4h", "1h", "15m", "5m", "3m")}

class FastSignalLaneTests(unittest.TestCase):
    def test_fast_lane_posts_execution_off(self):
        seen = {}
        def fake_post(url, payload, timeout=2.0):
            seen["payload"] = payload
            return {"ok": True, "execution": "OFF"}
        with patch.object(fast, "_post", side_effect=fake_post):
            result = fast.run_once(analysis(), {"leader_closed": True})
        self.assertEqual(result["signal"]["level"], "STRONG_ENTRY")
        self.assertTrue(result["signal"]["entry_ready"])
        self.assertEqual(seen["payload"]["execution"], "OFF")

if __name__ == "__main__":
    unittest.main()
