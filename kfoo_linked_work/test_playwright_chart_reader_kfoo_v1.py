from kfoo_linked_work.playwright_chart_reader import PlaywrightChartReader


def test_kfoo_state_parses_strong_entry_direction_and_aggregates():
    text = """
    🇸🇦 KFOO AI
    KFOO_ACTIVE_15M=TRUE
    KFOO_TABLE_15M=BULLISH
    KFOO_TF_AGG_15M=LONG
    KFOO_IND_AGG_15M=LONG
    DIRECTION_15M=long
    SIGNAL_ID=abc123
    STRONG_ENTRY
    """
    state = PlaywrightChartReader._parse_kfoo_state(text)
    assert state["present"] is True
    assert state["active_15m"] == "TRUE"
    assert state["direction_15m"] == "long"
    assert state["table_15m"] == "BULLISH"
    assert state["tf_agg_15m"] == "LONG"
    assert state["ind_agg_15m"] == "LONG"
    assert state["level"] == "STRONG_ENTRY"
    assert state["signal_id"] == "abc123"
    assert state["trade_ready"] is True


def test_kfoo_state_does_not_infer_trade_from_indicator_presence():
    text = "KFOO AI\nKFOO WHALE\n"
    state = PlaywrightChartReader._parse_kfoo_state(text)
    assert state["present"] is True
    assert state["level"] == "NONE"
    assert state["direction_15m"] == "neutral"
    assert state["trade_ready"] is False


def test_kfoo_state_requires_direction_for_trade_ready():
    text = """
    KFOO AI
    KFOO_ACTIVE_15M=TRUE
    STRONG_ENTRY
    DIRECTION_15M=neutral
    """
    state = PlaywrightChartReader._parse_kfoo_state(text)
    assert state["level"] == "STRONG_ENTRY"
    assert state["trade_ready"] is False
