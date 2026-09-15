from __future__ import annotations

import unittest
import time

from kfoo_linked_work.opportunity_scanner_v2 import OpportunityScannerV2


def candidate(symbol="GOODUSDT", score_boost=0, **overrides):
    base = {
        "symbol": symbol,
        "direction": "long",
        "risk_ratio_pct": 20,
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
    if score_boost:
        base["reward_risk"] = 3 + score_boost
        base.pop("target")
    base.update(overrides)
    return base


class OpportunityScannerV2Tests(unittest.TestCase):
    def setUp(self):
        self.scanner = OpportunityScannerV2()

    def test_selects_best_unique_tradeable(self):
        result = self.scanner.select([
            candidate("AUSDT"),
            candidate("BUSDT", score_boost=1),
            candidate("BADUSDT", risk_ratio_pct=80),
        ])
        self.assertEqual(result.status, "SELECTED")
        self.assertEqual(result.selected.symbol, "BUSDT")

    def test_no_clear_winner_when_scores_are_close(self):
        scanner = OpportunityScannerV2(min_margin=3)
        result = scanner.select([
            candidate("AUSDT"),
            candidate("BUSDT"),
        ])
        self.assertEqual(result.status, "NO_CLEAR_WINNER")

    def test_stale_candidate_is_rejected(self):
        scanner = OpportunityScannerV2(max_age_seconds=120)
        result = scanner.select([
            candidate("STALEUSDT", timestamp=time.time() - 300),
        ])
        self.assertEqual(result.status, "NO_OPPORTUNITY")
        self.assertEqual(result.ranked[0].data_quality, "STALE")

    def test_missing_timestamp_does_not_fabricate_freshness(self):
        result = self.scanner.select([candidate("NOTIMEUSDT")])
        self.assertEqual(result.status, "SELECTED")

    def test_duplicate_event_is_suppressed(self):
        scanner = OpportunityScannerV2()
        first = scanner.select([candidate("AUSDT", event_key="A|LONG|1")])
        second = scanner.select([candidate("AUSDT", event_key="A|LONG|1")])
        self.assertEqual(first.status, "SELECTED")
        self.assertEqual(second.status, "DUPLICATE")

    def test_execution_remains_analysis_only(self):
        result = self.scanner.select([candidate("AUSDT")])
        self.assertNotIn("order", result.to_dict())
        self.assertNotIn("execute", result.to_dict())


if __name__ == "__main__":
    unittest.main()
