from playwright_chart_reader import PlaywrightChartReader


class FakePage:
    def __init__(self, result):
        self.result = result

    def evaluate(self, _script):
        return self.result


def test_active_timeframe_is_used_instead_of_menu_order():
    page = FakePage({'active': ['15m'], 'metadata': ['1m', '3m', '5m', '15m'], 'toolbar': []})
    symbol, timeframe = PlaywrightChartReader._parse_metadata(
        'XAUUSD 4,411.735',
        'XAUUSD\n1m\n3m\n5m\n15m\n1h\nGold Spot / U.S. Dollar\nOANDA',
        page,
    )
    assert symbol == 'XAU/USD'
    assert timeframe == '15m'


def test_ambiguous_active_timeframes_fail_closed():
    assert PlaywrightChartReader._read_selected_timeframe(
        FakePage({'active': ['1m', '15m'], 'metadata': [], 'toolbar': []})
    ) is None


def test_page_level_single_timeframe_can_be_used():
    assert PlaywrightChartReader._read_selected_timeframe(
        FakePage({'active': [], 'metadata': ['15m'], 'toolbar': []})
    ) == '15m'


def test_toolbar_single_timeframe_candidate_can_be_used():
    assert PlaywrightChartReader._read_selected_timeframe(
        FakePage({
            'active': [],
            'metadata': [],
            'toolbar': [
                {'tf': '15m', 'text': '15', 'aria': '', 'title': '', 'rect': {'x': 250, 'y': 75, 'w': 30, 'h': 24}},
            ],
        })
    ) == '15m'


def test_toolbar_multiple_timeframes_fail_closed():
    assert PlaywrightChartReader._read_selected_timeframe(
        FakePage({
            'active': [],
            'metadata': [],
            'toolbar': [
                {'tf': '1m', 'text': '1', 'aria': '', 'title': '', 'rect': {'x': 200, 'y': 75, 'w': 24, 'h': 24}},
                {'tf': '15m', 'text': '15', 'aria': '', 'title': '', 'rect': {'x': 250, 'y': 75, 'w': 30, 'h': 24}},
            ],
        })
    ) is None


def test_xauusd_title_has_no_fake_timeframe():
    symbol, timeframe = PlaywrightChartReader._parse_title('XAUUSD 4,411.735 ▲ +0.22%')
    assert symbol == 'XAU/USD'
    assert timeframe is None


def test_timeframe_normalization():
    assert PlaywrightChartReader._normalize_timeframe('15 min') == '15m'
    assert PlaywrightChartReader._normalize_timeframe('1 hour') == '1h'
    assert PlaywrightChartReader._normalize_timeframe('15m') == '15m'
    assert PlaywrightChartReader._normalize_timeframe('anything') is None


if __name__ == '__main__':
    test_active_timeframe_is_used_instead_of_menu_order()
    test_ambiguous_active_timeframes_fail_closed()
    test_page_level_single_timeframe_can_be_used()
    test_toolbar_single_timeframe_candidate_can_be_used()
    test_toolbar_multiple_timeframes_fail_closed()
    test_xauusd_title_has_no_fake_timeframe()
    test_timeframe_normalization()
    print('PLAYWRIGHT_ACTIVE_TIMEFRAME_TEST=PASS')
