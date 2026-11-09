"""
gestor_escalamiento.py - Planificador Matemático de Escalamiento Institucional (Scale-In 30/30/40)
Elimina el promediado por pánico o ansiedad y lo reemplaza por una distribución
predefinida en 3 tramos de liquidez institucional con riesgo estrictamente acotado.
"""

from __future__ import annotations
import sys
from core.position_scaling import ScaleInManager

def mostrar_plan_escalamiento(
    margen_usdt: float = 500.0,
    apalancamiento: float = 3.0,
    zona_alta_demanda: float = 73500.0,
    zona_baja_demanda: float = 72800.0
):
    manager = ScaleInManager(symbol="BTC/USDT")
    plan = manager.calcular_plan_escalado(
        margen_total_usdt=margen_usdt,
        apalancamiento=apalancamiento,
        zona_alta_demanda=zona_alta_demanda,
        zona_baja_demanda=zona_baja_demanda
    )

    print("=" * 96)
    print(f"   PLAN DE ESCALAMIENTO PROFESIONAL (SCALE-IN 30/30/40) - CAPITAL: ${margen_usdt:,.2f} a {apalancamiento:.0f}x")
    print("=" * 96)

    print("\n[DIAGNOSTICO DEL ERROR COMUN: PROMEDIAR POR ANSIEDAD]")
    print("-" * 96)
    print("  * El error tipico: Entrar con todo el capital arriba y, cuando el precio baja un 0.5%,")
    print("    asustarse y meter mas dinero de forma improvisada para 'bajar el precio promedio'.")
    print("  * La consecuencia: Agotas tu liquidez demasiado rapido y, cuando el precio llega al verdadero")
    print("    fondo del retroceso institucional, ya estas sobreapalancado y con panico de liquidacion.")
    print("  * La solucion institucional: NUNCA agregar dinero nuevo. Tu capital total ($500 a 3x = $1,500)")
    print("    se fragmenta DE ANTEMANO en 3 ordenes limites pasivas colocadas en niveles estrategicos.")

    print("\n[DISTRIBUCION MATEMATICA DE LAS 3 ENTRADAS]")
    print("-" * 96)
    print(f"{'TRAMO':<8} | {'%':<5} | {'MARGEN':<10} | {'NOCIONAL':<11} | {'PRECIO LIMITE':<15} | {'BTC':<9} | {'ZONA INSTITUCIONAL'}")
    print("-" * 96)

    for t in plan.tramos:
        print(f"Tramo {t.numero_tramo:<2} | {t.porcentaje_capital*100:>2.0f}% | ${t.margen_usdt:<9,.2f} | ${t.nocional_usdt:<10,.2f} | ${t.precio_orden:<14,.2f} | {t.cantidad_activo:<8.4f} | {t.tipo_zona}")

    print("-" * 96)
    print(f"  >>> PRECIO PROMEDIO RESULTANTE (Si entran los 3 tramos): ${plan.precio_promedio_proyectado:,.2f}")
    print(f"      (Mejora tu precio de entrada en ${zona_alta_demanda - plan.precio_promedio_proyectado:,.2f} respecto a entrar todo arriba)")

    print("\n[GESTION ESTRICTA DE RIESGO Y BENEFICIO]")
    print("-" * 96)
    print(f"  * STOP LOSS INMUTABLE   : ${plan.stop_loss_inmutable:,.2f} (0.4% por debajo del minimo de demanda)")
    print(f"  * PERDIDA MAXIMA TOTAL  : -${plan.perdida_maxima_usdt:,.2f} USDT (Solo arriesgas el {plan.perdida_maxima_pct:.2f}% de tus ${margen_usdt:,.2f})")
    print(f"  * OBJETIVO 1 (TP1 50%)  : ${plan.take_profit_1:,.2f} (Ganancia estimada: +${plan.ganancia_proyectada_tp1:,.2f} USDT)")
    print(f"  * OBJETIVO 2 (TP2 50%)  : ${plan.take_profit_2:,.2f} (Ganancia estimada: +${plan.ganancia_proyectada_tp2:,.2f} USDT)")
    print(f"  * BENEFICIO TOTAL ESP.  : +${plan.ganancia_proyectada_tp1 + plan.ganancia_proyectada_tp2:,.2f} USDT")
    print(f"  * RATIO RIESGO/BENEFICIO: 1 : {plan.ratio_riesgo_beneficio:.1f}")

    print("\n[LAS 3 REGLAS DE ORO PARA NO CAER EN PANICO]")
    print("-" * 96)
    print("  1. DEJA LAS 3 ORDENES PUESTAS EN EL EXCHANGE Y CIERRA LA PANTALLA.")
    print("     No mires vela por vela de 1 minuto. El retroceso es normal y necesario para llenarte.")
    print("  2. SI SOLO ENTRA EL TRAMO 1 Y SUBE: NO AGREGUES MAS ARRIBA.")
    print("     Ganas con el 30% del capital sin riesgo. Menos ganancia es mejor que perseguir el precio.")
    print("  3. SI TOCA EL STOP LOSS: SE CIERRA TODO.")
    print("     Aceptas perder los -$25 o -$30 calculados. NUNCA canceles el Stop Loss ni metas mas margen.")
    print("=" * 96 + "\n")

if __name__ == "__main__":
    margen = 500.0
    lev = 3.0
    z_alta = 73500.0
    z_baja = 72800.0

    if len(sys.argv) > 1:
        try:
            margen = float(sys.argv[1])
        except ValueError:
            margen = 500.0
    if len(sys.argv) > 2:
        try:
            lev = float(sys.argv[2])
        except ValueError:
            lev = 3.0
    if len(sys.argv) > 3:
        try:
            z_alta = float(sys.argv[3])
        except ValueError:
            z_alta = 73500.0
    if len(sys.argv) > 4:
        try:
            z_baja = float(sys.argv[4])
        except ValueError:
            z_baja = 72800.0

    mostrar_plan_escalamiento(margen, lev, z_alta, z_baja)
