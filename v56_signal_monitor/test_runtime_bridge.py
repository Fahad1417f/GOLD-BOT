import unittest

from github_state_bridge import parse_log, runtime_health
from self_healing import diagnose


class BridgeRuntimeTests(unittest.TestCase):
    def test_runtime_health_reads_live_v56_markers(self):
        log = """CAPTURE_15M=PASS
ANALYSIS_15M=PASS
FRAME_15M_CAPTURE=PASS
FRAME_15M_VERIFY=PASS
TRADINGVIEW_SYMBOL_DETECTED: XAU/USD | source=browser_printwindow+toolbar_ocr_visual
MANUAL_TIMEFRAME_ACTIVE: 15m
KFOO_TABLE_15M=PASS
KFOO_ACTIVE_15M=bullish
"""
        health = runtime_health(log)
        self.assertEqual(health["vision_ocr"], "PASS")
        self.assertEqual(health["symbol_source"], "XAU/USD")
        self.assertEqual(health["manual_timeframe"], "15m")

    def test_parse_log_keeps_runtime_health_connected_to_state(self):
        log = """CAPTURE_15M=PASS
ANALYSIS_15M=PASS
FRAME_15M_CAPTURE=PASS
FRAME_15M_VERIFY=PASS
DIRECTION_15M=short
KFOO_TABLE_15M=PASS
KFOO_ACTIVE_15M=bearish
15m 10:14
3m 01:14
"""
        state = parse_log(log)
        self.assertEqual(state["runtime_health"]["vision_ocr"], "PASS")
        self.assertEqual(state["direction"], "short")
        self.assertEqual(state["candle_clock"]["15m"]["remaining_seconds"], 614)
        self.assertEqual(state["candle_clock"]["3m"]["remaining_seconds"], 74)


class HealingTests(unittest.TestCase):
    def test_historical_known_error_does_not_trigger_forever(self):
        old = "analyze_timeframe() missing 1 required positional argument: 'tf'\n"
        clean = old + ("x" * 30000) + "CAPTURE_15M=PASS"
        self.assertEqual(diagnose(clean)["class"], "NONE")


if __name__ == "__main__":
    unittest.main()
