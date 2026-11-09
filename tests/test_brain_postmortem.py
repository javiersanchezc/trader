import unittest
from core.brain import BrainEngine

class TestBrainEngine(unittest.TestCase):
    def setUp(self):
        self.brain = BrainEngine()

    def test_brier_score_perfect_calibration(self):
        for i in range(10):
            self.brain.log_decision_and_outcome(
                timestamp=1000 + i,
                symbol="BTC/USDT",
                direction="long",
                confidence=1.0,
                setup_quality=3,
                executed=True,
                rejection_reason=None,
                actual_return_bps=25.0
            )
        score = self.brain.compute_brier_score()
        self.assertEqual(score, 0.0)

    def test_brier_score_random_calibration(self):
        self.brain.log_decision_and_outcome(1001, "BTC/USDT", "long", 0.5, 2, True, None, 10.0)
        self.brain.log_decision_and_outcome(1002, "BTC/USDT", "long", 0.5, 2, True, None, -10.0)
        score = self.brain.compute_brier_score()
        self.assertAlmostEqual(score, 0.25, places=4)

    def test_nightly_post_mortem_audit(self):
        self.brain.log_decision_and_outcome(1001, "BTC/USDT", "long", 0.85, 3, True, None, 45.0)
        self.brain.log_decision_and_outcome(1002, "BTC/USDT", "long", 0.82, 2, True, None, 30.0)
        self.brain.log_decision_and_outcome(1003, "BTC/USDT", "short", 0.86, 3, True, None, 50.0)
        self.brain.log_decision_and_outcome(1004, "BTC/USDT", "long", 0.81, 2, True, None, -20.0)
        self.brain.log_decision_and_outcome(1005, "BTC/USDT", "long", 0.75, 1, False, "Calidad < 2", 60.0)
        self.brain.log_decision_and_outcome(1006, "BTC/USDT", "neutral", 0.50, 0, False, "Neutral", 0.0)

        report = self.brain.nightly_post_mortem()
        self.assertEqual(report["total_evaluaciones"], 6)
        self.assertEqual(report["total_ejecuciones"], 4)
        self.assertEqual(report["total_descartes"], 2)
        self.assertEqual(report["tasa_de_acierto"], 0.75)
        self.assertEqual(report["ganadoras_descartadas"], 1)
        self.assertIn("puntaje_de_brier", report)
        self.assertIn("accion_recomendada", report)

if __name__ == "__main__":
    unittest.main()
