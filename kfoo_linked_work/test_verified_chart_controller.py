import unittest
from unittest.mock import MagicMock
from kfoo_linked_work.verified_chart_controller import VerifiedChartController

class VerifiedControllerTests(unittest.TestCase):
    def test_rejects_unknown_timeframe(self):
        c=VerifiedChartController()
        with self.assertRaises(ValueError):
            c.set_timeframe("10m")
    def test_scan_order(self):
        c=VerifiedChartController()
        c.set_timeframe=MagicMock(side_effect=lambda tf: type("S",(),{"timeframe":tf})())
        self.assertEqual(list(c.scan_timeframes().keys()),["4h","1h","15m","5m","3m"])
        self.assertEqual(c.set_timeframe.call_count,5)
if __name__=="__main__": unittest.main()
