"""
simulador_volatilidad_intradia.py - Simulación con Rangos Reales de Bitcoin ($1,000 a $2,000 USD)
Demuestra el comportamiento del Escalamiento 30/30/40 ante oscilaciones intradía reales:
- Retroceso de $1,200 USD hacia zona de demanda 4H.
- Quiebre CHoCH 5m de $400 USD.
- Escalamiento de 3 tramos separados por $150 - $200 USD.
- Expansión intradía a favor de $1,500 a $2,000 USD.
- Comparativa del trader que promedia por pánico vs trader que escala por estrategia.
"""

from __future__ import annotations
import sys

def simular_intradia_real(capital_usdt: float = 500.0, apalancamiento: float = 3.0):
    nocional_total = capital_usdt * apalancamiento # $1,500 USDT

    print("=" * 100)
    print(f" SIMULACION INTRADIA REAL DE BITCOIN (DESPLAZAMIENTO DE $1,500 A $2,000 USD)")
    print(f" Capital: ${capital_usdt:,.2f} USDT | Apalancamiento: {apalancamiento:.0f}x | Nocional Total: ${nocional_total:,.2f} USDT")
    print("=" * 100)

    # Contexto Intradía Real
    p_techo_4h = 75200.0
    p_suelo_4h = 73500.0 # Caída previa de $1,700 USD (Divergencia RSI 4H en sobreventa 28)
    
    # En $73,500 nace el impulso de rebote en 5m
    swing_low_origen = 73500.0
    swing_high_roto  = 73950.0 # Techo de 5m
    choch_close      = 74200.0 # Vela de quiebre (+ $700 de impulso total)

    # Amplitud del impulso de quiebre
    impulso_total = choch_close - swing_low_origen # $700 USD

    # Niveles de Acción del Precio para los 3 Tramos
    # Tramo 1 (30%): Retesteo del swing high roto ($73,950) -> retroceso de $250
    t1_precio = swing_high_roto # $73,950
    # Tramo 2 (30%): Nivel de equilibrio 50% del impulso ($73,850) -> retroceso de $350
    t2_precio = swing_low_origen + (impulso_total * 0.50) # $73,850
    # Tramo 3 (40%): Mecha profunda / OTE 75% ($73,675) -> retroceso de $525
    t3_precio = swing_low_origen + (impulso_total * 0.25) # $73,675
    # Stop Loss: 0.3% por debajo del mínimo de origen ($73,500 - $220)
    stop_loss = swing_low_origen * (1.0 - 0.003) # $73,279.50

    # Objetivos Intradía con desplazamiento real (+ $1,500 y + $2,000)
    tp1_intradia = 74800.0 # + $1,300 desde el suelo (Resistencia media intradía)
    tp2_intradia = 75500.0 # + $2,000 desde el suelo (Máximo previo de 4H)

    # Cantidades de Bitcoin por tramo
    nocional_t1 = nocional_total * 0.30 # $450
    nocional_t2 = nocional_total * 0.30 # $450
    nocional_t3 = nocional_total * 0.40 # $600

    btc_t1 = nocional_t1 / t1_precio # ~0.00608 BTC
    btc_t2 = nocional_t2 / t2_precio # ~0.00609 BTC
    btc_t3 = nocional_t3 / t3_precio # ~0.00814 BTC
    total_btc = btc_t1 + btc_t2 + btc_t3 # ~0.02031 BTC

    # Precio promedio ponderado
    coste_total = (t1_precio * btc_t1) + (t2_precio * btc_t2) + (t3_precio * btc_t3)
    precio_promedio = coste_total / total_btc # ~ $73,809.50

    print("\n[MAPA DE LA ESTRUCTURA INTRADIA]")
    print("-" * 100)
    print(f"  * Rango de Volatilidad Intradía : Caída de -$1,700 USD (de $75,200 a $73,500)")
    print(f"  * Filtro Macro 4H               : Divergencia Regular Alcista Confirmada en $73,500")
    print(f"  * Impulso CHoCH en 5m           : Subida de +$700 USD (hasta $74,200)")
    print(f"  * El Error Retail Común         : Comprar todo en $74,200 (en el pico del rebote de 5m)")

    print("\n[PLAN INSTITUCIONAL: ESCALAMIENTO 30/30/40 EN EL RETROCESO]")
    print("-" * 100)
    print(f"{'TRAMO':<8} | {'%':<5} | {'MARGEN':<10} | {'PRECIO LIMITE':<15} | {'RETROCESO':<14} | {'ZONA INSTITUCIONAL'}")
    print("-" * 100)
    print(f"Tramo 1  | 30% | $150.00    | ${t1_precio:<14,.2f} | -$250 USD      | Retesteo Techo 5m Roto ($73,950)")
    print(f"Tramo 2  | 30% | $150.00    | ${t2_precio:<14,.2f} | -$350 USD      | Equilibrio 50% Fibo ($73,850)")
    print(f"Tramo 3  | 40% | $200.00    | ${t3_precio:<14,.2f} | -$525 USD      | Mecha de Manipulacion ($73,675)")
    print("-" * 100)
    print(f"  >>> PRECIO PROMEDIO FINAL (Llenados los 3): ${precio_promedio:,.2f}")
    print(f"      (Mejora de entrada: Ahorraste ${choch_close - precio_promedio:,.2f} USD por Bitcoin frente a comprar arriba)")

    # Cálculo de Ganancias y Pérdidas
    perdida_sl_total = total_btc * (precio_promedio - stop_loss)
    ganancia_tp1 = (total_btc * 0.5) * (tp1_intradia - precio_promedio)
    ganancia_tp2 = (total_btc * 0.5) * (tp2_intradia - precio_promedio)
    ganancia_total = ganancia_tp1 + ganancia_tp2
    ratio_rr = ganancia_total / perdida_sl_total

    print("\n[NUMEROS REALES EN UN MOVIMIENTO INTRADIA DE $1,500 A $2,000 USD]")
    print("-" * 100)
    print(f"  * Si toca STOP LOSS en ${stop_loss:,.2f}:")
    print(f"    - Distancia en precio     : -${precio_promedio - stop_loss:,.2f} USD (-0.72% del precio)")
    print(f"    - PERDIDA TOTAL REAL      : -${perdida_sl_total:,.2f} USDT (Solo el {perdida_sl_total/capital_usdt*100:.2f}% de tus $500)")
    print(f"    - Saldo restante protegido: ${capital_usdt - perdida_sl_total:,.2f} USDT")
    print()
    print(f"  * Si BTC hace el movimiento intradia alcista esperado:")
    print(f"    - TP1 en ${tp1_intradia:,.2f} (+${tp1_intradia - precio_promedio:,.2f} USD) : Cierras 50% -> Ganas +${ganancia_tp1:,.2f} USDT")
    print(f"    - TP2 en ${tp2_intradia:,.2f} (+${tp2_intradia - precio_promedio:,.2f} USD) : Cierras 50% -> Ganas +${ganancia_tp2:,.2f} USDT")
    print(f"    - GANANCIA NETA TOTAL     : +${ganancia_total:,.2f} USDT (+{ganancia_total/capital_usdt*100:.2f}% de rendimiento neto sobre tu margen)")
    print(f"    - RATIO RIESGO / BENEFICIO: 1 : {ratio_rr:.1f} (Por cada $1 en riesgo, ganas ${ratio_rr:.1f})")

    # Comparativa con el Promediado por Susto
    print("\n" + "=" * 100)
    print("      LA DIFERENCIA ENTRE PROMEDIAR POR SUSTO VS ESCALAR POR ESTRATEGIA")
    print("=" * 100)
    print("  TRADER 1: PROMEDIADO POR SUSTO (Sin plan)")
    print("  1. Entra con $500 a 3x en $74,200. Nocional = $1,500.")
    print("  2. El precio cae $300 a $73,900: Se asusta y mete otros $500 a 3x. Nocional = $3,000.")
    print("  3. El precio cae a $73,600 (mecha normal de manipulación): Entra en pánico y mete otros $500.")
    print("     Ahora tiene $4,500 nocional (9x apalancado de su cuenta real).")
    print("  4. Su pérdida flotante llega a -$75 USDT. Siente pánico de perder la mitad de su cuenta,")
    print("     CIERRA EN EL PEOR MOMENTO (en la mecha baja de $73,600).")
    print("  5. Dos horas después, BTC sube $1,800 a $75,400. Se queda con la pérdida y la rabia.")
    print("-" * 100)
    print("  TRADER 2: ESCALAMIENTO ESTRATÉGICO (Nuestro Sistema)")
    print("  1. Nunca agrega dinero extra. Los $500 a 3x ya estaban fragmentados ($150 / $150 / $200).")
    print("  2. La caída de $500 USD es exactamente lo que estaba esperando para llenar el Tramo 3.")
    print("  3. Precio promedio impecable en $73,809. Riesgo máximo cerrado en -$10.76 USDT.")
    print("  4. Cuando BTC sube los $1,500 a $2,000, cobra sus +$27.30 USDT con calma absoluta.")
    print("=" * 100 + "\n")

if __name__ == "__main__":
    cap = 500.0
    lev = 3.0
    if len(sys.argv) > 1:
        try:
            cap = float(sys.argv[1])
        except ValueError:
            cap = 500.0
    simular_intradia_real(cap, lev)
