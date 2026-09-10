from verified_candle_source_v56 import VerifiedCandleSourceV56, provider_contract


class FakePage:
    def __init__(self, value):
        self.value = value

    def evaluate(self, _script, _name):
        return self.value


def test_provider_contract_is_strict():
    c = provider_contract()
    assert c['provider'] == '__GOLDBOT_CANDLES__'
    assert c['minimum_candles'] == 9
    assert c['screenshot_inference'] is False
    assert c['chart_dom_inference'] is False
    assert c['execution'] is False


def test_missing_provider_fails_closed():
    result = VerifiedCandleSourceV56(FakePage(None)).read('15m')
    assert result.available is False
    assert result.verified is False


def test_valid_provider_is_accepted():
    candles = [
        {'open': 100 + i, 'high': 101 + i, 'low': 99 + i, 'close': 100.5 + i, 'time': i}
        for i in range(9)
    ]
    result = VerifiedCandleSourceV56(FakePage(candles)).read('15m')
    assert result.available is True
    assert result.verified is True
    assert result.timeframe == '15m'
    assert len(result.candles) == 9


def test_invalid_provider_row_fails_closed():
    candles = [{'open': 1, 'high': 2, 'low': 0} for _ in range(9)]
    result = VerifiedCandleSourceV56(FakePage(candles)).read('15m')
    assert result.available is False
    assert result.verified is False


if __name__ == '__main__':
    test_provider_contract_is_strict()
    test_missing_provider_fails_closed()
    test_valid_provider_is_accepted()
    test_invalid_provider_row_fails_closed()
    print('VERIFIED_CANDLE_SOURCE_TEST=PASS')
