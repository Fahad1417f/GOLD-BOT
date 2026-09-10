from head_shoulders_v56 import detect


def candles(values):
    return [{'open':v,'high':v+0.2,'low':v-0.2,'close':v} for v in values]


def test_insufficient():
    assert detect(candles([1,2,1])).reason == 'need_at_least_9_candles'


def test_engine_runs_on_candles():
    result = detect(candles([10,12,10,14,10,12,10,9,8,7,6]))
    assert result.reason


if __name__ == '__main__':
    test_insufficient(); test_engine_runs_on_candles(); print('HNS_ENGINE_TEST=PASS')
