"""
vision_mercado.py - Tablero Ejecutivo de Acción del Precio Multi-Temporal
Entrega una visión limpia y accionable en 3 horizontes:
- Largo Plazo (1D/1W): Hacia dónde va la marea macro (Sesgo Direccional)
- Mediano Plazo (4H/1H): Dónde estamos dentro del rango (Zona Barata vs Cara / Descuento vs Premium)
- Corto Plazo (15M/5M): Cuándo y cómo disparar (Entrada, Stop Loss, Take Profits y Ratio R:R)
"""

from __future__ import annotations
import sys
import time
from core.types import Candle
from core.multi_timeframe import PriceActionEngine

def generar_datos_mercado_actuales(precio_spot: float = 74850.0):
    candles_daily = []
    base_d = 62000.0
    for i in range(25):
        ts = int(time.time() * 1000) - (25 - i) * 86400000
        p = base_d + (i * 550.0)
        candles_daily.append(Candle(ts, p, p + 800, p - 400, p + 500, 2500.0))

    candles_h4 = []
    base_h4 = 72800.0
    for i in range(20):
        ts = int(time.time() * 1000) - (20 - i) * 14400000
        p = base_h4 + (i * 110.0)
        candles_h4.append(Candle(ts, p, p + 250, p - 180, p + 80, 800.0))

    candles_m15 = []
    base_m15 = precio_spot - 300.0
    for i in range(15):
        ts = int(time.time() * 1000) - (15 - i) * 900000
        p = base_m15 + (i * 20.0)
        candles_m15.append(Candle(ts, p, p + 60, p - 50, p + 15, 120.0))

    return candles_daily, candles_h4, candles_m15

def mostrar_tablero_accion_precio(precio_spot: float = 74850.0):
    engine = PriceActionEngine(symbol="BTC/USDT")
    daily, h4, m15 = generar_datos_mercado_actuales(precio_spot)
    
    hoja = engine.generar_hoja_de_ruta(daily, h4, m15, precio_spot)
    largo = hoja.largo_plazo
    mediano = hoja.mediano_plazo
    corto = hoja.corto_plazo

    print("=" * 95)
    print(f"       HOJA DE RUTA LIMPIA DE ACCION DEL PRECIO - {hoja.simbolo} (SPOT: ${hoja.precio_spot:,.2f})")
    print("=" * 95)

    # 1. VISION LARGO PLAZO
    print("\n[1] VISION LARGO PLAZO (1D / 1W) - SESGO DIRECCIONAL RECTOR")
    print("-" * 95)
    print(f"  * Tendencia Estructural    : {largo.tendencia_macro}")
    print(f"  * Sesgo Operativo Mayor    : {largo.sesgo_direccional}")
    print(f"  * Techo Macro (Resistencia): ${largo.resistencia_clave_macro:,.2f}")
    print(f"  * Suelo Macro (Soporte)    : ${largo.soporte_clave_macro:,.2f}")
    print(f"  * Invalidacion del Sesgo   : ${largo.nivel_invalidacion_macro:,.2f} (Si se pierde, cambia la tesis)")
    print(f"  * Resumen Limpio           : {largo.racional_limpio}")

    # 2. VISION MEDIANO PLAZO
    print("\n[2] VISION MEDIANO PLAZO (4H / 1H) - MAPA DEL RANGO Y UBICACION")
    print("-" * 95)
    print(f"  * Estructura del Rango     : {mediano.estructura_mercado}")
    print(f"  * Rango de Negociacion     : [Minimo: ${mediano.rango_minimo:,.2f}  <--->  Maximo: ${mediano.rango_maximo:,.2f}]")
    print(f"  * Nivel 50% (Equilibrio)   : ${mediano.precio_equilibrio:,.2f}")
    print(f"  * Ubicacion del Precio     : {mediano.ubicacion_actual}")
    print(f"  * Zona de Demanda (Compra) : ${mediano.zona_demanda_h4[0]:,.2f} - ${mediano.zona_demanda_h4[1]:,.2f}")
    print(f"  * Zona de Oferta (Venta)   : ${mediano.zona_oferta_h4[0]:,.2f} - ${mediano.zona_oferta_h4[1]:,.2f}")
    print(f"  * Regla Clave              : NUNCA comprar en Zona Premium ni vender en Zona Descuento.")

    # 3. VISION CORTO PLAZO
    print("\n[3] VISION CORTO PLAZO (15M / 5M) - GATILLO DE ENTRADA Y GESTION")
    print("-" * 95)
    print(f"  * Estado del Gatillo       : {corto.estado_gatillo}")
    print(f"  * Patron Identificado      : {corto.tipo_patron}")
    print(f"  * Precio de Entrada (EP)   : ${corto.precio_entrada:,.2f}")
    print(f"  * Stop Loss Tecnico (SL)   : ${corto.stop_loss_tecnico:,.2f}")
    print(f"  * Objetivo 1 (TP1)         : ${corto.take_profit_1:,.2f}  (Cierre del 50% de posicion)")
    print(f"  * Objetivo 2 (TP2)         : ${corto.take_profit_2:,.2f}  (Dejar correr tendencia)")
    print(f"  * Ratio Riesgo / Beneficio : 1 : {corto.ratio_riesgo_beneficio:.1f}")
    print(f"  * Detalle de Entrada       : {corto.racional_limpio}")

    # 4. PLAN DE ACCION EJECUTIVO
    print("\n" + "=" * 95)
    print("                      PLAN DE ACCION EJECUTIVO INMEDIATO")
    print("=" * 95)
    print(f"  >>> {hoja.plan_de_accion_ejecutivo}")
    print("=" * 95 + "\n")

if __name__ == "__main__":
    precio = 74850.0
    if len(sys.argv) > 1:
        try:
            precio = float(sys.argv[1])
        except ValueError:
            precio = 74850.0
    mostrar_tablero_accion_precio(precio)
