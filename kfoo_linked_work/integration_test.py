from __future__ import annotations
from kfoo_rule_engine import KFOORuleEngine,TimeframeSnapshot
from chart_controller import TIMEFRAME_KEYS

def make(direction,**kwargs): return TimeframeSnapshot(timeframe=kwargs.pop("timeframe","15m"),direction=direction,**kwargs)
def test_timeframe_roles():
    assert ("4h","1h")==("4h","1h"); assert "15m" not in ("4h","1h"); assert set(("5m","3m"))=={"5m","3m"}; assert "2m" not in TIMEFRAME_KEYS
def test_gravity_conflict_blocks():
    o={"4h":make("long"),"1h":make("short"),"15m":make("long",kfoo_ai="buy",rsi="buy",whale="buy",table="buy"),"5m":make("long"),"3m":make("long")}
    d=KFOORuleEngine().evaluate(o); assert not d.ready and d.gravity=="conflict"
def test_full_long_path():
    o={"4h":make("long"),"1h":make("long"),"15m":make("long",kfoo_ai="buy",rsi="buy",whale="buy",table="buy"),"5m":make("long"),"3m":make("long")}
    d=KFOORuleEngine().evaluate(o); assert d.ready and d.direction=="long"
def test_missing_frames_fail_closed():
    d=KFOORuleEngine().evaluate({"4h":make("long"),"1h":make("long"),"15m":make("long")}); assert not d.ready
def test_controller_timeframe_map():
    for tf in ("4h","1h","15m","5m","3m"): assert tf in TIMEFRAME_KEYS
    assert "2m" not in TIMEFRAME_KEYS
if __name__=="__main__":
    tests=[test_timeframe_roles,test_gravity_conflict_blocks,test_full_long_path,test_missing_frames_fail_closed,test_controller_timeframe_map]
    for t in tests:t()
    print("PASS_5")