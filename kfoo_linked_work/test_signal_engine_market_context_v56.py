from __future__ import annotations
import unittest
from signal_engine_v56 import promote

def frame(direction="long"):
    return {
        "samples": [{"active_kfoo": direction}] * 3,
        "active_kfoo": direction,
        "analysis": {
            "direction": direction,
            "kfoo_table_detected": True,
            "kfoo_table_direction": {"bias": direction},
            "kfoo_table": {
                "aggregates": {
                    "timeframes": {"bullish_pct": 75.0 if direction == "long" else 25.0, "bearish_pct": 25.0 if direction == "long" else 75.0},
                    "indicators": {"bullish_pct": 80.0 if direction == "long" else 20.0, "bearish_pct": 20.0 if direction == "long" else 80.0},
                },
                "timeframes": {"15m": {"signal": direction}},
            },
        },
    }

class SignalEngineMarketContextTests(unittest.TestCase):
    def test_high_risk_keeps_setup_but_holds_entry(self):
        a = {tf: frame("long") for tf in ("4h", "1h", "15m", "5m", "3m")}
        a["15m"]["analysis"]["risk_ratio"] = {"value_pct": 75, "status": "high", "rising": True}
        a["15m"]["analysis"]["continuity_average"] = {"average": 0.0320, "price": 0.0322, "slope": 0.0001}
        sig = promote(a, timing={"leader_closed": True})
        self.assertTrue(sig.setup_ready)
        self.assertFalse(sig.entry_ready)
        self.assertEqual(sig.level, "STRONG_SETUP")
        self.assertTrue(any("high-risk entry hold" in r for r in sig.reasons))

    def test_extreme_risk_blocks_promotion(self):
        a = {tf: frame("long") for tf in ("4h", "1h", "15m", "5m", "3m")}
        a["15m"]["analysis"]["risk_ratio"] = {"value_pct": 90, "status": "extreme", "rising": True}
        sig = promote(a, timing={"leader_closed": True})
        self.assertEqual(sig.level, "WAIT")
        self.assertFalse(sig.entry_ready)

if __name__ == "__main__":
    unittest.main()
