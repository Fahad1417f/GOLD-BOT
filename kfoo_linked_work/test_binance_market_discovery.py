import unittest
from unittest.mock import patch
from kfoo_linked_work.binance_market_discovery import build_candidates

class BinanceDiscoveryTests(unittest.TestCase):
    @patch("kfoo_linked_work.binance_market_discovery.ticker24")
    @patch("kfoo_linked_work.binance_market_discovery.perpetual_usdt_symbols")
    def test_builds_perpetual_candidates(self, symbols, tickers):
        symbols.return_value=["SUIUSDT","BTCUSDT"]
        tickers.return_value={
            "SUIUSDT":{"symbol":"SUIUSDT","priceChangePercent":"4.2","quoteVolume":"1000","lastPrice":"3.1","closeTime":1770000000000},
            "BTCUSDT":{"symbol":"BTCUSDT","priceChangePercent":"-1.0","quoteVolume":"5000","lastPrice":"90000","closeTime":1770000000000},
        }
        rows=build_candidates(2)
        self.assertEqual({x["symbol"] for x in rows},{"SUIUSDT.P","BTCUSDT.P"})
        self.assertTrue(all(x["kfoo_enrichment_required"] for x in rows))
        self.assertEqual(next(x for x in rows if x["symbol"]=="SUIUSDT.P")["direction"],"long")

if __name__=="__main__":
    unittest.main()
