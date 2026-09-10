import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from candle_clock import parse_kfoo_candle_clock, parse_legacy_leader_remaining

class CandleClockTests(unittest.TestCase):
    def test_15m_table_clock(self):
        c=parse_kfoo_candle_clock("KFOO table: 15m 10:14", "15m")
        self.assertIsNotNone(c)
        self.assertEqual(c.remaining_seconds, 614)
        self.assertEqual(c.source, "kfoo_table")

    def test_3m_table_clock(self):
        c=parse_kfoo_candle_clock("15m 10:14 | 3m 01:14", "3m")
        self.assertIsNotNone(c)
        self.assertEqual(c.remaining_seconds, 74)

    def test_clock_can_be_zero(self):
        c=parse_kfoo_candle_clock("3M_REMAINING=0", "3m")
        self.assertIsNotNone(c)
        self.assertTrue(c.closed)

    def test_4h_and_1h_are_not_changed(self):
        self.assertIsNone(parse_kfoo_candle_clock("4h 01:40:14 1h 40:14", "4h"))
        self.assertIsNone(parse_kfoo_candle_clock("4h 01:40:14 1h 40:14", "1h"))

    def test_legacy_fallback(self):
        c=parse_legacy_leader_remaining("LEADER_15M_REMAINING=299")
        self.assertEqual(c.remaining_seconds, 299)
        self.assertEqual(c.source, "legacy_leader_log")

if __name__=="__main__":
    unittest.main()
