import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kfoo_linked_work.opportunity_scanner_live_bridge import run_once


def candidate(symbol, score_bias=0):
    return {
        "symbol": symbol,
        "direction": "long",
        "risk_ratio_pct": 15 + score_bias,
        "reward_risk": 4,
        "gravity_4h": "long",
        "gravity_1h": "long",
        "leader_15m": "long",
        "timing_5m": "long",
        "timing_3m": "long",
        "kfoo_tf_pct": 80,
        "kfoo_ind_pct": 85,
        "liquidity_net_ratio_pct": 25,
        "continuity_side_ok": True,
        "event_key": symbol + "|LONG|demo",
    }


class LiveBridgeTests(unittest.TestCase):
    def test_selects_one_symbol_from_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "opportunity_candidates.json"
            p.write_text(json.dumps({"candidates": [
                candidate("BTCUSDT.P", 0),
                candidate("SUIUSDT.P", -10),
            ]}), encoding="utf-8")
            with patch("kfoo_linked_work.opportunity_scanner_live_bridge.notify_opportunity",
                       return_value={"ok": True, "sent": True}) as notify:
                out = run_once(p, __import__(
                    "kfoo_linked_work.opportunity_scanner_v2",
                    fromlist=["OpportunityScannerV2"]).OpportunityScannerV2())
            self.assertEqual(out["status"], "SELECTED")
            self.assertIn(out["selected"]["symbol"], {"BTCUSDT.P", "SUIUSDT.P"})
            notify.assert_called_once()

    def test_no_telegram_for_no_opportunity(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "opportunity_candidates.json"
            p.write_text(json.dumps({"candidates": [candidate("RISKUSDT.P", 70)]}), encoding="utf-8")
            with patch("kfoo_linked_work.opportunity_scanner_live_bridge.notify_opportunity") as notify:
                out = run_once(p, __import__(
                    "kfoo_linked_work.opportunity_scanner_v2",
                    fromlist=["OpportunityScannerV2"]).OpportunityScannerV2())
            self.assertEqual(out["status"], "NO_OPPORTUNITY")
            notify.assert_not_called()


if __name__ == "__main__":
    unittest.main()
