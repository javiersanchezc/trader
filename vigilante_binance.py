"""
vigilante_binance.py - Vigilante en Vivo conectado DIRECTAMENTE a Binance (sin TradingView, sin webhook)

En vez de esperar a que TradingView nos envíe la alerta, el sistema VA A BUSCAR los datos a Binance
(API pública, NO necesita API key ni permisos de trading) y calcula todo él mismo:

  1. Velas 4H  -> RSI de Wilder + Divergencia alcista (< 35)         [core/choch_rsi_strategy.py]
  2. Velas 5m  -> CHoCH (cierre con cuerpo sobre el último swing high)
  3. Libro L2  -> Spread REAL en bps                                  [semáforo de liquidez]
  4. Ticker    -> Volumen 24h REAL en USDT
  5. Velas 4H  -> Caída REAL de las últimas 4 velas                   [semáforo cuchillo cayendo]
  6. Velas 5m  -> Soporte real del impulso (swing low) para anclar las 3 órdenes

Solo usa velas CERRADAS (la vela en curso se descarta) -> cero repintado / cero lookahead.

MODOS:
  python vigilante_binance.py MSTR --ahora                 # Foto instantánea + plan con datos reales
  python vigilante_binance.py MSTR BTC SOL                 # Vigila 24/7 y genera el plan al saltar la señal
  python vigilante_binance.py MSTR BTC --max-risk 15 --capital 500 --lev 3 --intervalo 30

Este script NUNCA envía órdenes. Solo lee datos y escribe planes en la carpeta planes/.
"""

from __future__ import annotations
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.types import Candle
from core.choch_rsi_strategy import ChochRsiStrategy
from core.notificador_telegram import NotificadorTelegram, extraer_resumen_plan
from generador_plan_alerta import calcular_y_generar_plan

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CARPETA_PLANES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "planes")
VELAS_IMPULSO_5M = 24          # 2 horas de velas de 5m para localizar el origen del impulso
AMPLITUD_MINIMA_PCT = 0.40     # Si el impulso es menor, el soporte no es significativo -> usa preset


@dataclass
class LecturaMercado:
    simbolo: str
    precio: float
    spread_bps: float
    volumen_24h_usdt: float
    caida_4h_pct: float
    swing_low: Optional[float]
    rsi_4h: float
    divergencia_4h: bool
    choch_5m: bool
    swing_high_5m: Optional[float]
    senal_confirmada: bool
    ts_vela_5m: int


# ----------------------------------------------------------------------------------------------
# Conexión con Binance
# ----------------------------------------------------------------------------------------------
def crear_exchange():
    """Binance Futuros USDT-M (donde cotiza MSTRUSDT perpetuo). Solo endpoints públicos."""
    import ccxt
    ex = ccxt.binanceusdm({"enableRateLimit": True, "timeout": 15000})
    ex.load_markets()
    return ex


def resolver_simbolo(exchange, base: str) -> str:
    base = base.upper().replace("USDT", "").replace("/", "").replace(":", "").strip()
    for candidato in (f"{base}/USDT:USDT", f"{base}/USDT"):
        if candidato in exchange.markets:
            return candidato
    raise ValueError(f"{base} no cotiza en Binance Futuros USDT-M")


def a_velas(ohlcv: List[List[float]]) -> List[Candle]:
    return [Candle(int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5] or 0.0)) for r in ohlcv]


# ----------------------------------------------------------------------------------------------
# Cálculos (puros, testeables sin red)
# ----------------------------------------------------------------------------------------------
def calcular_spread_bps(order_book: Dict[str, Any]) -> float:
    bids, asks = order_book.get("bids") or [], order_book.get("asks") or []
    if not bids or not asks:
        return 9999.0  # Libro vacío = tóxico
    best_bid, best_ask = float(bids[0][0]), float(asks[0][0])
    mid = (best_bid + best_ask) / 2.0
    return ((best_ask - best_bid) / mid) * 10_000.0 if mid > 0 else 9999.0


def calcular_caida_4h_pct(velas_4h: List[Candle], precio: float) -> float:
    """Caída desde la apertura de hace 4 velas de 4H (~16h). Positivo = ha caído."""
    if len(velas_4h) < 4:
        return 0.0
    p_inicio = velas_4h[-4].open
    return max(0.0, ((p_inicio - precio) / p_inicio) * 100.0) if p_inicio > 0 else 0.0


