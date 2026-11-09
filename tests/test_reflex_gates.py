import unittest
from core.types import MarketState, Regime, Direction
from core.reflex import ReflexEngine

class TestReflexEngine(unittest.TestCase):
    def setUp(self):
        self.reflex = ReflexEngine()

    def test_reflex_bullish_order_block(self):
        state = MarketState(
            symbol="BTC/USDT",
            causal_timestamp=1700000000000,
            mid_price=90000.0,
            spread_bps=2.0,
            orderbook_imbalance=0.25, # positive imbalance
            realized_volatility=0.40,
            current_inventory=0.0,
            current_drawdown=0.01,
            detected_order_block={"side": "bullish", "high": 90100.0, "low": 89900.0}
        )
        decision = self.reflex.evaluate(state)
        self.assertEqual(decision.direction, Direction.LONG)
        self.assertEqual(decision.setup_quality, 3)
        self.assertGreater(decision.confidence, 0.80)

    def test_reflex_liquidity_sweep_rejection(self):
        state = MarketState(
            symbol="BTC/USDT",
            causal_timestamp=1700000000000,
            mid_price=90000.0,
            spread_bps=2.5,
            orderbook_imbalance=-0.20,
            realized_volatility=0.45,
            current_inventory=0.0,
            current_drawdown=0.01,
            liquidity_sweep_detected=True,
            breakout_type="fake_breakout"
        )
        decision = self.reflex.evaluate(state)
        self.assertEqual(decision.direction, Direction.SHORT)
        self.assertGreaterEqual(decision.setup_quality, 2)
        self.assertGreater(decision.confidence, 0.80)

if __name__ == "__main__":
    unittest.main()
