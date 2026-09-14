from kfoo_linked_work.playwright_chart_reader import PlaywrightChartReader


def test_kfoo_visual_profile_from_visible_text():
    text = """
    🇸🇦 KFOO AI
    متوسط الاستمرارية
    رصد سوينق
    مضاربة سكالب ⚡
    KFOO Whale
    """
    state = PlaywrightChartReader._parse_kfoo_state(text)
    profile = state["visual_monitoring"]
    assert state["present"] is True
    assert profile["continuity_average"] is True
    assert profile["swing_monitoring"] is True
    assert profile["lightning_monitoring"] is True
    assert profile["whale"] is True
    assert profile["candle_window"] == 24


def test_kfoo_marker_signal_is_fail_closed_without_direction():
    text = "KFOO AI\nSTRONG_ENTRY\nDIRECTION_15M=neutral"
    state = PlaywrightChartReader._parse_kfoo_state(text)
    assert state["level"] == "STRONG_ENTRY"
    assert state["trade_ready"] is False