def calcular_swing_low_impulso(velas_5m: List[Candle], precio: float, swing_low_estrategia: Optional[float]) -> Optional[float]:
    """Origen del impulso: el mínimo más bajo entre el swing low estructural y las últimas 2 horas."""
    if not velas_5m:
        return None
    minimo_reciente = min(c.low for c in velas_5m[-VELAS_IMPULSO_5M:])
    candidatos = [minimo_reciente] + ([swing_low_estrategia] if swing_low_estrategia else [])
    soporte = min(candidatos)
    if soporte >= precio:
        return None
    amplitud_pct = (precio - soporte) / precio * 100.0
    if amplitud_pct < AMPLITUD_MINIMA_PCT:
        return None
    return soporte


def leer_mercado(exchange, base: str, estrategia: Optional[ChochRsiStrategy] = None) -> LecturaMercado:
    estrategia = estrategia or ChochRsiStrategy()
    simbolo = resolver_simbolo(exchange, base)

    # Se descarta la última vela (en curso) -> solo velas cerradas
    velas_4h = a_velas(exchange.fetch_ohlcv(simbolo, "4h", limit=150))[:-1]
    velas_5m = a_velas(exchange.fetch_ohlcv(simbolo, "5m", limit=120))[:-1]
    libro = exchange.fetch_order_book(simbolo, limit=10)
    ticker = exchange.fetch_ticker(simbolo)

    precio = float(ticker.get("last") or velas_5m[-1].close)
    volumen = float(ticker.get("quoteVolume") or 0.0)
    if volumen <= 0 and ticker.get("baseVolume"):
        volumen = float(ticker["baseVolume"]) * precio

    divergencia, rsi = estrategia.detectar_divergencia_alcista_4h(velas_4h)
    choch, swing_high, swing_low_est = estrategia.detectar_choch_5m(velas_5m)

    return LecturaMercado(
        simbolo=simbolo,
        precio=precio,
        spread_bps=round(calcular_spread_bps(libro), 2),
        volumen_24h_usdt=volumen,
        caida_4h_pct=round(calcular_caida_4h_pct(velas_4h, precio), 2),
        swing_low=calcular_swing_low_impulso(velas_5m, precio, swing_low_est),
        rsi_4h=round(rsi, 2),
        divergencia_4h=divergencia,
        choch_5m=choch,
        swing_high_5m=swing_high,
        senal_confirmada=bool(divergencia and choch),
        ts_vela_5m=velas_5m[-1].timestamp,
    )


# ----------------------------------------------------------------------------------------------
# Salida
# ----------------------------------------------------------------------------------------------
def resumen_lectura(l: LecturaMercado) -> str:
    si_no = lambda b: "SI" if b else "no"
    soporte = f"${l.swing_low:,.4f}" if l.swing_low else "no significativo (usa volatilidad calibrada)"
    return "\n".join([
        "-" * 104,
        f"  LECTURA EN VIVO BINANCE  {l.simbolo}   {datetime.now():%Y-%m-%d %H:%M:%S}",
        "-" * 104,
        f"  Precio actual         : ${l.precio:,.4f}",
        f"  RSI 4H                : {l.rsi_4h:.2f}   | Divergencia alcista 4H : {si_no(l.divergencia_4h)}",
        f"  CHoCH 5m (vela cerrada): {si_no(l.choch_5m)}   | Swing high 5m          : {l.swing_high_5m or '-'}",
        f"  Soporte del impulso   : {soporte}",
        f"  Spread real           : {l.spread_bps:.2f} bps",
        f"  Volumen 24h real      : ${l.volumen_24h_usdt:,.0f}",
        f"  Caida ultimas 4 velas 4H: {l.caida_4h_pct:.2f}%",
        f"  >>> SENAL COMPLETA (Div 4H + CHoCH 5m): {'*** CONFIRMADA ***' if l.senal_confirmada else 'todavia no'}",
        "-" * 104,
    ])


def generar_plan_desde_lectura(l: LecturaMercado, capital: float, lev: float, max_riesgo: float) -> str:
    return calcular_y_generar_plan(
        simbolo=l.simbolo.split(":")[0],
        precio_alerta=l.precio,
        capital_usdt=capital,
        apalancamiento=lev,
        swing_low=l.swing_low,
        max_riesgo_usdt=max_riesgo,
        caida_reciente_pct=l.caida_4h_pct,
        spread_bps=l.spread_bps,
        volumen_24h_usdt=l.volumen_24h_usdt,
    )


