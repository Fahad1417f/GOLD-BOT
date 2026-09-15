from __future__ import annotations

"""Opportunity Scanner V2: multi-symbol selection layer.

Analysis-only and fail-closed. It consumes already-produced KFOO/market
candidates; it does not scrape TradingView, call an exchange, or place orders.

V2 adds:
- live multi-symbol normalization;
- freshness gating when a timestamp is supplied;
- deterministic ranking with a margin between #1 and #2;
- one selected opportunity at a time;
- duplicate-event suppression for Telegram;
- explicit NO_OPPORTUNITY state when no candidate is safe enough.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
import json
import os
import time

from .opportunity_scanner_v1 import Opportunity, OpportunityScanner


@dataclass(frozen=True)
class Selection:
    status: str
    selected: Opportunity | None
    ranked: tuple[Opportunity, ...]
    selection_reason: str
    event_key: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "selected": self.selected.to_dict() if self.selected else None,
            "ranked": [x.to_dict() for x in self.ranked],
            "selection_reason": self.selection_reason,
            "event_key": self.event_key,
        }


class OpportunityScannerV2:
    def __init__(
        self,
        *,
        min_reward_risk: float = 2.0,
        max_risk_ratio_pct: float = 60.0,
        min_score: float = 70.0,
        min_selection_score: float = 75.0,
        min_margin: float = 3.0,
        max_age_seconds: float = 120.0,
    ) -> None:
        self.scanner = OpportunityScanner(
            min_reward_risk=min_reward_risk,
            max_risk_ratio_pct=max_risk_ratio_pct,
            min_score=min_score,
        )
        self.min_selection_score = float(min_selection_score)
        self.min_margin = float(min_margin)
        self.max_age_seconds = float(max_age_seconds)
        self._last_event_key = ""

    @staticmethod
    def _timestamp_seconds(value: Any) -> float | None:
        if value is None or value == "":
            return None
        if isinstance(value, (int, float)):
            return float(value) / 1000.0 if float(value) > 10_000_000_000 else float(value)
        raw = str(value).strip()
        try:
            return float(raw)
        except ValueError:
            pass
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None

    def _fresh(self, candidate: Mapping[str, Any], now: float) -> bool | None:
        ts = candidate.get("timestamp") or candidate.get("updated_at") or candidate.get("observed_at")
        parsed = self._timestamp_seconds(ts)
        if parsed is None:
            return None
        age = max(0.0, now - parsed)
        return age <= self.max_age_seconds

    def rank_live(self, candidates: Sequence[Mapping[str, Any]], *, now: float | None = None) -> list[Opportunity]:
        now_value = time.time() if now is None else float(now)
        results: list[Opportunity] = []
        for candidate in candidates:
            fresh = self._fresh(candidate, now_value)
            if fresh is False:
                item = dict(candidate)
                item["risk_ratio_status"] = "high"
                item["event_key"] = str(candidate.get("event_key") or "") + "|STALE"
                op = self.scanner.scan(item)
                results.append(
                    Opportunity(
                        symbol=op.symbol,
                        direction=op.direction,
                        status="REJECT",
                        score=op.score,
                        risk_ratio_pct=op.risk_ratio_pct,
                        reward_risk=op.reward_risk,
                        reasons=op.reasons,
                        hard_blocks=tuple(list(op.hard_blocks) + [f"stale market data (>{self.max_age_seconds:.0f}s)"]),
                        data_quality="STALE",
                        event_key=op.event_key,
                    )
                )
            else:
                results.append(self.scanner.scan(candidate))
        return sorted(
            results,
            key=lambda x: (
                {"TRADEABLE": 0, "WATCH": 1, "REJECT": 2}[x.status],
                -x.score,
                x.symbol,
            ),
        )

    def select(self, candidates: Sequence[Mapping[str, Any]], *, now: float | None = None) -> Selection:
        ranked = self.rank_live(candidates, now=now)
        tradeable = [x for x in ranked if x.status == "TRADEABLE" and x.score >= self.min_selection_score]
        if not tradeable:
            return Selection(
                status="NO_OPPORTUNITY",
                selected=None,
                ranked=tuple(ranked),
                selection_reason="No candidate passed the fail-closed tradeability threshold.",
            )

        best = tradeable[0]
        if len(tradeable) > 1:
            margin = best.score - tradeable[1].score
            if margin < self.min_margin:
                return Selection(
                    status="NO_CLEAR_WINNER",
                    selected=None,
                    ranked=tuple(ranked),
                    selection_reason=f"Top candidates are too close (margin {margin:.1f} < {self.min_margin:.1f}).",
                )

        event_key = best.event_key
        if event_key == self._last_event_key:
            return Selection(
                status="DUPLICATE",
                selected=best,
                ranked=tuple(ranked),
                selection_reason="Same opportunity event was already selected.",
                event_key=event_key,
            )

        self._last_event_key = event_key
        return Selection(
            status="SELECTED",
            selected=best,
            ranked=tuple(ranked),
            selection_reason="Best unique candidate passed all hard gates and selection margin.",
            event_key=event_key,
        )


def load_candidates(source: str) -> list[Mapping[str, Any]]:
    payload = json.loads(source)
    candidates = payload.get("candidates", payload) if isinstance(payload, Mapping) else payload
    if not isinstance(candidates, list):
        raise ValueError("candidate payload must contain a list")
    return [x for x in candidates if isinstance(x, Mapping)]


def scan_environment() -> Selection:
    source = os.getenv("GOLDBOT_OPPORTUNITY_CANDIDATES_JSON", "").strip()
    if not source:
        return Selection(
            status="NO_INPUT",
            selected=None,
            ranked=tuple(),
            selection_reason="GOLDBOT_OPPORTUNITY_CANDIDATES_JSON is not set.",
        )
    return OpportunityScannerV2().select(load_candidates(source))


if __name__ == "__main__":
    result = scan_environment()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
