from playwright_chart_reader import PlaywrightChartReader


class FakePage:
    def __init__(self, values):
        self.values = values

    def evaluate(self, _script):
        return self.values


def test_active_timeframe_is_used_instead_of_menu_order():
    symbol, timeframe = PlaywrightChartReader._parse_metadata(
        'XAUUSD 4,411.735',
        'XAUUSD\n1m\n3m\n5m\n15m\n1h\nGold Spot / U.S. Dollar\nOANDA',
        FakePage(['15m']),
    )
    assert symbol == 'XAU/USD'
    assert timeframe == '15m'


def test_ambiguous_active_timeframes_fail_closed():
    assert PlaywrightChartReader._read_selected_timeframe(FakePage(['1m', '15m'])) is None


def test_xauusd_title_has_no_fake_timeframe():
    symbol, timeframe = PlaywrightChartReader._parse_title('XAUUSD 4,411.735 ▲ +0.22%')
    assert symbol == 'XAU/USD'
    assert timeframe is None


if __name__ == '__main__':
    test_active_timeframe_is_used_instead_of_menu_order()
    test_ambiguous_active_timeframes_fail_closed()
    test_xauusd_title_has_no_fake_timeframe()
    print('PLAYWRIGHT_ACTIVE_TIMEFRAME_TEST=PASS')
