"""
estrategia_choch_4h_5m.py - Ejecutor de la Estrategia CHoCH 5m + Divergencia RSI 4H
Implementa el indicador Pine Script v6 en Python con la comparativa de:
- Modo A: Entrada clásica a mercado en el quiebre (Pine Script puro).
- Modo B: Escalamiento Institucional 30/30/40 en el retroceso al Order Block.
Soporta tanto simulación instantánea como escaneo en vivo con CCXT (--live).
"""

from __future__ import annotations
import sys
import time
from core.types import Candle
from core.choch_rsi_strategy import ChochRsiStrategy, SetupCHoCHRSI

def simular_mercado_choch_div(precio_base: float = 74500.0):
    candles_4h = []
    ts = int(time.time() * 1000) - 50 * 14400000

    p = 76000.0
    for i in range(12):
        ts += 14400000
        p -= 220.0
        candles_4h.append(Candle(ts, p + 50, p + 100, p - 60, p, 1500.0))

    # Trough 1
    candles_4h.append(Candle(ts + 14400000, p, p + 30, p - 80, p - 50, 1800.0))
    ts += 14400000
    p = p - 50

    # Rebound
    for i in range(4):
        ts += 14400000
        p += 150.0
        candles_4h.append(Candle(ts, p - 30, p + 50, p - 40, p, 800.0))

    # Second drop (Lower low in price, higher low in RSI)
    for i in range(6):
        ts += 14400000
        p -= 120.0
        candles_4h.append(Candle(ts, p + 20, p + 40, p - 50, p, 600.0))
    
    # Trough 2
    candles_4h.append(Candle(ts + 14400000, p, p + 20, p - 100, p - 70, 700.0))
    ts += 14400000
    p = p - 70

    # Confirmation rebound
    for i in range(4):
        ts += 14400000
        p += 60.0
        candles_4h.append(Candle(ts, p - 20, p + 40, p - 30, p, 500.0))

    # 5m candles with CHoCH break
    candles_5m = []
    base_5m = p - 100.0
    ts_5m = int(time.time() * 1000) - 25 * 300000

    for i in range(10):
        ts_5m += 300000
        p_5m = base_5m + (i * 8.0)
        candles_5m.append(Candle(ts_5m, p_5m, p_5m + 20, p_5m - 20, p_5m + 5, 80.0))

    swing_high_p = base_5m + 120.0
    ts_5m += 300000
    candles_5m.append(Candle(ts_5m, swing_high_p - 15, swing_high_p, swing_high_p - 30, swing_high_p - 20, 90.0))

    for i in range(4):
        ts_5m += 300000
        p_sub = swing_high_p - 30.0 - (i * 12.0)
        candles_5m.append(Candle(ts_5m, p_sub + 10, p_sub + 15, p_sub - 15, p_sub, 70.0))

    swing_low_p = p_sub - 20.0
    ts_5m += 300000
    candles_5m.append(Candle(ts_5m, p_sub, p_sub + 10, swing_low_p, swing_low_p + 15, 110.0))

    for i in range(3):
        ts_5m += 300000
        p_reb = swing_low_p + 20.0 + (i * 20.0)
        candles_5m.append(Candle(ts_5m, p_reb - 10, p_reb + 20, p_reb - 10, p_reb, 80.0))

    ts_5m += 300000
    quiebre_close = swing_high_p + 60.0
    candles_5m.append(Candle(ts_5m, swing_high_p - 10, quiebre_close + 20, swing_high_p - 15, quiebre_close, 350.0))

    return candles_4h, candles_5m

def descargar_velas_en_vivo(symbol: str = "BTC/USDT", exchange_id: str = "binance"):
    import ccxt
    ex_cls = getattr(ccxt, exchange_id)
    exchange = ex_cls({"enableRateLimit": True, "timeout": 10000})
    print(f"[CONEXION CCXT]: Conectando a {exchange_id.upper()} para {symbol}...")
    ohlcv_4h = exchange.fetch_ohlcv(symbol, timeframe="4h", limit=50)
    ohlcv_5m = exchange.fetch_ohlcv(symbol, timeframe="5m", limit=50)

    c_4h = [Candle(int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])) for r in ohlcv_4h]
    c_5m = [Candle(int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])) for r in ohlcv_5m]
    return c_4h, c_5m

