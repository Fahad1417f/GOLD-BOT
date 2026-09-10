from verified_candle_source_v56 import CandleFeed
from verified_hns_mtf_v56 import VerifiedHNSMTFV56


class DummySource:
    def __init__(self, feeds):
        self.feeds = feeds

    def read(self, timeframe, outputsize=100):
        return self.feeds[timeframe]


def _feeds():
    candles = [
        {'open': 100 + i, 'high': 101 + i, 'low': 99 + i, 'close': 100.5 + i}
        for i in range(12)
    ]
    return {tf: CandleFeed(True, True, 'test', tf, candles, 'OK') for tf in ('4h', '1h', '15m', '5m', '3m')}


def test_hns_mtf_available_without_fabrication():
    pipe = VerifiedHNSMTFV56(api_key='dummy')
    pipe.pipeline.source = DummySource(_feeds())
    result = pipe.read()
    assert result.verified is True
    assert all(result.frames[tf].verified for tf in ('4h', '1h', '15m'))
    assert result.aligned is False
    assert result.direction == 'neutral'


def test_hns_mtf_fails_closed_when_ohlc_missing():
    feeds = _feeds()
    feeds['1h'] = CandleFeed(False, False, 'none', '1h', None, 'NO_FEED')
    pipe = VerifiedHNSMTFV56(api_key='dummy')
    pipe.pipeline.source = DummySource(feeds)
    result = pipe.read()
    assert result.verified is False
    assert '1h:NO_FEED' in result.reason


if __name__ == '__main__':
    test_hns_mtf_available_without_fabrication()
    test_hns_mtf_fails_closed_when_ohlc_missing()
    print('VERIFIED_HNS_MTF_TEST=PASS')
