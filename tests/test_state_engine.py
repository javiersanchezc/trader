import unittest
import json
from core.types import Candle, OrderBookSnapshot
from core.state_engine import StateEngine

class TestStateEngine(unittest.TestCase):
    def setUp(self):
        self.engine = StateEngine(symbol="BTC/USDT", book_depth_levels=3)
        self.sample_book = OrderBookSnapshot(
            timestamp=1700000000000,
            bids=[(90000.0, 2.0), (89990.0, 3.0), (89980.0, 5.0)],
            asks=[(90010.0, 1.0), (90020.0, 1.5), (90030.0, 2.5)]
        )
        self.sample_candles = [
            Candle(timestamp=1700000000000 + i * 60000,
                   open=90000.0 + i * 10,
                   high=90020.0 + i * 10,
                   low=89980.0 + i * 10,
                   close=90005.0 + i * 10,
                   volume=15.0 + (i % 3))
            for i in range(25)
        ]

    def test_mid_and_spread_calculation(self):
        mid, spread_bps = self.engine.compute_mid_and_spread(self.sample_book)
        self.assertEqual(mid, 90005.0)
        # best_ask = 90010, best_bid = 90000, spread = 10, bps = (10 / 90005) * 10000 = ~1.11 bps
        self.assertAlmostEqual(spread_bps, (10.0 / 90005.0) * 10000.0, places=3)

    def test_orderbook_imbalance(self):
        # bids total size = 2 + 3 + 5 = 10; asks total size = 1 + 1.5 + 2.5 = 5
        # imbalance = (10 - 5) / (10 + 5) = 5 / 15 = 0.3333...
        imbalance = self.engine.compute_orderbook_imbalance(self.sample_book)
        self.assertAlmostEqual(imbalance, 5.0 / 15.0, places=4)

    def test_compact_state_token_size(self):
        state = self.engine.compile_state(
            book=self.sample_book,
            candles=self.sample_candles,
            current_inventory=0.5,
            current_equity=100000.0
        )
        compact_str = state.to_compact_token_state()
        data = json.loads(compact_str)
        self.assertEqual(data["s"], "BTC/USDT")
        self.assertEqual(data["mid"], 90005.0)
        # Token size estimation: character length / 3.5 is well under 400 tokens
        self.assertLess(len(compact_str) / 3.0, 400)

    def test_drawdown_tracking(self):
        self.engine.peak_equity = 100000.0
        dd_1 = self.engine.compute_drawdown(95000.0)
        self.assertAlmostEqual(dd_1, 0.05, places=4)
        # New high watermark
        dd_2 = self.engine.compute_drawdown(110000.0)
        self.assertEqual(dd_2, 0.0)
        self.assertEqual(self.engine.peak_equity, 110000.0)

if __name__ == "__main__":
    unittest.main()
