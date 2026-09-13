from kfoo_linked_work.vision_identity_v1 import parse_visible_identity

def test_near_is_detected_but_not_assumed_gold():
    x=parse_visible_identity("NEARUSDT.P 2.359", "NEAR / TetherUS PERPETUAL CONTRACT\nBinance\n15دقيقة")
    assert x.symbol=="NEARUSDT.P"
    assert not x.verified

def test_gold_identity_requires_verified_timeframe():
    x=parse_visible_identity("XAU/USD", "GOLD SPOT / U.S. DOLLAR")
    assert x.symbol=="XAU/USD"
    assert not x.verified
    y=parse_visible_identity("XAU/USD", "GOLD SPOT / U.S. DOLLAR", "15m")
    assert y.verified
    assert y.timeframe=="15m"

def test_timeframe_menu_is_not_selected_by_visible_text():
    x=parse_visible_identity("NEARUSDT.P", "1دقيقة 3دقيقة 5دقيقة 15دقيقة 1ساعة 4ساعة")
    assert x.timeframe is None
