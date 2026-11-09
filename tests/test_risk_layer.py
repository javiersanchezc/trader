import unittest
from core.types import (
    DecisionSchema,
    MarketState,
    Position,
    Regime,
    Direction,
    RiskState,
    ToxicFlow,
    RiskParameters
)
from core.risk_layer import RiskEngine

class TestRiskLayer(unittest.TestCase):
    def setUp(self):
        self.params = RiskParameters(
            max_drawdown_limit=0.15,
            max_daily_loss=0.03,
            quarter_kelly_fraction=0.25,
            min_confidence_threshold=0.80,
            min_setup_quality=2
        )
        self.risk_engine = RiskEngine(params=self.params, starting_equity=100_000.0)
        self.base_state = MarketState(
            symbol="BTC/USDT",
            causal_timestamp=1700000000000,
            mid_price=90000.0,
            spread_bps=2.0,
            orderbook_imbalance=0.30,
            realized_volatility=0.45,
            current_inventory=0.0,
            current_drawdown=0.02
        )

    def test_rejection_low_confidence(self):
        decision = DecisionSchema(
            regime=Regime.TRENDING,
            direction=Direction.LONG,
            confidence=0.75,  # <= 0.80
            setup_quality=3,
            risk_state=RiskState.SAFE,
            toxic_flow=ToxicFlow.BENIGN,
            rationale="Test low confidence"
        )
        passed, reason = self.risk_engine.evaluate_execution_gates(decision, self.base_state)
        self.assertFalse(passed)
        self.assertIn("Confianza 0.75 <= 0.8", reason)

    def test_rejection_low_setup_quality(self):
        decision = DecisionSchema(
            regime=Regime.TRENDING,
            direction=Direction.LONG,
            confidence=0.85,
            setup_quality=1,  # < 2
            risk_state=RiskState.SAFE,
            toxic_flow=ToxicFlow.BENIGN,
            rationale="Test low quality"
        )
        passed, reason = self.risk_engine.evaluate_execution_gates(decision, self.base_state)
        self.assertFalse(passed)
        self.assertIn("Calidad de configuración 1 por debajo del umbral", reason)

    def test_rejection_risk_state_not_safe(self):
        decision = DecisionSchema(
            regime=Regime.TRENDING,
            direction=Direction.LONG,
            confidence=0.88,
            setup_quality=3,
            risk_state=RiskState.NEAR_LIMIT,  # not safe
            toxic_flow=ToxicFlow.BENIGN,
            rationale="Test risk state"
        )
        passed, reason = self.risk_engine.evaluate_execution_gates(decision, self.base_state)
        self.assertFalse(passed)
        self.assertIn("no es 'seguro'", reason)

    def test_rejection_crisis_escalation_to_brain(self):
        decision = DecisionSchema(
            regime=Regime.CRISIS,
            direction=Direction.LONG,
            confidence=0.90,
            setup_quality=3,
            risk_state=RiskState.SAFE,
            toxic_flow=ToxicFlow.TOXIC_CLUSTER,
            rationale="Crisis regime test"
        )
        passed, reason = self.risk_engine.evaluate_execution_gates(decision, self.base_state)
        self.assertFalse(passed)
        self.assertTrue(self.risk_engine.brain_escalation_required)
        self.assertIn("Escalado al Cerebro", reason)

    def test_max_drawdown_kill_switch(self):
        crisis_state = MarketState(
            symbol="BTC/USDT",
            causal_timestamp=1700000000000,
            mid_price=90000.0,
            spread_bps=2.0,
            orderbook_imbalance=0.30,
            realized_volatility=0.45,
            current_inventory=0.0,
            current_drawdown=0.16  # > 15%
        )
        decision = DecisionSchema(
            regime=Regime.TRENDING,
            direction=Direction.LONG,
            confidence=0.90,
            setup_quality=3,
            risk_state=RiskState.SAFE,
            toxic_flow=ToxicFlow.BENIGN,
            rationale="Valid decision during breach"
        )
        passed, reason = self.risk_engine.evaluate_execution_gates(decision, crisis_state)
        self.assertFalse(passed)
        self.assertTrue(self.risk_engine.kill_switch_triggered)
        self.assertIn("Ruptura de drawdown máximo", reason)

    def test_quarter_kelly_sizing(self):
        size = self.risk_engine.compute_quarter_kelly_size(confidence=0.85, mid_price=90000.0, reward_risk_ratio=1.8)
        self.assertGreater(size, 0.0)
        self.assertAlmostEqual(size, 15000.0 / 90000.0, places=3)

    def test_order_creation_approved(self):
        decision = DecisionSchema(
            regime=Regime.TRENDING,
            direction=Direction.LONG,
            confidence=0.86,
            setup_quality=3,
            risk_state=RiskState.SAFE,
            toxic_flow=ToxicFlow.BENIGN,
            rationale="Clean setup"
        )
        pos = Position(symbol="BTC/USDT")
        order = self.risk_engine.size_and_create_order(decision, self.base_state, pos, "ORD_01")
        self.assertIsNotNone(order)
        self.assertEqual(order.side, "buy")
        self.assertGreater(order.quantity, 0)

if __name__ == "__main__":
    unittest.main()
