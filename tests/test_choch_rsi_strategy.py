import unittest
from core.types import Candle
from core.choch_rsi_strategy import ChochRsiStrategy
from estrategia_choch_4h_5m import simular_mercado_choch_div

class TestChochRsiStrategy(unittest.TestCase):
    def setUp(self):
        self.strat = ChochRsiStrategy()

    def test_rsi_calculation(self):
        # Secuencia creciente simple
        closes = [100.0 + i * 2.0 for i in range(30)]
        rsi = self.strat.calcular_rsi(closes)
        self.assertEqual(len(rsi), len(closes))
        self.assertGreater(rsi[-1], 70.0)

    def test_full_setup_evaluation(self):
        c_4h, c_5m = simular_mercado_choch_div()
        setup = self.strat.evaluar_estrategia(c_4h, c_5m, capital_usdt=500.0, apalancamiento=3.0)
        self.assertTrue(setup.confirmado)
        self.assertTrue(setup.divergencia_4h_activa)
        self.assertGreater(setup.precio_quiebre_choch, setup.swing_high_roto)
        self.assertLess(setup.plan_escalamiento.precio_promedio_proyectado, setup.precio_quiebre_choch)

if __name__ == "__main__":
    unittest.main()
