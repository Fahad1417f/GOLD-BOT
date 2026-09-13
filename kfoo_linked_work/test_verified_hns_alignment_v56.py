from __future__ import annotations
import kfoo_linked_work.verified_hns_mtf_v56 as module

class FakeFrame:
    def __init__(self):
        self.available=True; self.verified=True; self.candles=[{"open":1,"high":2,"low":0,"close":1}]*12; self.reason="ok"
class FakeFeed:
    def __init__(self): self.frames={"4h":FakeFrame(),"1h":FakeFrame(),"15m":FakeFrame()}

def test_hns_alignment_requires_all_three_confirmed(monkeypatch):
    class FakePipeline:
        def __init__(self,*args,**kwargs): pass
        def read(self,outputsize=100): return FakeFeed()
    calls=["short","short","long"]
    def fake_detect(candles):
        direction=calls.pop(0)
        return type("R",(),{"detected":True,"confirmed":True,"direction":direction,"pattern":"test","neckline":1.0,"confidence":0.9,"reason":"clean_closed_break"})()
    monkeypatch.setattr(module,"VerifiedMTFCandlePipelineV56",FakePipeline)
    monkeypatch.setattr(module,"detect",fake_detect)
    result=module.VerifiedHNSMTFV56().read()
    assert result.verified is True
    assert result.aligned is False
    assert result.direction == "neutral"
    assert result.reason == "VERIFIED_HNS_MTF_CONFLICT_OR_PARTIAL"