def guardar_plan(l: LecturaMercado, texto: str, prefijo: str) -> str:
    os.makedirs(CARPETA_PLANES, exist_ok=True)
    base = l.simbolo.split("/")[0]
    ruta = os.path.join(CARPETA_PLANES, f"{datetime.now():%Y%m%d_%H%M%S}_{base}_{prefijo}.txt")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(resumen_lectura(l) + "\n\n" + texto)
    return ruta


def construir_mensaje_telegram(l: LecturaMercado, plan: str, es_senal: bool) -> str:
    base = l.simbolo.split("/")[0]
    cabecera = f"🚨 SEÑAL CONFIRMADA {base}" if es_senal else f"📸 Foto de mercado {base} (señal NO confirmada)"
    lineas = [
        cabecera,
        f"🕒 {datetime.now():%d/%m %H:%M}  |  Precio ${l.precio:,.4f}",
        f"📊 RSI4H {l.rsi_4h:.1f} | Div 4H {'✅' if l.divergencia_4h else '❌'} | CHoCH 5m {'✅' if l.choch_5m else '❌'}",
        f"💧 Spread {l.spread_bps:.2f} bps | Vol24h ${l.volumen_24h_usdt/1e6:,.1f}M | Caída 4H {l.caida_4h_pct:.1f}%",
        f"🧱 Soporte impulso: {'$' + format(l.swing_low, ',.4f') if l.swing_low else 'volatilidad calibrada'}",
        "",
    ]
    lineas += extraer_resumen_plan(plan)
    if not es_senal:
        lineas += ["", "⚠️ Solo referencia: espera la confirmación Div 4H + CHoCH 5m."]
    lineas += ["", "Pon las 3 límites + SL y cierra la gráfica. Plan, no susto."]
    return "\n".join(lineas)


def notificar(notificador: Optional[NotificadorTelegram], l: LecturaMercado, plan: str, ruta: str, es_senal: bool) -> None:
    if not notificador or not notificador.activo:
        return
    ok = notificador.enviar_mensaje(construir_mensaje_telegram(l, plan, es_senal))
    ok_doc = notificador.enviar_documento(ruta, caption=f"Plan completo {l.simbolo.split('/')[0]}")
    if ok and ok_doc:
        print("  [TELEGRAM] Alerta y plan enviados al movil.")
    else:
        print(f"  [TELEGRAM] Fallo el envio: {notificador.ultimo_error}")


# ----------------------------------------------------------------------------------------------
# Modos
# ----------------------------------------------------------------------------------------------
def modo_ahora(exchange, activos: List[str], capital: float, lev: float, max_riesgo: float,
               notificador: Optional[NotificadorTelegram] = None) -> None:
    for base in activos:
        try:
            l = leer_mercado(exchange, base)
        except Exception as e:
            print(f"[ERROR {base}]: {e}")
            continue
        plan = generar_plan_desde_lectura(l, capital, lev, max_riesgo)
        print(resumen_lectura(l))
        if not l.senal_confirmada:
            print("  ! AVISO: La senal Div 4H + CHoCH 5m NO esta confirmada. Este plan es solo de referencia.\n")
        print(plan)
        ruta = guardar_plan(l, plan, 'foto')
        print(f"  Guardado en: {ruta}\n")
        notificar(notificador, l, plan, ruta, es_senal=l.senal_confirmada)


