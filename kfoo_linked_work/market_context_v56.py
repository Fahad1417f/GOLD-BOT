from __future__ import annotations

"""Fast, optional market-context enrichment for V56.

The module is intentionally dependency-free and fail-closed:
- Risk Ratio is treated as a volatility/risk filter, never a direction signal.
- Liquidity is evaluated for strength, net flow and change/velocity when history exists.
- Continuity Average is evaluated for price side, slope and distance.
- Missing enrichment never fabricates a value and never promotes an entry.
"""

from dataclasses import dataclass, asdict
from typing import Any, Mapping, Sequence


def _num(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _side(value: Any) -> str:
    v = str(value or "").strip().lower()
    if v in {"long", "buy", "bull", "bullish", "شراء"}:
        return "long"
    if v in {"short", "sell", "bear", "bearish", "بيع"}:
        return "short"
    return "neutral"


def _first(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


@dataclass(frozen=True)
class RiskContext:
    value_pct: float | None = None
    status: str = "unknown"
    rising: bool = False
    direction: str = "neutral"
    valid: bool = False


@dataclass(frozen=True)
class LiquidityContext:
    incoming_usd: float | None = None
    outgoing_usd: float | None = None
    net_usd: float | None = None
    total_usd: float | None = None
    net_ratio_pct: float | None = None
    velocity_usd: float | None = None
    strength: str = "unknown"
    valid: bool = False


@dataclass(frozen=True)
class ContinuityContext:
    price: float | None = None
    average: float | None = None
    slope: float | None = None
    distance_pct: float | None = None
    side_ok: bool = False
    status: str = "unknown"
    valid: bool = False


@dataclass(frozen=True)
class MarketContext:
    risk: RiskContext
    liquidity: LiquidityContext
    continuity: ContinuityContext
    available: bool = False
    blocking_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _risk(raw: Mapping[str, Any]) -> RiskContext:
    nested = raw.get("risk_ratio") if isinstance(raw.get("risk_ratio"), Mapping) else {}
    value = _num(_first(nested, "value_pct", "percent", "pct", "value"))
    if value is None:
        value = _num(_first(raw, "risk_ratio_pct", "risk_pct", "risk_ratio_value"))
    if value is not None and 0.0 <= value <= 1.0:
        value *= 100.0

    status = str(_first(nested, "status", "state", "level") or
                 _first(raw, "risk_ratio_status", "risk_status") or "unknown").lower()
    direction = _side(_first(nested, "direction", "bias") or
                       _first(raw, "risk_ratio_direction", "risk_direction"))

    rising_value = _first(nested, "rising", "increasing") 
    rising = bool(rising_value) if rising_value is not None else False

    arrow = str(_first(nested, "arrow", "marker", "color") or
                _first(raw, "risk_ratio_arrow", "risk_ratio_color") or "").lower()
    if any(token in arrow for token in ("red", "orange", "high", "extreme", "🔴", "🟥")):
        if status == "unknown":
            status = "high"
    if value is not None and status == "unknown":
        if value >= 80:
            status = "extreme"
        elif value >= 60:
            status = "high"
        elif value >= 30:
            status = "elevated"
        else:
            status = "low"

    return RiskContext(value, status, rising, direction, value is not None or status != "unknown")


def _liquidity(raw: Mapping[str, Any], previous: Mapping[str, Any] | None) -> LiquidityContext:
    nested = raw.get("liquidity") if isinstance(raw.get("liquidity"), Mapping) else {}
    incoming = _num(_first(nested, "incoming_usd", "inflow_usd", "buy_usd", "incoming"))
    outgoing = _num(_first(nested, "outgoing_usd", "outflow_usd", "sell_usd", "outgoing"))
    if incoming is None:
        incoming = _num(_first(raw, "liquidity_incoming_usd", "inflow_usd", "buy_usd"))
    if outgoing is None:
        outgoing = _num(_first(raw, "liquidity_outgoing_usd", "outflow_usd", "sell_usd"))

    net = _num(_first(nested, "net_usd", "net", "net_flow_usd"))
    if net is None and incoming is not None and outgoing is not None:
        net = incoming - outgoing
    total = _num(_first(nested, "total_usd", "total", "gross_usd"))
    if total is None and incoming is not None and outgoing is not None:
        total = incoming + outgoing
    ratio = (net / total * 100.0) if net is not None and total and total > 0 else None

    velocity = _num(_first(nested, "velocity_usd", "change_usd", "delta_usd"))
    if velocity is None:
        velocity = _num(_first(raw, "liquidity_velocity_usd", "liquidity_delta_usd"))
    if velocity is None and previous:
        prev = _liquidity(previous, None)
        if net is not None and prev.net_usd is not None:
            velocity = net - prev.net_usd

    strength = str(_first(nested, "strength", "state", "level") or
                   _first(raw, "liquidity_strength") or "unknown").lower()
    if strength == "unknown" and total is not None:
        # Directional imbalance is useful even when absolute size is unknown.
        strength = "inflow" if (ratio or 0) > 20 else "outflow" if (ratio or 0) < -20 else "balanced"

    valid = incoming is not None or outgoing is not None or net is not None
    return LiquidityContext(incoming, outgoing, net, total, ratio, velocity, strength, valid)


def _continuity(raw: Mapping[str, Any], expected_side: str) -> ContinuityContext:
    nested = raw.get("continuity_average") if isinstance(raw.get("continuity_average"), Mapping) else {}
    price = _num(_first(nested, "price", "current_price") or
                 _first(raw, "price", "current_price", "mark_price"))
    average = _num(_first(nested, "average", "value", "ma") or
                   _first(raw, "continuity_average_value", "continuity_ma", "continuity_avg"))
    slope = _num(_first(nested, "slope", "delta", "change") or
                 _first(raw, "continuity_slope", "continuity_delta"))

    if slope is None:
        avgs = _first(nested, "values", "history") or _first(raw, "continuity_average_history")
        if isinstance(avgs, Sequence) and not isinstance(avgs, (str, bytes)) and len(avgs) >= 2:
            a0, a1 = _num(avgs[-2]), _num(avgs[-1])
            if a0 is not None and a1 is not None:
                slope = a1 - a0
                if average is None:
                    average = a1

    distance = ((price - average) / average * 100.0) if price is not None and average else None
    if expected_side == "long":
        side_ok = price is not None and average is not None and price > average and (slope is None or slope >= 0)
    elif expected_side == "short":
        side_ok = price is not None and average is not None and price < average and (slope is None or slope <= 0)
    else:
        side_ok = False

    status = "above" if distance is not None and distance > 0 else "below" if distance is not None and distance < 0 else "at_average" if distance is not None else "unknown"
    return ContinuityContext(price, average, slope, distance, side_ok, status, price is not None and average is not None)


def enrich_market_context(frame: Mapping[str, Any], expected_side: str = "neutral",
                           previous_frame: Mapping[str, Any] | None = None) -> MarketContext:
    analysis = frame.get("analysis") if isinstance(frame.get("analysis"), Mapping) else frame
    if not isinstance(analysis, Mapping):
        analysis = {}
    expected = _side(expected_side)
    risk = _risk(analysis)
    liquidity = _liquidity(analysis, previous_frame)
    continuity = _continuity(analysis, expected)
    available = risk.valid or liquidity.valid or continuity.valid
    return MarketContext(risk, liquidity, continuity, available, "")


def context_gate(ctx: MarketContext, expected_side: str) -> tuple[bool, list[str]]:
    """Return (pass, reasons). Missing fields are informational, not fabricated."""
    side = _side(expected_side)
    reasons: list[str] = []
    if ctx.risk.valid:
        reasons.append(f"risk_ratio={ctx.risk.status}" + (" rising" if ctx.risk.rising else ""))
        if ctx.risk.status in {"high", "extreme"}:
            reasons.append("high-volatility filter active")
    if ctx.liquidity.valid:
        reasons.append(f"liquidity={ctx.liquidity.strength}")
        if ctx.liquidity.net_ratio_pct is not None:
            reasons.append(f"net_flow={ctx.liquidity.net_ratio_pct:.1f}%")
    if ctx.continuity.valid:
        reasons.append(f"continuity={ctx.continuity.status}")
        if ctx.continuity.side_ok:
            reasons.append("continuity average agrees with direction")

    # These are optional filters until the upstream live feed exposes the fields.
    # Once present, an explicit high-risk or opposite continuity state blocks promotion.
    if ctx.risk.valid and ctx.risk.status in {"high", "extreme"}:
        return False, reasons
    if ctx.continuity.valid and side in {"long", "short"} and not ctx.continuity.side_ok:
        return False, reasons + ["continuity average conflicts with direction"]
    return True, reasons
