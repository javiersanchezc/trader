"""
notificador_telegram.py - Envío de alertas y planes al móvil vía Telegram Bot API.

Credenciales (por orden de prioridad):
  1. Variables de entorno TELEGRAM_TOKEN y TELEGRAM_CHAT_ID
  2. Archivo local telegram_config.json  (excluido de git en .gitignore)

Solo usa la librería estándar (urllib). Nunca lanza excepciones hacia el vigilante:
si Telegram falla, devuelve False y el sistema sigue funcionando.
"""

from __future__ import annotations
import json
import os
import re
import uuid
import urllib.request
import urllib.parse
from typing import Optional, Tuple, List

RUTA_CONFIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "telegram_config.json")
LIMITE_MENSAJE = 4000  # Telegram admite 4096 caracteres


def cargar_credenciales(ruta: str = RUTA_CONFIG) -> Tuple[Optional[str], Optional[str]]:
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if token and chat_id:
        return token, chat_id
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return cfg.get("telegram_token"), str(cfg.get("chat_id") or "") or None
        except Exception:
            return None, None
    return None, None


def extraer_resumen_plan(plan: str) -> List[str]:
    """Extrae del plan las líneas clave (órdenes, SL, TP, riesgo) en formato compacto para móvil."""
    resumen = []
    for linea in plan.splitlines():
        l = linea.strip()
        m = re.match(r"Orden (\d)\s*\|\s*Limit Buy\s*\|\s*\$(\S+)\s*\|\s*(\S+)\s*\|\s*\$(\S+)", l)
        if m:
            resumen.append(f"🟢 Orden {m.group(1)}: ${m.group(2)}  | cant {m.group(3)} | margen ${m.group(4)}")
            continue
        if l.startswith("* STOP LOSS"):
            resumen.append("🛑 SL: " + l.split(":", 1)[1].strip().split(" (")[0])
        elif l.startswith("- Riesgo Maximo"):
            resumen.append("💸 Pérdida máx: " + l.split(":", 1)[1].strip().split(" (")[0])
        elif l.startswith("* TAKE PROFIT 1"):
            resumen.append("🎯 TP1 (50%): " + l.split(":", 1)[1].strip().replace("-->", "→"))
        elif l.startswith("* TAKE PROFIT 2"):
            resumen.append("🎯 TP2 (50%): " + l.split(":", 1)[1].strip().replace("-->", "→"))
        elif l.startswith(">>> SI SE LLENAN LAS 3"):
            precio_prom = l.split("quedara en:")[-1].strip() if "quedara en:" in l else l.split(":")[-1].strip()
            resumen.append(f"⚖️ Promedio si llenan 3: {precio_prom}")
        elif l.startswith("* ACCION EN CODIGO DURO"):
            resumen.append("🛡️ Guardián: exposición reducida " + l.split("a ", 1)[-1].strip())
        elif "ORDEN DE BLOQUEO DE SEGURIDAD" in l:
            resumen.append("⛔ BLOQUEADO POR SEGURIDAD: no se generan órdenes")
        elif l.startswith("Motivo:"):
            resumen.append("   " + l)
    return resumen


class NotificadorTelegram:
    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None, timeout: int = 15):
        if token is None or chat_id is None:
            t, c = cargar_credenciales()
            token, chat_id = token or t, chat_id or c
        self.token = token
        self.chat_id = chat_id
        self.timeout = timeout
        self.ultimo_error = ""

    @property
    def activo(self) -> bool:
        return bool(self.token and self.chat_id)

    def _url(self, metodo: str) -> str:
        return f"https://api.telegram.org/bot{self.token}/{metodo}"

    def enviar_mensaje(self, texto: str) -> bool:
        if not self.activo:
            self.ultimo_error = "Telegram no configurado"
            return False
        ok = True
        for i in range(0, len(texto), LIMITE_MENSAJE):
            datos = urllib.parse.urlencode({
                "chat_id": self.chat_id,
                "text": texto[i:i + LIMITE_MENSAJE],
                "disable_web_page_preview": "true",
            }).encode("utf-8")
            ok = self._post(urllib.request.Request(self._url("sendMessage"), data=datos)) and ok
        return ok

    def enviar_documento(self, ruta_archivo: str, caption: str = "") -> bool:
        if not self.activo or not os.path.exists(ruta_archivo):
            self.ultimo_error = "Telegram no configurado o archivo inexistente"
            return False
        limite = "----trader" + uuid.uuid4().hex
        with open(ruta_archivo, "rb") as f:
            contenido = f.read()
        nombre = os.path.basename(ruta_archivo)
        partes = []
        for campo, valor in (("chat_id", self.chat_id), ("caption", caption[:1000])):
            partes.append(f"--{limite}\r\nContent-Disposition: form-data; name=\"{campo}\"\r\n\r\n{valor}\r\n".encode("utf-8"))
        partes.append(
            f"--{limite}\r\nContent-Disposition: form-data; name=\"document\"; filename=\"{nombre}\"\r\n"
            f"Content-Type: text/plain\r\n\r\n".encode("utf-8") + contenido + b"\r\n"
        )
        partes.append(f"--{limite}--\r\n".encode("utf-8"))
        req = urllib.request.Request(self._url("sendDocument"), data=b"".join(partes))
        req.add_header("Content-Type", f"multipart/form-data; boundary={limite}")
        return self._post(req)

    def _post(self, req: urllib.request.Request) -> bool:
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                respuesta = json.loads(resp.read().decode("utf-8"))
                if not respuesta.get("ok"):
                    self.ultimo_error = str(respuesta)
                return bool(respuesta.get("ok"))
        except Exception as e:
            # No exponer el token en logs
            self.ultimo_error = str(e).replace(self.token or "", "***")
            return False
