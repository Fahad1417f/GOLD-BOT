from playwright_chart_reader import PlaywrightChartReader


class FakePage:
    def __init__(self, result):
        self.result = result

    def evaluate(self, _script):
        return self.result


def test_active_timeframe_is_used_instead_of_menu_order():
    class ActivePage(FakePage):
        pass

    page = ActivePage({'active': ['15m'], 'page': ['1m', '3m', '5m', '15m']})
    symbol, timeframe = PlaywrightChartReader._parse_metadata(
        'XAUUSD 4,411.735',
        'XAUUSD\n1m\n3m\n5m\n15m\n1h\nGold Spot / U.S. Dollar\nOANDA',
        page,
    )
    assert symbol == 'XAU/USD'
    assert timeframe == '15m'


def test_ambiguous_active_timeframes_fail_closed():
    assert PlaywrightChartReader._read_selected_timeframe(
        FakePage({'active': ['1m', '15m'], 'page': []})
    ) is None


def test_page_level_single_timeframe_can_be_used():
    assert PlaywrightChartReader._read_selected_timeframe(
        FakePage({'active': [], 'page': ['15m']})
    ) == '15m'


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
    test_xauusd_title_has_no_fake_timeframe()
    test_timeframe_normalization()
    print('PLAYWRIGHT_ACTIVE_TIMEFRAME_TEST=PASS')
