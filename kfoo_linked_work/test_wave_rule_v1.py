from __future__ import annotations

"""Deterministic tests for the KFOO wave-breakout hypothesis.

Rule under test:
- bullish: a bullish impulse breaks above the high of the last bearish wave;
- bearish: a bearish impulse breaks below the low of the last bullish wave.

This module intentionally does not infer wave structure from raw candles.
The caller supplies the last opposite wave boundary and the current impulse.
It is a contract test for the decision rule, not a profitability claim.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WaveBreak:
    direction: str
    last_opposite_high: float
    last_opposite_low: float
    current_high: float
    current_low: float
    confirmed_close: float


def detect_wave_break(x: WaveBreak) -> str:
    if x.direction == "bullish" and x.confirmed_close > x.last_opposite_high:
        return "LONG"
    if x.direction == "bearish" and x.confirmed_close < x.last_opposite_low:
        return "SHORT"
    return "WAIT"


def test_bullish_break_confirmed():
    assert detect_wave_break(WaveBreak("bullish", 3300, 3280, 3310, 3290, 3302)) == "LONG"


def test_bearish_break_confirmed():
    assert detect_wave_break(WaveBreak("bearish", 3300, 3280, 3290, 3270, 3278)) == "SHORT"


def test_bullish_touch_is_not_break():
    assert detect_wave_break(WaveBreak("bullish", 3300, 3280, 3305, 3290, 3300)) == "WAIT"


def test_bearish_touch_is_not_break():
    assert detect_wave_break(WaveBreak("bearish", 3300, 3280, 3290, 3275, 3280)) == "WAIT"


def test_wrong_direction_is_blocked():
    assert detect_wave_break(WaveBreak("neutral", 3300, 3280, 3310, 3270, 3310)) == "WAIT"


def test_bullish_close_back_inside_is_not_confirmation():
    assert detect_wave_break(WaveBreak("bullish", 3300, 3280, 3310, 3290, 3299.9)) == "WAIT"


def test_bearish_close_back_inside_is_not_confirmation():
    assert detect_wave_break(WaveBreak("bearish", 3300, 3280, 3290, 3270, 3280.1)) == "WAIT"


if __name__ == "__main__":
    tests = [
        test_bullish_break_confirmed,
        test_bearish_break_confirmed,
        test_bullish_touch_is_not_break,
        test_bearish_touch_is_not_break,
        test_wrong_direction_is_blocked,
        test_bullish_close_back_inside_is_not_confirmation,
        test_bearish_close_back_inside_is_not_confirmation,
    ]
    for t in tests:
        t()
    print("WAVE_RULE_V1=PASS cases=7")
