from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict

GRAVITY_TIMEFRAMES = ("4h", "1h")
LEADER_TIMEFRAME = "15m"
ENTRY_TIMEFRAMES = ("5m", "3m")

@dataclass
class TimeframeSnapshot:
    timeframe: str
    direction: str = "neutral"
    strength: float = 0.0
    kfoo_ai: str = "neutral"
    rsi: str = "neutral"
    whale: str = "neutral"
    table: str = "neutral"

@dataclass
class Decision:
    direction: str
    gravity: str
    leader: str
    entry: str
    score: float
    ready: bool
    reasons: list[str]

class KFOORuleEngine:
    def __init__(self, min_score: float = 0.75):
        self.min_score = float(min_score)

    @staticmethod
    def _side(v: str) -> str:
        v = (v or "neutral").strip().lower()
        if v in {"buy","long","bull","bullish","شراء"}: return "long"
        if v in {"sell","short","bear","bearish","بيع"}: return "short"
        return "neutral"

    def evaluate(self, observations: Dict[str, TimeframeSnapshot]) -> Decision:
        required = list(GRAVITY_TIMEFRAMES)+[LEADER_TIMEFRAME]+list(ENTRY_TIMEFRAMES)
        missing=[tf for tf in required if tf not in observations]
        if missing:
            return Decision("neutral","incomplete","incomplete","incomplete",0.0,False,[f"missing:{','.join(missing)}"])
        g4=self._side(observations["4h"].direction); g1=self._side(observations["1h"].direction)
        leader=self._side(observations["15m"].direction)
        if g4=="neutral" or g1=="neutral":
            return Decision("neutral","unclear",leader,"unclear",0.0,False,["gravity_not_confirmed"])
        if g4!=g1:
            return Decision("neutral","conflict",leader,"blocked",0.0,False,["gravity_conflict:4h_vs_1h"])
        gravity=g4
        comp=[observations["15m"].kfoo_ai,observations["15m"].rsi,observations["15m"].whale,observations["15m"].table]
        aligned=sum(self._side(x)==gravity for x in comp)
        score=aligned/4.0
        if leader!=gravity:
            return Decision("neutral",gravity,leader,"blocked",score,False,["leader_conflict:15m"])
        if aligned<3:
            return Decision("neutral",gravity,leader,"blocked",score,False,[f"components_aligned:{aligned}/4"])
        entry_sides=[self._side(observations[tf].direction) for tf in ENTRY_TIMEFRAMES]
        entry_aligned=sum(x==gravity for x in entry_sides)
        reasons=[f"gravity:{gravity}",f"leader:15m={leader}",f"components:{aligned}/4",f"entry_frames:{entry_aligned}/2"]
        ready=score>=self.min_score and entry_aligned>=2
        return Decision(gravity if ready else "neutral",gravity,leader,"confirmed" if ready else "unconfirmed",score,ready,reasons)

    def as_dict(self, decision: Decision):
        return asdict(decision)