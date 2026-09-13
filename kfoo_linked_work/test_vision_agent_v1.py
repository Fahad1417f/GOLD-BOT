from kfoo_linked_work.vision_agent_v1 import VisionAgentV1

def test_empty_input_is_safe():
    e=VisionAgentV1().analyze_ohlc([])
    assert e.confidence == 0
    assert "NO_CANDLES" in e.warnings

def test_reconstructs_normalized_ohlc_without_execution():
    rows=[
        {"open":10,"high":12,"low":9,"close":11},
        {"open":11,"high":13,"low":10,"close":12},
        {"open":12,"high":14,"low":11,"close":13},
    ]
    e=VisionAgentV1().analyze_ohlc(rows, "15m")
    assert len(e.candles) == 3
    assert e.trend == "up"
    assert e.confidence > 0

def test_module_has_no_execution_dependency():
    import kfoo_linked_work.vision_agent_v1 as m
    assert not hasattr(m, "BinanceClient")
    assert not hasattr(m, "CryptoAgent")