def imprimir_setup(setup: SetupCHoCHRSI, capital_usdt: float, apalancamiento: float):
    print("=" * 96)
    print(f" ESTRATEGIA CUANTITATIVA: CHoCH 5m + DIVERGENCIA RSI 4H (PINE SCRIPT v6 EN PYTHON)")
    print("=" * 96)

    print("\n[ESTADO DE LOS FILTROS MACRO Y MICRO]")
    print("-" * 96)
    print(f"  * Divergencia RSI 4H Activa: {'SI (Confirmada)' if setup.divergencia_4h_activa else 'NO'}")
    print(f"  * Valor RSI 4H Actual      : {setup.rsi_4h_valor:.2f} (Zona de absorcion < 50)")
    print(f"  * Quiebre CHoCH 5m         : {'CONFIRMADO CON CUERPO' if setup.confirmado else 'PENDIENTE'}")
    print(f"  * Ultimo Swing High Roto   : ${setup.swing_high_roto:,.2f}")
    print(f"  * Cierre de la Vela 5m     : ${setup.precio_quiebre_choch:,.2f}")

    if not setup.confirmado:
        print("\n[INFO]: No se cumplen todas las condiciones simultaneas en este momento.")
        print("        El sistema mantiene el capital protegido fuera de mercado.")
        print("=" * 96 + "\n")
        return

    print("\n" + "=" * 96)
    print("                 COMPARATIVA CRITICA DE METODOS DE ENTRADA")
    print("=" * 96)

    # 1. METODO DEL INDICADOR ORIGINAL
    dist_sl_clasico = setup.entrada_mercado_clasica - setup.stop_loss_clasico
    pct_sl_clasico = (dist_sl_clasico / setup.entrada_mercado_clasica) * 100
    perdida_clasica = (capital_usdt * apalancamiento) * (pct_sl_clasico / 100.0)

    print("\n[METODO 1: INDICADOR PINE SCRIPT ORIGINAL (ENTRADA A MERCADO EN EL CIERRE)]")
    print("-" * 96)
    print(f"  * Precio de Entrada (Close) : ${setup.entrada_mercado_clasica:,.2f} (Compras en el pico del impulso)")
    print(f"  * Stop Loss Tecnico         : ${setup.stop_loss_clasico:,.2f} (Distancia: -{pct_sl_clasico:.2f}%)")
    print(f"  * Take Profit (1:2.0)       : ${setup.take_profit_clasico:,.2f}")
    print(f"  * Perdida Si Toca el Stop   : -${perdida_clasica:,.2f} USDT")
    print(f"  * Problema Psicologico      : Si el precio hace un retroceso normal del 0.8%, tu posicion entra")
    print(f"                                de inmediato en perdida de -${perdida_clasica * 0.6:.2f} USDT y te asustas.")

    # 2. METODO DE ESCALAMIENTO INSTITUCIONAL EN EL RETROCESO
    plan = setup.plan_escalamiento
    print("\n[METODO 2: ESCALAMIENTO INSTITUCIONAL 30/30/40 (EN EL RETROCESO AL ORDER BLOCK)]")
    print("-" * 96)
    print("  En lugar de comprar arriba, el quiebre de 5m ACTIVA 3 ordenes limites en el retroceso:")
    print(f"{'TRAMO':<8} | {'%':<5} | {'MARGEN':<10} | {'PRECIO LIMITE':<15} | {'BTC':<9} | {'ZONA DE DEMANDA'}")
    print("-" * 96)
    for t in plan.tramos:
        print(f"Tramo {t.numero_tramo:<2} | {t.porcentaje_capital*100:>2.0f}% | ${t.margen_usdt:<9,.2f} | ${t.precio_orden:<14,.2f} | {t.cantidad_activo:<8.4f} | {t.tipo_zona}")

    print("-" * 96)
    print(f"  >>> PRECIO PROMEDIO RESULTANTE : ${plan.precio_promedio_proyectado:,.2f}")
    print(f"      (Mejora tu entrada en ${setup.entrada_mercado_clasica - plan.precio_promedio_proyectado:,.2f} respecto a entrar a mercado)")
    print(f"  * STOP LOSS DEFENSIVO          : ${plan.stop_loss_inmutable:,.2f}")
    print(f"  * PERDIDA MAXIMA EN STOP LOSS  : -${plan.perdida_maxima_usdt:,.2f} USDT (Solo el {plan.perdida_maxima_pct:.2f}% de tu margen)")
    print(f"  * TAKE PROFIT 1 (50%)          : ${plan.take_profit_1:,.2f} (+${plan.ganancia_proyectada_tp1:,.2f} USDT)")
    print(f"  * TAKE PROFIT 2 (50%)          : ${plan.take_profit_2:,.2f} (+${plan.ganancia_proyectada_tp2:,.2f} USDT)")
    print(f"  * RATIO RIESGO / BENEFICIO REAL: 1 : {plan.ratio_riesgo_beneficio:.1f}")

    print("\n" + "=" * 96)
    print("                       CONCLUSION OPERATIVA INMEDIATA")
    print("=" * 96)
    print("  El indicador de TradingView te avisa: 'HUBO CHoCH 5m + DIV 4H'.")
    print("  Tu accion inmediata NO es comprar con un boton a mercado.")
    print(f"  Tu accion es colocar tus 3 ordenes limites pasivas entre ${plan.tramos[0].precio_orden:,.2f} y ${plan.tramos[2].precio_orden:,.2f}.")
    print("=" * 96 + "\n")

def main():
    cap = 500.0
    lev = 3.0
    es_en_vivo = "--live" in sys.argv

    args_limpios = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args_limpios) > 0:
        try:
            cap = float(args_limpios[0])
        except ValueError:
            cap = 500.0
    if len(args_limpios) > 1:
        try:
            lev = float(args_limpios[1])
        except ValueError:
            lev = 3.0

    strat = ChochRsiStrategy()

    if es_en_vivo:
        try:
            c_4h, c_5m = descargar_velas_en_vivo()
        except Exception as e:
            print(f"[ERROR AL CONECTAR EN VIVO]: {e}")
            print("[INFO]: Ejecutando en modo de simulacion demostrativa...")
            c_4h, c_5m = simular_mercado_choch_div()
    else:
        c_4h, c_5m = simular_mercado_choch_div()

    setup = strat.evaluar_estrategia(c_4h, c_5m, capital_usdt=cap, apalancamiento=lev)
    imprimir_setup(setup, cap, lev)

if __name__ == "__main__":
    main()
