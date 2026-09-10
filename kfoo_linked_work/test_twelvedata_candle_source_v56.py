import os

from twelvedata_candle_source_v56 import TwelveDataCandleSourceV56


def test_missing_key_fails_closed():
    previous = os.environ.pop('TWELVEDATA_API_KEY', None)
    try:
        result = TwelveDataCandleSourceV56(api_key='').read('15m')
        assert result.available is False
        assert result.verified is False
        assert result.reason == 'TWELVEDATA_API_KEY_NOT_SET'
    finally:
        if previous is not None:
            os.environ['TWELVEDATA_API_KEY'] = previous


def test_timeframe_mapping():
    assert TwelveDataCandleSourceV56.INTERVALS['15m'] == '15min'
    assert TwelveDataCandleSourceV56.INTERVALS['1h'] == '1h'
    assert TwelveDataCandleSourceV56.INTERVALS['4h'] == '4h'


def test_invalid_timeframe_fails_closed():
    result = TwelveDataCandleSourceV56(api_key='dummy').read('bad')
    assert result.available is False
    assert result.reason == 'UNSUPPORTED_TIMEFRAME'


if __name__ == '__main__':
    test_missing_key_fails_closed()
    test_timeframe_mapping()
    test_invalid_timeframe_fails_closed()
    print('TWELVEDATA_CANDLE_SOURCE_TEST=PASS')
