from __future__ import annotations

from market_context_v56 import enrich_market_context


def test_risk_ratio_high_is_volatility_filter_not_direction():
    frame = {"analysis": {"risk_ratio": {"value_pct": 85, "status": "high", "rising": True}}}
    ctx = enrich_market_context(frame, "short")
    assert ctx.risk.value_pct == 85
    assert ctx.risk.status == "high"
    assert ctx.risk.rising is True
    assert ctx.risk.direction == "neutral"


def test_liquidity_weak_outflow_and_velocity():
    previous = {"analysis": {"liquidity": {"incoming_usd": 200_000, "outgoing_usd": 220_000}}}
    current = {"analysis": {"liquidity": {"incoming_usd": 165_100, "outgoing_usd": 273_200}}}
    ctx = enrich_market_context(current, "short", previous)
    assert round(ctx.liquidity.net_usd, 2) == -108100
    assert round(ctx.liquidity.net_ratio_pct, 2) < 0
    assert ctx.liquidity.velocity_usd is not None
    assert ctx.liquidity.strength in {"inflow", "outflow", "balanced"}


def test_continuity_average_confirms_short_when_price_below_and_slope_falls():
    frame = {"analysis": {
        "price": 0.03186,
        "continuity_average": {"average": 0.03210, "slope": -0.00010},
    }}
    ctx = enrich_market_context(frame, "short")
    assert ctx.continuity.valid
    assert ctx.continuity.side_ok
    assert ctx.continuity.status == "below"


def test_continuity_conflict_blocks_entry_context():
    frame = {"analysis": {
        "price": 0.03220,
        "continuity_average": {"average": 0.03200, "slope": -0.00010},
    }}
    ctx = enrich_market_context(frame, "short")
    assert ctx.continuity.valid
    assert not ctx.continuity.side_ok
