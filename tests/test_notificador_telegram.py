import unittest
from unittest import mock
from core.notificador_telegram import NotificadorTelegram, extraer_resumen_plan
from generador_plan_alerta import calcular_y_generar_plan


class TestNotificadorTelegram(unittest.TestCase):
    def test_no_configurado_no_envia(self):
        n = NotificadorTelegram(token="", chat_id="")
        self.assertFalse(n.activo)
        self.assertFalse(n.enviar_mensaje("hola"))

    def test_resumen_extrae_ordenes_sl_tp(self):
        plan = calcular_y_generar_plan("MSTR", 127.35, 500, 3, swing_low=121.88, max_riesgo_usdt=15)
        r = "\n".join(extraer_resumen_plan(plan))
        self.assertIn("Orden 1: $125.260", r)
        self.assertIn("Orden 3", r)
        self.assertIn("SL: $121.453", r)
        self.assertIn("-$15.00 USDT", r)
        self.assertIn("TP1", r)
        self.assertIn("TP2", r)

    def test_resumen_bloqueo(self):
        plan = calcular_y_generar_plan("MSTR", 127.35, 500, 3, caida_reciente_pct=9.5)
        self.assertTrue(any("BLOQUEADO" in x for x in extraer_resumen_plan(plan)))

    def test_envio_usa_api_y_oculta_token_en_errores(self):
        n = NotificadorTelegram(token="TOKEN_SECRETO", chat_id="123")
        with mock.patch("urllib.request.urlopen", side_effect=Exception("fallo con TOKEN_SECRETO")):
            self.assertFalse(n.enviar_mensaje("hola"))
        self.assertNotIn("TOKEN_SECRETO", n.ultimo_error)


if __name__ == "__main__":
    unittest.main()
