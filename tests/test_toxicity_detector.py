import unittest
from core.toxicity_detector import ToxicityDetector

class TestToxicityDetector(unittest.TestCase):
    def setUp(self):
        self.detector = ToxicityDetector(
            max_spread_bps=25.0,
            max_caida_veloz_pct=7.0,
            min_volumen_24h_usdt=5_000_000.0
        )

    def test_mercado_saludable(self):
        diag = self.detector.evaluar_seguridad_mercado(
            precio_actual=74000.0,
            caida_pct_forzada=2.5,
            spread_bps_forzado=3.0,
            volumen_24h_forzado=80_000_000.0
        )
        self.assertEqual(diag.nivel_peligro, "SEGURO")
        self.assertTrue(diag.aprobado_para_operar)

    def test_bloqueo_cuchillo_cayendo(self):
        diag = self.detector.evaluar_seguridad_mercado(
            precio_actual=74000.0,
            caida_pct_forzada=9.5, # > 7.0%
            spread_bps_forzado=4.0
        )
        self.assertEqual(diag.nivel_peligro, "PELIGRO_EXTREMO_BLOQUEADO")
        self.assertFalse(diag.aprobado_para_operar)
        self.assertTrue(diag.es_caida_libre_extrema)

    def test_bloqueo_spread_toxico(self):
        diag = self.detector.evaluar_seguridad_mercado(
            precio_actual=74000.0,
            caida_pct_forzada=1.0,
            spread_bps_forzado=38.0 # > 25 bps
        )
        self.assertFalse(diag.aprobado_para_operar)
        self.assertTrue(diag.tiene_problemas_liquidez)

if __name__ == "__main__":
    unittest.main()
