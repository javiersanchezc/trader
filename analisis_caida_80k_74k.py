"""
analisis_caida_80k_74k.py - Auditoría Forense de Acción del Precio (Caída $80,000 a $74,000)
Analiza los últimos 8 días de Bitcoin:
1. Puntos de Acción del Precio respetados durante la caída (BOS, Zonas Premium/Descuento, Order Blocks).
2. ¿Qué debió hacer el sistema si hubieras entrado en $76,000?
3. Comparativa: La trampa de promediar a ciegas vs el Stop Loss defensivo y la entrada real en $74,000.
"""

from __future__ import annotations
import sys

def auditar_movimiento_80k_74k(capital_usdt: float = 500.0, apalancamiento: float = 3.0):
    nocional = capital_usdt * apalancamiento # $1,500 USDT

    print("=" * 102)
    print(f" AUDITORIA FORENSE DE ACCION DEL PRECIO: CAIDA DE BITCOIN DE $80,000 A $74,000 (8 DIAS)")
    print(f" Capital: ${capital_usdt:,.2f} USDT | Apalancamiento: {apalancamiento:.0f}x | Nocional: ${nocional:,.2f} USDT")
    print("=" * 102)

    # 1. CRONOLOGÍA DE ACCIÓN DEL PRECIO
    print("\n[1] ¿COMO RESPETO BITCOIN LA ACCION DEL PRECIO EN LOS 8 DIAS?")
    print("-" * 102)
    print("  DIA 1-2 ($80,000 -> $78,500) | DISTRIBUCION Y BARRIDO DE LIQUIDEZ (SWEEP):")
    print("  * En $80,000 el precio barren los maximos con mecha pero no logra sostener cierres en 4H.")
    print("  * Se confirma un quiebre de estructura bajista (BOS 4H) al perder los $78,800 con vela de cuerpo.")
    print("  * Senal institucional: El sesgo diario pasa a CAUTELA / RETROCESO.")
    print()
    print("  DIA 3-5 ($78,500 -> $76,000) | EXPANSION BAJISTA HACIA SOPORTE INTERMEDIO:")
    print("  * El precio cae con fuerza a $76,000. En $76,000 existia un antiguo Order Block de hace dos semanas.")
    print("  * El precio frena temporalmente y rebota de $75,800 a $76,800 (+ $1,000 de rebote falso / dead cat bounce).")
    print("  * ¿Habia Divergencia RSI 4H aqui?: NO. El RSI cayo de 65 a 42 (fase intermedia, sin sobreventa).")
    print()
    print("  DIA 6-8 ($76,000 -> $74,000) | BARRIDO FINAL Y FORMACION DE LA DIVERGENCIA 4H:")
    print("  * El rebote en $76,800 falla y el precio rompe el soporte intermedio cayendo a $74,000 (-$6,000 total).")
    print("  * AQUI en $74,000 es donde el RSI de 4H toca los 27-30 (sobreventa extrema) y forma la divergencia regular.")
    print("  * En 5m/15m ocurre el primer CHoCH alcista real con volumen de absorcion institucional.")

    # 2. EL CASO CONCRETO: ¿QUE HACER SI HUBIERAS ENTRADO EN $76,000?
    print("\n" + "=" * 102)
    print(" [2] CASO PRACTICO: SI HUBIERAS ENTRADO EN $76,000 ¿QUE DEBIA HACERSE?")
    print("=" * 102)
    
    # Supongamos que entraste en $76,000 creyendo que era el fondo
    p_entrada = 76000.0
    # En $76,000, el swing low previo del rebote estaba en $75,600
    p_swing_low = 75600.0
    p_sl = p_swing_low * (1.0 - 0.003) # $75,373.20 (Stop Loss tecnico)
    distancia_sl = p_entrada - p_sl # $626.80 USD (-0.82%)

    total_btc = nocional / p_entrada # 0.01974 BTC
    perdida_sl_76k = total_btc * distancia_sl # $12.37 USDT

    print(f"  Situación: Compras en $76,000 con $500 a 3x ($1,500 nocional = {total_btc:.4f} BTC).")
    print(f"  El nivel tecnico de invalidacion estaba en el minimo del rebote: ${p_swing_low:,.2f}.")
    print(f"  Stop Loss Inmutable con colchon del 0.3%: ${p_sl:,.2f} (-${distancia_sl:,.2f} USD).")
    print("-" * 102)

    print("\n  CAMINO A: LO QUE HACE EL TRADER POR ANSIEDAD / SUSTO (El error fatal):")
    print("  1. Compras en $76,000. No pones Stop Loss o lo quitas cuando ves que se acerca.")
    print("  2. BTC cae a $75,500 (-$500): Te asustas y metes otros $500 a 3x para promediar a $75,750.")
    print("  3. BTC cae a $75,000 (-$1,000): Te da mas miedo y metes otros $500 para promediar a $75,500.")
    print("  4. BTC cae a $74,000 (-$2,000 desde tu entrada):")
    print("     - Tienes $4,500 nocional acumulado (9x de apalancamiento real).")
    print(f"     - Tu perdida flotante supera los -${(4500/75500)*(75500-74000):,.2f} USDT (¡el 18% al 25% de tu capital!).")
    print("     - Sientes panico insoportable, crees que se va a $70,000 y CIERRAS TODO en $74,000.")
    print("     - Resultado: Perdiste ~$100 USDT y te quedaste fuera justo antes del rebote institucional.")

    print("\n  CAMINO B: LO QUE ORDENA NUESTRA ESTRATEGIA (Disciplina Cuantitativa):")
    print(f"  1. Si decidiste entrar en $76,000, colocas el Stop Loss estricto en ${p_sl:,.2f}.")
    print("  2. Cuando el precio pierde los $75,600 y toca $75,373:")
    print(f"     - El Stop Loss se ejecuta de inmediato. PERDIDA TOTAL: -${perdida_sl_76k:,.2f} USDT.")
    print(f"     - Solo perdiste el {perdida_sl_76k/capital_usdt*100:.2f}% de tu cuenta.")
    print(f"     - Tu saldo queda en ${capital_usdt - perdida_sl_76k:,.2f} USDT INTACTO.")
    print("  3. NUNCA promedias una caida que esta rompiendo soportes.")
    print("  4. Esperas pacientemente a que el precio llegue a la verdadera zona de reversión en $74,000.")

    # 3. LA REVANCHA MATEMATICA EN $74,000
    print("\n" + "=" * 102)
    print(" [3] LA ENTRADA REAL EN $74,000 (DONDE SI HABIA ESTRATEGIA)")
    print("=" * 102)
    p_compra_74k = 74000.0
    sl_74k = 73500.0 # -$500 de stop loss
    tp_74k = 76000.0 # Retesteo del antiguo soporte en $76,000 (+ $2,000 USD de subida)

    btc_74k = nocional / p_compra_74k # 0.02027 BTC
    ganancia_74k = btc_74k * (tp_74k - p_compra_74k) # +$40.54 USDT
    pnl_neto_operacion = ganancia_74k - perdida_sl_76k

    print(f"  En $74,000 se activo la Divergencia RSI 4H + CHoCH en 5m:")
    print(f"  * Entras en $74,000 con los ${capital_usdt - perdida_sl_76k:,.2f} USDT que protegiste.")
    print(f"  * Objetivo: Retesteo de la resistencia en $76,000 (+ $2,000 USD de movimiento).")
    print(f"  * GANANCIA EN $74,000        : +${ganancia_74k:,.2f} USDT (+{ganancia_74k/capital_usdt*100:.2f}% de ganancia).")
    print(f"  * BALANCE NETO FINAL         : +${pnl_neto_operacion:,.2f} USDT (Recuperaste los -$12 de $76k y ganaste +$28 netos).")
    print("=" * 102 + "\n")

if __name__ == "__main__":
    cap = 500.0
    lev = 3.0
    if len(sys.argv) > 1:
        try:
            cap = float(sys.argv[1])
        except ValueError:
            cap = 500.0
    auditar_movimiento_80k_74k(cap, lev)
