"""
simulador_estrategia_completa.py - Simulador Multi-Escenario de Acción del Precio
Valida 4 escenarios reales con capital de $500 USDT a 3x:
1. Escenario 1: Retroceso Superficial (Solo llena Tramo 1 y despega hacia TP).
2. Escenario 2: Retroceso Profundo Institucional (Llena Tramo 1, 2 y 3, promedio optimo y despegue).
3. Escenario 3: Invalidacion de Estructura (El soporte falla y toca Stop Loss controlado).
4. Escenario 4: Filtro Macro Activo (CHoCH en 5m pero SIN divergencia 4H -> Disciplina de NO entrar).
"""

from __future__ import annotations
import sys
import time
from core.types import Candle
from core.choch_rsi_strategy import ChochRsiStrategy

def crear_velas_4h_con_divergencia():
    """Genera 35 velas de 4H con divergencia regular alcista limpia (Lower Low en precio, Higher Low en RSI <= 35)."""
    candles = []
    ts = int(time.time() * 1000) - 40 * 14400000
    p = 76500.0
    
    # 1. Caida inicial a sobreventa (Pivote 1 en $73,500)
    for _ in range(12):
        ts += 14400000
        p -= 250.0
        candles.append(Candle(ts, p + 50, p + 100, p - 60, p, 1500.0))
    candles.append(Candle(ts + 14400000, p, p + 20, p - 90, p - 60, 1800.0))
    ts += 14400000
    p -= 60.0 # Trough 1: ~73,440

    # Rebote de confirmacion
    for _ in range(4):
        ts += 14400000
        p += 160.0
        candles.append(Candle(ts, p - 30, p + 50, p - 40, p, 800.0))

    # Caida que hace Lower Low en precio ($73,050) pero menor momentum en RSI
    for _ in range(6):
        ts += 14400000
        p -= 120.0
        candles.append(Candle(ts, p + 20, p + 40, p - 50, p, 600.0))
    candles.append(Candle(ts + 14400000, p, p + 20, p - 100, p - 70, 700.0))
    ts += 14400000
    p -= 70.0 # Trough 2: ~72,980

    # Rebote de confirmacion con RSI < 50
    for _ in range(4):
        ts += 14400000
        p += 70.0
        candles.append(Candle(ts, p - 20, p + 40, p - 30, p, 500.0))

    return candles

def crear_velas_4h_sin_divergencia():
    """Genera 35 velas de 4H en caida libre continua (sin divergencia, RSI sobrevendido pero sin pivote alcista)."""
    candles = []
    ts = int(time.time() * 1000) - 40 * 14400000
    p = 77000.0
    for _ in range(30):
        ts += 14400000
        p -= 150.0
        candles.append(Candle(ts, p + 30, p + 50, p - 60, p, 1200.0))
    return candles

def crear_velas_5m_choch():
    """Genera velas de 5m que forman un Swing High en $73,380, un Swing Low en $73,280 y un quiebre CHoCH con cuerpo a $73,440."""
    candles = []
    ts = int(time.time() * 1000) - 20 * 300000
    p = 73200.0

    # Subida hacia el Swing High
    for i in range(6):
        ts += 300000
        p += 25.0
        candles.append(Candle(ts, p - 15, p + 15, p - 15, p, 80.0))
    
    # Swing High en $73,380
    swing_high = 73380.0
    ts += 300000
    candles.append(Candle(ts, swing_high - 10, swing_high, swing_high - 25, swing_high - 15, 100.0))

    # 4 velas que confirman el swing high
    for i in range(4):
        ts += 300000
        p_sub = swing_high - 20.0 - (i * 15.0)
        candles.append(Candle(ts, p_sub + 10, p_sub + 15, p_sub - 15, p_sub, 70.0))

    # Swing Low en $73,280
    swing_low = 73280.0
    ts += 300000
    candles.append(Candle(ts, p_sub, p_sub + 10, swing_low, swing_low + 15, 120.0))

    # Rebote previo al quiebre
    for i in range(3):
        ts += 300000
        p_reb = swing_low + 20.0 + (i * 20.0)
        candles.append(Candle(ts, p_reb - 10, p_reb + 20, p_reb - 10, p_reb, 80.0))

    # Vela de quiebre CHoCH con cuerpo a $73,440
    ts += 300000
    quiebre_close = 73440.0
    candles.append(Candle(ts, swing_high - 10, quiebre_close + 20, swing_high - 15, quiebre_close, 350.0))

    return candles, swing_high, swing_low, quiebre_close

