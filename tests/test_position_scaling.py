import unittest
from core.position_scaling import ScaleInManager

class TestPositionScaling(unittest.TestCase):
    def setUp(self):
        self.manager = ScaleInManager(symbol="BTC/USDT")

    def test_scale_in_calculation(self):
        plan = self.manager.calcular_plan_escalado(
            margen_total_usdt=500.0,
            apalancamiento=3.0,
            zona_alta_demanda=73500.0,
            zona_baja_demanda=72800.0
        )
        self.assertEqual(plan.margen_total_usdt, 500.0)
        self.assertEqual(plan.nocional_total_usdt, 1500.0)
        self.assertEqual(len(plan.tramos), 3)

        # Verificar porcentajes 30% / 30% / 40%
        self.assertAlmostEqual(plan.tramos[0].margen_usdt, 150.0)
        self.assertAlmostEqual(plan.tramos[1].margen_usdt, 150.0)
        self.assertAlmostEqual(plan.tramos[2].margen_usdt, 200.0)

        # Verificar que el precio promedio ponderado es menor que el precio de entrada inicial
        self.assertLess(plan.precio_promedio_proyectado, 73500.0)
        self.assertGreater(plan.precio_promedio_proyectado, 72800.0)

        # Stop loss debe estar por debajo de la zona baja
        self.assertLess(plan.stop_loss_inmutable, 72800.0)

        # La pérdida máxima calculada debe ser menor al 10% del margen total
        self.assertLess(plan.perdida_maxima_pct, 10.0)
        self.assertGreater(plan.ratio_riesgo_beneficio, 1.8)

if __name__ == "__main__":
    unittest.main()
