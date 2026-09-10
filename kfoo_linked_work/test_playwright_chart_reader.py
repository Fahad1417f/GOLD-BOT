from playwright_chart_reader import PlaywrightChartReader


def test_title_parsing():
    symbol, tf = PlaywrightChartReader._parse_title('XAU/USD 15m — TradingView')
    assert symbol == 'XAU/USD'
    assert tf == '15m'


def test_xauusd_title_parsing():
    symbol, tf = PlaywrightChartReader._parse_title('XAUUSD 4,411.735 ▲ +0.22%')
    assert symbol == 'XAU/USD'
    assert tf is None


def test_visible_gold_spot_metadata():
    symbol, tf = PlaywrightChartReader._parse_metadata(
        'XAUUSD 4,411.735',
        'XAUUSD\n1m\n3m\n5m\n15m\nGold Spot / U.S. Dollar\nOANDA',
        None,
    )
    assert symbol == 'XAU/USD'
    assert tf is None


def test_no_browser_is_fail_closed():
    r = PlaywrightChartReader(cdp_url='http://127.0.0.1:1')
    result = r.connect()
    assert result.connected is False
    assert result.reason


if __name__ == '__main__':
    test_title_parsing()
    test_xauusd_title_parsing()
    test_visible_gold_spot_metadata()
    print('PLAYWRIGHT_READER_TEST=PASS')
