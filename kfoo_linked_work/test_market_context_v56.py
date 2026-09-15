from __future__ import annotations
import unittest
from market_context_v56 import enrich_market_context

class MarketContextTests(unittest.TestCase):
    def test_risk_ratio_high_is_volatility_filter_not_direction(self):
        ctx = enrich_market_context({"analysis": {"risk_ratio": {"value_pct": 85, "status": "high", "rising": True}}}, "short")
        self.assertEqual(ctx.risk.value_pct, 85)
        self.assertEqual(ctx.risk.status, "high")
        self.assertTrue(ctx.risk.rising)
        self.assertEqual(ctx.risk.direction, "neutral")

    def test_liquidity_weak_outflow_and_velocity(self):
        previous = {"analysis": {"liquidity": {"incoming_usd": 200_000, "outgoing_usd": 220_000}}}
        current = {"analysis": {"liquidity": {"incoming_usd": 165_100, "outgoing_usd": 273_200}}}
        ctx = enrich_market_context(current, "short", previous)
        self.assertEqual(round(ctx.liquidity.net_usd, 2), -108100)
        self.assertLess(ctx.liquidity.net_ratio_pct, 0)
        self.assertIsNotNone(ctx.liquidity.velocity_usd)
        self.assertIn(ctx.liquidity.strength, {"inflow", "outflow", "balanced"})

    def test_continuity_average_confirms_short_when_price_below_and_slope_falls(self):
        frame = {"analysis": {"price": 0.03186, "continuity_average": {"average": 0.03210, "slope": -0.00010}}}
        ctx = enrich_market_context(frame, "short")
        self.assertTrue(ctx.continuity.valid)
        self.assertTrue(ctx.continuity.side_ok)
        self.assertEqual(ctx.continuity.status, "below")

    def test_continuity_conflict_is_detectable(self):
        frame = {"analysis": {"price": 0.03220, "continuity_average": {"average": 0.03200, "slope": -0.00010}}}
        ctx = enrich_market_context(frame, "short")
        self.assertTrue(ctx.continuity.valid)
        self.assertFalse(ctx.continuity.side_ok)

if __name__ == "__main__":
    unittest.main()
