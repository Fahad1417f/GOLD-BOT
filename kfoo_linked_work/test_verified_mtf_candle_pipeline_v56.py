from verified_mtf_candle_pipeline_v56 import VerifiedMTFCandlePipelineV56, MTFFrame


class DummySource:
    def __init__(self, feeds):
        self.feeds = feeds

    def read(self, timeframe, outputsize=100):
        return self.feeds[timeframe]


def test_required_timeframes():
    assert VerifiedMTFCandlePipelineV56.REQUIRED_TIMEFRAMES == ('4h', '1h', '15m', '5m', '3m')


def test_complete_pipeline():
    from verified_candle_source_v56 import CandleFeed
    pipe = VerifiedMTFCandlePipelineV56(api_key='dummy')
    candles = [{'open': 1, 'high': 2, 'low': 0, 'close': 1} for _ in range(9)]
    pipe.source = DummySource({tf: CandleFeed(True, True, 'test', tf, candles, 'OK') for tf in pipe.REQUIRED_TIMEFRAMES})
    result = pipe.read()
    assert result.verified is True
    assert result.all_required_available is True
    assert all(result.frames[tf].verified for tf in pipe.REQUIRED_TIMEFRAMES)


def test_incomplete_pipeline_fails_closed():
    from verified_candle_source_v56 import CandleFeed
    pipe = VerifiedMTFCandlePipelineV56(api_key='dummy')
    candles = [{'open': 1, 'high': 2, 'low': 0, 'close': 1} for _ in range(9)]
    feeds = {tf: CandleFeed(True, True, 'test', tf, candles, 'OK') for tf in pipe.REQUIRED_TIMEFRAMES}
    feeds['3m'] = CandleFeed(False, False, 'none', '3m', None, 'UNAVAILABLE')
    pipe.source = DummySource(feeds)
    result = pipe.read()
    assert result.verified is False
    assert result.all_required_available is False
    assert '3m:UNAVAILABLE' in result.reason


if __name__ == '__main__':
    test_required_timeframes()
    test_complete_pipeline()
    test_incomplete_pipeline_fails_closed()
    print('VERIFIED_MTF_PIPELINE_TEST=PASS')
