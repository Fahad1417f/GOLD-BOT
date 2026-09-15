from __future__ import annotations

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from opportunity_scanner_v1 import OpportunityScanner


def candidate(**overrides):
    base = {
        "symbol": "TESTUSDT",
        "direction": "long",
        "risk_ratio_pct": 25,
        "entry": 100,
        "stop": 98,
        "target": 106,
        "gravity_4h": "long",
        "gravity_1h": "long",
        "leader_15m": "long",
        "timing_5m": "long",
        "timing_3m": "long",
        "kfoo_tf_pct": 75,
        "kfoo_ind_pct": 80,
        "liquidity": {"net_ratio_pct": 20},
        "continuity": {"side_ok": True},
    }
    base.update(overrides)
    return base


class OpportunityScannerTests(unittest.TestCase):
    def setUp(self):
        self.scanner = OpportunityScanner()

    def test_good_candidate_is_tradeable(self):
        op = self.scanner.scan(candidate())
        self.assertEqual(op.status, "TRADEABLE")
        self.assertGreaterEqual(op.score, 70)
        self.assertEqual(op.reward_risk, 3.0)

    def test_high_risk_is_rejected(self):
        op = self.scanner.scan(candidate(risk_ratio_pct=75))
        self.assertEqual(op.status, "REJECT")
        self.assertTrue(any("Risk Ratio high" in x for x in op.hard_blocks))

    def test_extreme_risk_is_rejected(self):
        op = self.scanner.scan(candidate(risk_ratio_pct=90))
        self.assertEqual(op.status, "REJECT")
        self.assertTrue(any("extreme" in x.lower() for x in op.hard_blocks))

    def test_low_reward_risk_is_rejected(self):
        op = self.scanner.scan(candidate(target=103))
        self.assertEqual(op.status, "REJECT")
        self.assertTrue(any("Reward/Risk below" in x for x in op.hard_blocks))

    def test_rank_prefers_tradeable_over_watch_and_reject(self):
        ranked = self.scanner.rank([
            candidate(symbol="BADUSDT", risk_ratio_pct=80),
            candidate(symbol="WATCHUSDT", timing_3m="short"),
            candidate(symbol="GOODUSDT"),
        ])
        self.assertEqual(ranked[0].symbol, "GOODUSDT")
        self.assertEqual(ranked[0].status, "TRADEABLE")
        self.assertEqual(ranked[-1].status, "REJECT")


if __name__ == "__main__":
    unittest.main()
