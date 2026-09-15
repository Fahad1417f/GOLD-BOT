from __future__ import annotations

"""Fail-closed Opportunity Scanner for V56.

Ranks candidate crypto setups before trading:
- high/extreme Risk Ratio is a rejection filter;
- minimum reward/risk is mandatory when entry/stop/target are supplied;
- 4H/1H gravity, 15M leader and 5M/3M timing improve the score;
- positive liquidity and continuity agreement improve the score;
- missing data never receives a fabricated score.

This module is analysis-only. It never places orders.
"""

from dataclasses import dataclass, asdict
from typing import Any, Mapping, Sequence
import json
import os
from pathlib import Path


def _num(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _direction(v: Any) -> str:
    s = str(v or "").strip().lower()
    if s in {"long", "buy", "bull", "bullish", "شراء"}:
        return "long"
    if s in {"short", "sell", "bear", "bearish", "بيع"}:
        return "short"
    return "neutral"


def _pct(v: Any) -> float | None:
    n = _num(v)
    if n is None:
        return None
    return n * 100.0 if 0 <= n <= 1 else n


def _bool(v: Any) -> bool:
    return bool(v) and str(v).lower() not in {"0", "false", "no", "unknown"}


@dataclass(frozen=True)
class Opportunity:
    symbol: str
    direction: str
    status: str
    score: float
    risk_ratio_pct: float | None
    reward_risk: float | None
    reasons: tuple[str, ...]
    hard_blocks: tuple[str, ...]
    data_quality: str
    event_key: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OpportunityScanner:
    def __init__(
        self,
        min_reward_risk: float = 2.0,
        max_risk_ratio_pct: float = 60.0,
        min_score: float = 70.0,
    ) -> None:
        self.min_reward_risk = float(min_reward_risk)
        self.max_risk_ratio_pct = float(max_risk_ratio_pct)
        self.min_score = float(min_score)

    def scan(self, candidate: Mapping[str, Any]) -> Opportunity:
        symbol = str(candidate.get("symbol") or candidate.get("ticker") or "UNKNOWN").upper()
        direction = _direction(candidate.get("direction") or candidate.get("bias"))
        reasons: list[str] = []
        blocks: list[str] = []

        risk = candidate.get("risk_ratio") if isinstance(candidate.get("risk_ratio"), Mapping) else {}
        risk_pct = _pct(
            risk.get("value_pct") if risk else candidate.get("risk_ratio_pct")
        )
        risk_status = str(
            (risk.get("status") if risk else candidate.get("risk_ratio_status")) or ""
        ).lower()

        if risk_pct is not None:
            if risk_pct >= 80 or risk_status == "extreme":
                blocks.append(f"Risk Ratio extreme ({risk_pct:.1f}%)")
            elif risk_pct >= self.max_risk_ratio_pct or risk_status == "high":
                blocks.append(f"Risk Ratio high ({risk_pct:.1f}%)")
            elif risk_pct < 30:
                reasons.append(f"Risk Ratio favorable ({risk_pct:.1f}%)")
            else:
                reasons.append(f"Risk Ratio acceptable but elevated ({risk_pct:.1f}%)")
        else:
            reasons.append("Risk Ratio unavailable")

        rr = _num(candidate.get("reward_risk") or candidate.get("rr"))
        if rr is None:
            entry = _num(candidate.get("entry"))
            stop = _num(candidate.get("stop") or candidate.get("stop_loss"))
            target = _num(candidate.get("target") or candidate.get("take_profit"))
            if entry is not None and stop is not None and target is not None and entry != stop:
                risk_points = abs(entry - stop)
                reward_points = abs(target - entry)
                rr = reward_points / risk_points if risk_points else None
        if rr is not None:
            if rr < self.min_reward_risk:
                blocks.append(f"Reward/Risk below minimum ({rr:.2f}R)")
            else:
                reasons.append(f"Reward/Risk {rr:.2f}R")
        else:
            blocks.append("Reward/Risk unavailable")

        gravity4 = _direction(candidate.get("gravity_4h"))
        gravity1 = _direction(candidate.get("gravity_1h"))
        leader = _direction(candidate.get("leader_15m"))
        timing5 = _direction(candidate.get("timing_5m"))
        timing3 = _direction(candidate.get("timing_3m"))

        if direction == "neutral":
            blocks.append("Direction unavailable")
        if gravity4 and gravity1 and gravity4 == gravity1 == direction:
            reasons.append("4H + 1H gravity aligned")
        else:
            blocks.append("4H/1H gravity not aligned with candidate")

        if leader == direction:
            reasons.append("15M leader aligned")
        else:
            blocks.append("15M leader not aligned")

        if timing5 == direction and timing3 == direction:
            reasons.append("5M + 3M timing aligned")
        else:
            reasons.append("5M/3M timing not confirmed")

        kfoo_tf = _pct(candidate.get("kfoo_tf_pct"))
        kfoo_ind = _pct(candidate.get("kfoo_ind_pct"))
        if kfoo_tf is not None and kfoo_tf >= 62.5:
            reasons.append(f"KFOO TF {kfoo_tf:.1f}%")
        elif kfoo_tf is not None:
            blocks.append(f"KFOO TF weak ({kfoo_tf:.1f}%)")
        else:
            reasons.append("KFOO TF unavailable")

        if kfoo_ind is not None and kfoo_ind >= 75:
            reasons.append(f"KFOO indicators {kfoo_ind:.1f}%")
        elif kfoo_ind is not None:
            blocks.append(f"KFOO indicators weak ({kfoo_ind:.1f}%)")
        else:
            reasons.append("KFOO indicators unavailable")

        liquidity = candidate.get("liquidity") if isinstance(candidate.get("liquidity"), Mapping) else {}
        net_ratio = _pct(liquidity.get("net_ratio_pct") if liquidity else candidate.get("liquidity_net_ratio_pct"))
        if net_ratio is not None:
            if net_ratio > 10:
                reasons.append(f"positive liquidity {net_ratio:.1f}%")
            elif net_ratio < -10:
                blocks.append(f"negative liquidity {net_ratio:.1f}%")
            else:
                reasons.append(f"balanced liquidity {net_ratio:.1f}%")
        else:
            reasons.append("liquidity unavailable")

        continuity = candidate.get("continuity") if isinstance(candidate.get("continuity"), Mapping) else {}
        continuity_ok = continuity.get("side_ok") if continuity else candidate.get("continuity_side_ok")
        if continuity_ok is True:
            reasons.append("continuity average agrees")
        elif continuity_ok is False:
            blocks.append("continuity average conflicts")
        else:
            reasons.append("continuity unavailable")

        # Score only evidence that is actually present. Hard blocks always win.
        score = 0.0
        if risk_pct is not None and risk_pct < self.max_risk_ratio_pct:
            score += 20 if risk_pct < 30 else 12
        if rr is not None and rr >= self.min_reward_risk:
            score += min(25.0, 10.0 + rr * 5.0)
        if gravity4 and gravity1 and gravity4 == gravity1 == direction:
            score += 20
        if leader == direction:
            score += 10
        if timing5 == direction and timing3 == direction:
            score += 10
        if kfoo_tf is not None and kfoo_tf >= 62.5:
            score += 7
        if kfoo_ind is not None and kfoo_ind >= 75:
            score += 5
        if net_ratio is not None and net_ratio > 10:
            score += 5
        if continuity_ok is True:
            score += 3
        score = min(100.0, round(score, 1))

        if blocks:
            status = "REJECT"
        elif score >= self.min_score:
            status = "TRADEABLE"
        else:
            status = "WATCH"

        quality = "HIGH" if len(reasons) >= 7 and not any("unavailable" in r for r in reasons) else "PARTIAL"
        event_key = str(candidate.get("event_key") or f"{symbol}|{direction}|{round(score,1)}|{rr or 0}")
        return Opportunity(
            symbol=symbol,
            direction=direction,
            status=status,
            score=score,
            risk_ratio_pct=risk_pct,
            reward_risk=rr,
            reasons=tuple(reasons),
            hard_blocks=tuple(blocks),
            data_quality=quality,
            event_key=event_key,
        )

    def rank(self, candidates: Sequence[Mapping[str, Any]]) -> list[Opportunity]:
        results = [self.scan(c) for c in candidates]
        priority = {"TRADEABLE": 0, "WATCH": 1, "REJECT": 2}
        return sorted(results, key=lambda x: (priority[x.status], -x.score, x.symbol))


def scan_json_file(path: str | os.PathLike[str]) -> list[Opportunity]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, Mapping):
        candidates = payload.get("candidates") or []
    else:
        candidates = payload
    if not isinstance(candidates, list):
        raise ValueError("candidate payload must contain a list")
    return OpportunityScanner().rank(candidates)


if __name__ == "__main__":
    source = os.getenv("GOLDBOT_OPPORTUNITY_CANDIDATES_JSON", "").strip()
    if not source:
        raise SystemExit("GOLDBOT_OPPORTUNITY_CANDIDATES_JSON is required")
    payload = json.loads(source)
    candidates = payload.get("candidates", payload) if isinstance(payload, Mapping) else payload
    for item in OpportunityScanner().rank(candidates):
        print(json.dumps(item.to_dict(), ensure_ascii=False))
