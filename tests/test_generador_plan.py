import unittest
from generador_plan_alerta import calcular_y_generar_plan

class TestGeneradorPlanAlerta(unittest.TestCase):
    def test_generacion_plan_btc(self):
        reporte = calcular_y_generar_plan(
            simbolo="BTC/USDT",
            precio_alerta=74400.0,
            capital_usdt=500.0,
            apalancamiento=3.0
        )
        self.assertIn("BTC/USDT", reporte)
        self.assertIn("Orden 1", reporte)
        self.assertIn("STOP LOSS OBLIGATORIO", reporte)

    def test_generacion_plan_eth(self):
        reporte = calcular_y_generar_plan(
            simbolo="ETH",
            precio_alerta=2950.0,
            capital_usdt=500.0,
            apalancamiento=3.0
        )
        self.assertIn("ETH/USDT", reporte)
        self.assertIn("CANTIDAD ETH", reporte)

    def test_generacion_plan_sol(self):
        reporte = calcular_y_generar_plan(
            simbolo="SOL",
            precio_alerta=185.5,
            capital_usdt=500.0,
            apalancamiento=3.0
        )
        self.assertIn("SOL/USDT", reporte)
        self.assertIn("CANTIDAD SOL", reporte)

    def test_anclaje_estructural_y_recorte_riesgo_mstr(self):
        # MSTR en $127.35 con soporte real de mecha en $121.88 (rango 4.29%)
        # Con 3x completo perdería ~$37 USDT; el guardián debe recortarlo a -$20.00 USDT exactos
        reporte = calcular_y_generar_plan(
            simbolo="MSTR",
            precio_alerta=127.35,
            capital_usdt=500.0,
            apalancamiento=3.0,
            swing_low=121.88,
            max_riesgo_usdt=20.0
        )
        self.assertIn("ANCLADO A SOPORTE REAL EN GRAFICA ($121.880", reporte)
        self.assertIn("GUARDIAN DE RIESGO DETERMINISTA - AJUSTE AUTOMATICO DE POSICION", reporte)
        self.assertIn("-$20.00 USDT", reporte)
        self.assertIn("ESCENARIO LLENADO PARCIAL", reporte)

if __name__ == "__main__":
    unittest.main()
