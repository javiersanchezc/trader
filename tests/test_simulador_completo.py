import unittest
from simulador_estrategia_completa import (
    crear_velas_4h_con_divergencia,
    crear_velas_4h_sin_divergencia,
    crear_velas_5m_choch
)
from core.choch_rsi_strategy import ChochRsiStrategy

class TestSimuladorCompleto(unittest.TestCase):
    def setUp(self):
        self.strat = ChochRsiStrategy()

    def test_escenarios_coherencia(self):
        c4_div = crear_velas_4h_con_divergencia()
        c4_sin = crear_velas_4h_sin_divergencia()
        c5, sh, sl, close = crear_velas_5m_choch()

        # Con divergencia 4H debe confirmar
        s_ok = self.strat.evaluar_estrategia(c4_div, c5, 500.0, 3.0)
        self.assertTrue(s_ok.confirmado)

        # Sin divergencia 4H debe bloquear
        s_fail = self.strat.evaluar_estrategia(c4_sin, c5, 500.0, 3.0)
        self.assertFalse(s_fail.confirmado)

if __name__ == "__main__":
    unittest.main()
