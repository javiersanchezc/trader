import unittest
from core.types import Candle
from vigilante_binance import (
    calcular_spread_bps,
    calcular_caida_4h_pct,
    calcular_swing_low_impulso,
    leer_mercado,
    generar_plan_desde_lectura,
    parsear_argumentos,
)


class FakeExchange:
    """Simula la API pública de Binance sin red."""
    def __init__(self, precio=127.35):
        self.precio = precio
        self.markets = {"MSTR/USDT:USDT": {}}

    def fetch_ohlcv(self, simbolo, tf, limit=100):
        filas, ts = [], 1_700_000_000_000
        paso = 14_400_000 if tf == "4h" else 300_000
        for i in range(limit):
            p = 130.0 - (i % 20) * 0.2 if tf == "4h" else 122.0 + i * 0.05
            filas.append([ts + i * paso, p, p + 0.5, p - 0.5, p, 1000.0])
        return filas

    def fetch_order_book(self, simbolo, limit=10):
        return {"bids": [[127.34, 50]], "asks": [[127.36, 50]]}

    def fetch_ticker(self, simbolo):
        return {"last": self.precio, "quoteVolume": 80_000_000.0}


class TestVigilanteBinance(unittest.TestCase):
    def test_spread(self):
        self.assertAlmostEqual(calcular_spread_bps({"bids": [[99.99, 1]], "asks": [[100.01, 1]]}), 2.0, places=2)
        self.assertEqual(calcular_spread_bps({"bids": [], "asks": []}), 9999.0)

    def test_caida_4h(self):
        velas = [Candle(i, 100.0, 101, 99, 100, 1) for i in range(6)]
        self.assertAlmostEqual(calcular_caida_4h_pct(velas, 92.0), 8.0)
        self.assertEqual(calcular_caida_4h_pct(velas, 105.0), 0.0)

    def test_swing_low_descarta_impulsos_minusculos(self):
        velas = [Candle(i, 100, 100.1, 99.9, 100, 1) for i in range(30)]
        self.assertIsNone(calcular_swing_low_impulso(velas, 100.05, None))
        velas[-5] = Candle(0, 100, 100, 96.0, 99, 1)
        self.assertEqual(calcular_swing_low_impulso(velas, 100.0, None), 96.0)

    def test_lectura_y_plan_con_exchange_simulado(self):
        l = leer_mercado(FakeExchange(), "MSTR")
        self.assertEqual(l.simbolo, "MSTR/USDT:USDT")
        self.assertAlmostEqual(l.spread_bps, 1.57, places=1)
        self.assertEqual(l.volumen_24h_usdt, 80_000_000.0)
        plan = generar_plan_desde_lectura(l, 500.0, 3.0, 15.0)
        self.assertIn("MSTR/USDT", plan)
        self.assertIn("VERDE - SEGURO", plan)

    def test_argumentos(self):
        cfg = parsear_argumentos(["mstr", "btc", "--max-risk", "15", "--ahora"])
        self.assertEqual(cfg["activos"], ["MSTR", "BTC"])
        self.assertEqual(cfg["max_riesgo"], 15.0)
        self.assertTrue(cfg["ahora"])


if __name__ == "__main__":
    unittest.main()