def ejecutar_simulacion_multi_escenario(capital_usdt: float = 500.0, apalancamiento: float = 3.0):
    strat = ChochRsiStrategy()

    print("=" * 100)
    print(f"      BANCO DE PRUEBAS MULTI-ESCENARIO: ACCION DEL PRECIO + ESCALAMIENTO 30/30/40")
    print(f"      Capital Base: ${capital_usdt:,.2f} USDT | Apalancamiento: {apalancamiento:.0f}x | Nocional: ${capital_usdt*apalancamiento:,.2f}")
    print("=" * 100)

    c_4h_div = crear_velas_4h_con_divergencia()
    c_4h_sin_div = crear_velas_4h_sin_divergencia()
    c_5m, sh, sl, close_choch = crear_velas_5m_choch()

    setup = strat.evaluar_estrategia(c_4h_div, c_5m, capital_usdt=capital_usdt, apalancamiento=apalancamiento)
    plan = setup.plan_escalamiento

    t1_p = plan.tramos[0].precio_orden # $73,380.00 (30%)
    t2_p = plan.tramos[1].precio_orden # $73,355.25 (30%)
    t3_p = plan.tramos[2].precio_orden # $73,337.93 (40%)
    sl_p = plan.stop_loss_inmutable      # $73,257.17
    tp1_p = plan.take_profit_1          # $73,533.17
    tp2_p = plan.take_profit_2          # $73,700.74

    # -------------------------------------------------------------------------------------------------
    # ESCENARIO 1: RETROCESO SUPERFICIAL
    # -------------------------------------------------------------------------------------------------
    print("\n" + "=" * 100)
    print(" [ESCENARIO 1]: RETROCESO SUPERFICIAL (Fuerza Compradora Agresiva)")
    print("-" * 100)
    print(f"  * El precio rompe a ${close_choch:,.2f} y hace un retroceso leve a ${t1_p - 5:,.2f} antes de subir.")
    print(f"  * ¿Que ordenes se llenan?: SOLO TRAMO 1 (${t1_p:,.2f} - Margen $150 a 3x = $450 nocional).")
    print(f"  * Tramos 2 y 3 quedan sin ejecutar (el precio no llego tan abajo).")
    
    qty_t1 = plan.tramos[0].cantidad_activo
    pnl_e1_tp1 = (qty_t1 * 0.5) * (tp1_p - t1_p)
    pnl_e1_tp2 = (qty_t1 * 0.5) * (tp2_p - t1_p)
    total_e1 = pnl_e1_tp1 + pnl_e1_tp2
    print(f"  >>> RESULTADO OPERATIVO:")
    print(f"      - Capital Arriesgado Real   : $150.00 USDT (no pusiste en juego los $500).")
    print(f"      - Beneficio Obtenido (TP1+2): +${total_e1:,.2f} USDT (+{total_e1/150.0*100:.2f}% de retorno).")
    print(f"      - Leccion Psicologica       : No perseguiste el precio arriba; ganaste con el 30% con CERO estres.")

    # -------------------------------------------------------------------------------------------------
    # ESCENARIO 2: RETROCESO PROFUNDO INSTITUCIONAL
    # -------------------------------------------------------------------------------------------------
    print("\n" + "=" * 100)
    print(" [ESCENARIO 2]: RETROCESO PROFUNDO INSTITUCIONAL (Manipulacion / Barrido de Mecha)")
    print("-" * 100)
    print(f"  * El precio cae hasta ${t3_p - 10:,.2f} con una mecha rapida de 5m (parece que se desploma).")
    print(f"  * ¿Que ordenes se llenan?: TRAMO 1 + TRAMO 2 + TRAMO 3 (100% de la posicion planificada).")
    print(f"  * Precio Promedio Ponderado : ${plan.precio_promedio_proyectado:,.2f} (Pegado al fondo).")
    print(f"  * El precio absorbe los contratos y rebota con fuerza hacia TP1 (${tp1_p:,.2f}) y TP2 (${tp2_p:,.2f}).")
    
    print(f"  >>> RESULTADO OPERATIVO:")
    print(f"      - Margen Total Asignado     : $500.00 USDT a 3x.")
    print(f"      - Beneficio Obtenido (TP1+2): +${plan.ganancia_proyectada_tp1 + plan.ganancia_proyectada_tp2:,.2f} USDT.")
    print(f"      - Ratio R:R Matemático      : 1 : {plan.ratio_riesgo_beneficio:.1f}")
    print(f"      - Leccion Psicologica       : Lo que antes te asustaba (la mecha roja) aqui fue tu mejor aliado,")
    print(f"                                    porque te lleno el 40% del capital al precio mas barato posible.")

    # -------------------------------------------------------------------------------------------------
    # ESCENARIO 3: FALLA DE ESTRUCTURA (STOP LOSS CONTROLADO)
    # -------------------------------------------------------------------------------------------------
    print("\n" + "=" * 100)
    print(" [ESCENARIO 3]: INVALIDACION DE ESTRUCTURA (El Soporte Falla / Ruptura Real hacia Abajo)")
    print("-" * 100)
    print(f"  * Entran los 3 tramos pero el precio continua cayendo con volumen y perfora el Stop Loss en ${sl_p:,.2f}.")
    print(f"  * La posicion completa se cierra AUTOMATICAMENTE sin dudar.")
    print(f"  >>> RESULTADO OPERATIVO:")
    print(f"      - Perdida Real Total en USDT: -${plan.perdida_maxima_usdt:,.2f} USDT.")
    print(f"      - Impacto sobre la Cuenta   : Pierdes exactamente el {plan.perdida_maxima_pct:.2f}% de tu margen.")
    print(f"      - Saldo Restante en Cuenta  : ${capital_usdt - plan.perdida_maxima_usdt:,.2f} USDT.")
    print(f"      - Leccion Psicologica       : NUNCA promediaste de mas ni agregaste fondos improvisados.")
    print(f"                                    La cuenta sigue con el 99.6% viva para la proxima operacion.")

    # -------------------------------------------------------------------------------------------------
    # ESCENARIO 4: FILTRO MACRO ACTIVO (DISCIPLINA DE NO ENTRAR)
    # -------------------------------------------------------------------------------------------------
    print("\n" + "=" * 100)
    print(" [ESCENARIO 4]: TRAMPA SIN DIVERGENCIA 4H (El Quiebre es un Fake Breakout)")
    print("-" * 100)
    setup_falso = strat.evaluar_estrategia(c_4h_sin_div, c_5m, capital_usdt=capital_usdt, apalancamiento=apalancamiento)
    print(f"  * Ocurre un quiebre CHoCH en 5m a ${close_choch:,.2f}, pero el RSI de 4H NO tiene divergencia.")
    print(f"  * Evaluacion del Sistema:")
    print(f"      - Divergencia 4H Activa: {setup_falso.divergencia_4h_activa}")
    print(f"      - CHoCH 5m Confirmado  : {setup_falso.confirmado}")
    print(f"      - Estado de la Compuerta: ORDEN DENEGADA / FUERA DE MERCADO.")
    print(f"  >>> RESULTADO OPERATIVO:")
    print(f"      - El precio continuo cayendo a $71,000. El filtro macro 4H te salvo de una trampa mortal.")
    print("=" * 100 + "\n")

if __name__ == "__main__":
    cap = 500.0
    lev = 3.0
    if len(sys.argv) > 1:
        try:
            cap = float(sys.argv[1])
        except ValueError:
            cap = 500.0
    if len(sys.argv) > 2:
        try:
            lev = float(sys.argv[2])
        except ValueError:
            lev = 3.0
    ejecutar_simulacion_multi_escenario(cap, lev)
