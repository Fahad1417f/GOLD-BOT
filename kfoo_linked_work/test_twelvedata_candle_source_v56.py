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
    assert '3m' not in TwelveDataCandleSourceV56.INTERVALS
    assert TwelveDataCandleSourceV56.INTERVALS['15m'] == '15min'
    assert TwelveDataCandleSourceV56.INTERVALS['1h'] == '1h'
    assert TwelveDataCandleSourceV56.INTERVALS['4h'] == '4h'


def test_3m_aggregation():
    candles = []
    for i in range(12):
        candles.append({
            'open': 100 + i,
            'high': 101 + i,
            'low': 99 + i,
            'close': 100.5 + i,
            'time': f'2026-09-10T10:{i:02d}:00+00:00',
        })
    result = TwelveDataCandleSourceV56._aggregate_3m(candles, 4)
    assert result is not None
    assert len(result) == 4
    assert result[0]['open'] == 100
    assert result[0]['high'] == 103
    assert result[0]['low'] == 99
    assert result[0]['close'] == 102.5
    assert result[-1]['open'] == 109
    assert result[-1]['close'] == 111.5


def test_3m_aggregation_rejects_incomplete_bucket():
    candles = [
        {'open': 100 + i, 'high': 101 + i, 'low': 99 + i, 'close': 100.5 + i,
         'time': f'2026-09-10T10:{i:02d}:00+00:00'}
        for i in (0, 1, 3, 4, 5, 6, 7, 8, 9)
    ]
    result = TwelveDataCandleSourceV56._aggregate_3m(candles, 3)
    assert result is not None
    assert all(c['time'] != '2026-09-10T10:00:00+00:00' for c in result)


def test_invalid_timeframe_fails_closed():
    result = TwelveDataCandleSourceV56(api_key='dummy').read('bad')
    assert result.available is False
    assert result.reason == 'UNSUPPORTED_TIMEFRAME'


if __name__ == '__main__':
    test_missing_key_fails_closed()
    test_timeframe_mapping()
    test_3m_aggregation()
    test_3m_aggregation_rejects_incomplete_bucket()
    test_invalid_timeframe_fails_closed()
    print('TWELVEDATA_CANDLE_SOURCE_TEST=PASS')
