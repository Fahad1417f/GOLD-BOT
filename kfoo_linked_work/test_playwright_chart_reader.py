from playwright_chart_reader import PlaywrightChartReader


def test_title_parsing():
    symbol, tf = PlaywrightChartReader._parse_title('XAU/USD 15m — TradingView')
    assert symbol == 'XAU/USD'
    assert tf == '15m'


def test_no_browser_is_fail_closed():
    r = PlaywrightChartReader(cdp_url='http://127.0.0.1:1')
    result = r.connect()
    assert result.connected is False
    assert result.reason


if __name__ == '__main__':
    test_title_parsing()
    print('PLAYWRIGHT_READER_TEST=PASS')