def modo_vigilante(exchange, activos: List[str], capital: float, lev: float, max_riesgo: float, intervalo: int,
                   notificador: Optional[NotificadorTelegram] = None) -> None:
    ultima_vela_alertada: Dict[str, int] = {}
    print(f"\n[VIGILANTE BINANCE ACTIVO] Activos: {', '.join(activos)} | Revisando cada {intervalo}s | Ctrl+C para salir\n")
    if notificador and notificador.activo:
        notificador.enviar_mensaje(
            f"🤖 Vigilante activo\nActivos: {', '.join(activos)}\nRiesgo máx: ${max_riesgo:,.2f} | Capital ${capital:,.0f} | {lev:.0f}x\n"
            f"Te aviso aquí cuando se confirme Div RSI 4H + CHoCH 5m."
        )
    while True:
        for base in activos:
            try:
                l = leer_mercado(exchange, base)
            except Exception as e:
                print(f"[{datetime.now():%H:%M:%S}] [ERROR {base}]: {e} (reintento en el siguiente ciclo)")
                continue

            estado = "SENAL!" if l.senal_confirmada else "esperando"
            print(f"[{datetime.now():%H:%M:%S}] {l.simbolo:<16} ${l.precio:<12,.4f} RSI4H {l.rsi_4h:5.1f} "
                  f"Div:{'S' if l.divergencia_4h else 'n'} CHoCH:{'S' if l.choch_5m else 'n'} "
                  f"Spread {l.spread_bps:5.2f}bps Caida {l.caida_4h_pct:4.1f}% -> {estado}")

            if l.senal_confirmada and ultima_vela_alertada.get(base) != l.ts_vela_5m:
                ultima_vela_alertada[base] = l.ts_vela_5m  # Una sola alerta por vela de 5m
                plan = generar_plan_desde_lectura(l, capital, lev, max_riesgo)
                print("\a")  # Pitido
                print(resumen_lectura(l))
                print(plan)
                ruta = guardar_plan(l, plan, 'SENAL')
                print(f"  Guardado en: {ruta}\n")
                notificar(notificador, l, plan, ruta, es_senal=True)
        time.sleep(intervalo)


def parsear_argumentos(argv: List[str]) -> Dict[str, Any]:
    cfg: Dict[str, Any] = {"activos": [], "capital": 500.0, "lev": 3.0, "max_riesgo": 20.0, "intervalo": 60,
                           "ahora": False, "telegram": None, "test_telegram": False}
    flags_valor = {"--capital": ("capital", float), "--lev": ("lev", float),
                   "--max-risk": ("max_riesgo", float), "--intervalo": ("intervalo", int)}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in flags_valor and i + 1 < len(argv):
            clave, tipo = flags_valor[a]
            cfg[clave] = tipo(argv[i + 1])
            i += 2
            continue
        if a == "--ahora":
            cfg["ahora"] = True
        elif a == "--telegram":
            cfg["telegram"] = True
        elif a == "--sin-telegram":
            cfg["telegram"] = False
        elif a == "--test-telegram":
            cfg["test_telegram"] = True
        elif not a.startswith("--"):
            cfg["activos"].append(a.upper())
        i += 1
    if not cfg["activos"]:
        cfg["activos"] = ["BTC"]
    cfg["intervalo"] = max(10, cfg["intervalo"])
    # Por defecto: el vigilante continuo SÍ avisa por Telegram; la foto (--ahora) solo si se pide --telegram
    if cfg["telegram"] is None:
        cfg["telegram"] = not cfg["ahora"]
    return cfg


def main() -> None:
    cfg = parsear_argumentos(sys.argv[1:])
    notificador = NotificadorTelegram() if (cfg["telegram"] or cfg["test_telegram"]) else None

    if cfg["test_telegram"]:
        if not notificador.activo:
            print("[TELEGRAM] No configurado: crea telegram_config.json o define TELEGRAM_TOKEN / TELEGRAM_CHAT_ID.")
            return
        ok = notificador.enviar_mensaje("✅ Prueba de conexión: el sistema de trading d:\\trader ya puede enviarte alertas.")
        print("[TELEGRAM] Mensaje de prueba enviado." if ok else f"[TELEGRAM] Error: {notificador.ultimo_error}")
        return

    if notificador and not notificador.activo:
        print("[TELEGRAM] Aviso: no configurado, se continua sin notificaciones al movil.")

    try:
        exchange = crear_exchange()
    except Exception as e:
        print(f"[ERROR] No se pudo conectar con Binance: {e}")
        print("Comprueba tu conexion a internet (o si Binance esta restringido en tu red/pais).")
        return

    if cfg["ahora"]:
        modo_ahora(exchange, cfg["activos"], cfg["capital"], cfg["lev"], cfg["max_riesgo"], notificador)
    else:
        try:
            modo_vigilante(exchange, cfg["activos"], cfg["capital"], cfg["lev"], cfg["max_riesgo"], cfg["intervalo"], notificador)
        except KeyboardInterrupt:
            print("\n[VIGILANTE DETENIDO]")


if __name__ == "__main__":
    main()
