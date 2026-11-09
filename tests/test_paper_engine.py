import unittest
from core.types import Candle, OrderBookSnapshot
from simulation.paper_engine import PaperTradingHarness

class TestPaperTradingHarness(unittest.TestCase):
    def setUp(self):
        self.harness = PaperTradingHarness(
            symbol="BTC/USDT",
            initial_balance=100_000.0,
            taker_fee_bps=4.0,
            slippage_bps=2.0
        )

    def test_full_pipeline_tick_execution(self):
        # Create baseline candles + Bullish Order Block setup
        candles = []
        for i in range(10):
            candles.append(Candle(timestamp=1000 * i, open=90000, high=90100, low=89900, close=90020, volume=10.0))
        # Bearish OB candidate
        candles.append(Candle(timestamp=10000, open=90050, high=90100, low=89900, close=89920, volume=12.0))
        # Huge expansion candle
        candles.append(Candle(timestamp=11000, open=89950, high=90600, low=89940, close=90550, volume=40.0))
        # Retracement into OB zone
        candles.append(Candle(timestamp=12000, open=90400, high=90420, low=90000, close=90050, volume=15.0))

        # Order book with positive imbalance (bid heavy)
        book = OrderBookSnapshot(
            timestamp=12000,
            bids=[(90050.0, 5.0), (90040.0, 4.0)],
            asks=[(90060.0, 1.0), (90070.0, 1.0)]
        )

        result = self.harness.process_tick(book, candles)
        self.assertTrue(result["gate_passed"])
        self.assertIsNotNone(result["order"])
        self.assertEqual(result["order"]["side"], "buy")
        self.assertGreater(self.harness.position.size, 0)
        self.assertLess(self.harness.balance, 100_000.0) # capital deployed + fee paid
        self.assertEqual(len(self.harness.execution_history), 1)

if __name__ == "__main__":
    unittest.main()
