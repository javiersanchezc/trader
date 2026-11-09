"""
generador_plan_alerta.py - Generador Universal de Planes de Acción Multi-Activo con Guardián de Riesgo Determinista
Soporta cualquier activo (BTC, ETH, SOL, MSTR, XRP, etc.).
Incluye:
1. Semáforo de Seguridad Pre-Ejecución (Detector de Cuchillo Cayendo > 7% y Spread Tóxico > 25 bps).
2. Anclaje Estructural Real (swing_low / soporte de mecha en gráfica) o Volatilidad Beta calibrada.
3. Guardián Inmutable de Riesgo en Dólares (Tope estricto p.ej. -$20 USDT incluyendo Slippage y Comisiones).
   Si el soporte estructural está lejos, reduce automáticamente el tamaño/apalancamiento efectivo
   para que JAMÁS pierdas más de tu límite permitido.
4. Desglose contra Selección Adversa (Escenario si solo llena Orden 1 vs Llenado Completo 3/3).
"""

from __future__ import annotations
import sys
import os
import json
from datetime import datetime
from typing import Optional
from core.toxicity_detector import ToxicityDetector, DiagnosticoSeguridad

VOLATILIDAD_PRESETS = {
    "BTC": 0.90,
    "ETH": 1.15,
    "SOL": 1.45,
    "MSTR": 1.85,
    "DEFAULT": 1.10
}
VOLATILIDAD_INTRADIA_DEFAULT_PCT = 0.90

def normalizar_simbolo(simbolo_raw: str) -> str:
    s = simbolo_raw.upper().replace("/", "").replace("-", "").strip()
    if s.endswith("USDT") or s.endswith("USD") or s.endswith("USDC"):
        base = s.replace("USDT", "").replace("USDC", "").replace("USD", "")
        return f"{base}/USDT"
    return f"{s}/USDT"

def formatear_precision(valor: float, precio_activo: float) -> str:
    if precio_activo >= 1000.0:
        return f"{valor:,.2f}"
    elif precio_activo >= 10.0:
        return f"{valor:,.3f}"
    elif precio_activo >= 1.0:
        return f"{valor:,.4f}"
    else:
        return f"{valor:,.6f}"

def formatear_cantidad(qty: float) -> str:
    if qty >= 1000.0:
        return f"{qty:,.1f}"
    elif qty >= 10.0:
        return f"{qty:,.2f}"
    elif qty >= 1.0:
        return f"{qty:,.3f}"
    elif qty >= 0.01:
        return f"{qty:,.4f}"
    else:
        return f"{qty:,.6f}"

def calcular_y_generar_plan(
    simbolo: str = "BTC/USDT",
    precio_alerta: float = 74400.0,
    capital_usdt: float = 500.0,
    apalancamiento: float = 3.0,
    amplitud_pct: float = VOLATILIDAD_INTRADIA_DEFAULT_PCT,
    swing_low: Optional[float] = None,
    max_riesgo_usdt: float = 20.0,
    slippage_sl_bps: float = 8.0,
    taker_fee_bps: float = 4.0,
    caida_reciente_pct: Optional[float] = None,
    spread_bps: Optional[float] = None,
    volumen_24h_usdt: Optional[float] = None
) -> str:
    simbolo_clean = normalizar_simbolo(simbolo)
    base_coin = simbolo_clean.split("/")[0]
    nocional_solicitado = capital_usdt * apalancamiento

    # Determinar amplitud del impulso: Anclaje Estructural Real (swing_low) vs Preset Beta
    usando_soporte_real = False
    if swing_low is not None and 0.0 < swing_low < precio_alerta:
        usando_soporte_real = True
        p_origen_impulso = swing_low
        amplitud_usd = precio_alerta - swing_low
        amplitud_pct_efectiva = (amplitud_usd / precio_alerta) * 100.0
    else:
        if amplitud_pct == VOLATILIDAD_INTRADIA_DEFAULT_PCT:
            amplitud_pct_efectiva = VOLATILIDAD_PRESETS.get(base_coin, VOLATILIDAD_PRESETS.get("DEFAULT", 1.10))
        else:
            amplitud_pct_efectiva = amplitud_pct
        amplitud_usd = precio_alerta * (amplitud_pct_efectiva / 100.0)
        p_origen_impulso = precio_alerta - amplitud_usd

    # 1. EVALUAR TOXICIDAD Y SEGURIDAD PRE-EJECUCIÓN
    detector = ToxicityDetector()
    diagnostico = detector.evaluar_seguridad_mercado(
        precio_actual=precio_alerta,
        caida_pct_forzada=caida_reciente_pct,
        spread_bps_forzado=spread_bps,
        volumen_24h_forzado=volumen_24h_usdt
    )

    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lineas = []
    lineas.append("=" * 104)
    lineas.append(f"  PLAN DE EJECUCION TACTICA UNIVERSAL - {simbolo_clean} (SPOT ALERTA: ${formatear_precision(precio_alerta, precio_alerta)})")
    lineas.append(f"  Generado: {ahora} | Capital: ${capital_usdt:,.2f} USDT | Apalancamiento Max: {apalancamiento:.1f}x | Tope Riesgo: -${max_riesgo_usdt:,.2f}")
    if usando_soporte_real:
        lineas.append(f"  Modo Estructura: ANCLADO A SOPORTE REAL EN GRAFICA (${formatear_precision(p_origen_impulso, precio_alerta)} | Rango: {amplitud_pct_efectiva:.2f}%)")
    else:
        lineas.append(f"  Modo Estructura: VOLATILIDAD BETA CALIBRADA ({amplitud_pct_efectiva:.2f}% | Base Impulso: ${formatear_precision(p_origen_impulso, precio_alerta)})")
    lineas.append("=" * 104)

    # 2. BLOQUE DE SEMÁFORO DE SEGURIDAD
    lineas.append("\n" + "[SEMAFORO DE SEGURIDAD Y TOXICIDAD DE LA SENAL]")
    lineas.append("-" * 104)
    if diagnostico.nivel_peligro == "SEGURO":
        lineas.append(f"  * ESTADO DE SEGURIDAD       : [VERDE - SEGURO] Mercado con condiciones saludables.")
        lineas.append(f"  * Diagnostico de Caida      : Caida controlada ({diagnostico.caida_reciente_pct:.1f}% en 4H). No es cuchillo cayendo.")
        lineas.append(f"  * Diagnostico de Liquidez   : Spread optimo ({diagnostico.spread_bps:.1f} bps). Libro con profundidad adecuada.")
    elif diagnostico.nivel_peligro == "PRECAUCION_RIESGO_ALTO":
        lineas.append(f"  * ESTADO DE SEGURIDAD       : [AMARILLO - ALTO RIESGO] Problemas de liquidez detectados.")
        for m in diagnostico.motivos_alerta:
            lineas.append(f"    ! {m}")
    else: # PELIGRO_EXTREMO_BLOQUEADO
        lineas.append(f"  * ESTADO DE SEGURIDAD       : [ROJO - PELIGRO EXTREMO: CUCHILLO CAYENDO / LIQUIDEZ TOXICA]")
        for m in diagnostico.motivos_alerta:
            lineas.append(f"    ! {m}")

    lineas.append(f"  * Accion del Sistema        : {diagnostico.accion_recomendada}")

    # SI ESTA BLOQUEADO POR PELIGRO O TOXICIDAD, DETENER EMISIÓN DE COMPRAS
    if not diagnostico.aprobado_para_operar:
        lineas.append("\n" + "!" * 104)
        lineas.append("  [ORDEN DE BLOQUEO DE SEGURIDAD]: NO SE GENERAN ORDENES DE COMPRA PARA ESTA ALERTA.")
        if diagnostico.es_caida_libre_extrema:
            lineas.append("  Motivo: Caida a plomo (cuchillo cayendo). Esperar formacion de suelo y divergencia en 4H.")
        if diagnostico.tiene_problemas_liquidez:
            lineas.append("  Motivo: Libro iliquido o spread toxico. Entrar aqui provocaria un deslizamiento (slippage) que devora el beneficio.")
        lineas.append("  El sistema protege tu dinero manteniendolo al 100% en liquidez (USDT intacto).")
        lineas.append("!" * 104 + "\n")
        reporte = "\n".join(lineas)
        ruta_txt = os.path.join(os.path.dirname(__file__), "ULTIMO_PLAN_DE_ACCION.txt")
        with open(ruta_txt, "w", encoding="utf-8") as f:
            f.write(reporte)
        return reporte

    # 3. CALCULO DE PRECIOS ESTRUCTURALES (30% / 30% / 40%)
    p_quiebre = precio_alerta
    p_t1 = p_quiebre - (amplitud_usd * 0.382)
    p_t2 = p_quiebre - (amplitud_usd * 0.50)
    p_t3 = p_quiebre - (amplitud_usd * 0.75)
    # Colchón estructural del 0.35% bajo el mínimo real para evitar barrido de mecha
    p_sl = p_origen_impulso * (1.0 - 0.0035)

    # Precio promedio ponderado unitario (independiente del nocional total)
    unidades_por_dolar = (0.30 / p_t1) + (0.30 / p_t2) + (0.40 / p_t3)
    p_promedio = 1.0 / unidades_por_dolar

    # 4. GUARDIAN DE RIESGO EN CODIGO DURO (INCLUYENDO SLIPPAGE Y COMISIONES TAKER)
    distancia_sl_estructural_usd = p_promedio - p_sl
    costo_fricciones_por_unidad = p_sl * ((slippage_sl_bps + taker_fee_bps) / 10000.0)
    distancia_efectiva_usd = distancia_sl_estructural_usd + costo_fricciones_por_unidad

    qty_solicitada = nocional_solicitado * unidades_por_dolar
    perdida_potencial_bruta = qty_solicitada * distancia_efectiva_usd

    recorte_riesgo_aplicado = False
    if perdida_potencial_bruta > max_riesgo_usdt and max_riesgo_usdt > 0:
        recorte_riesgo_aplicado = True
        factor_escala = max_riesgo_usdt / perdida_potencial_bruta
        nocional_efectivo = nocional_solicitado * factor_escala
        apalancamiento_efectivo = nocional_efectivo / capital_usdt
        capital_asignado = capital_usdt * factor_escala
    else:
        factor_escala = 1.0
        nocional_efectivo = nocional_solicitado
        apalancamiento_efectivo = apalancamiento
        capital_asignado = capital_usdt

    m_t1 = round(capital_asignado * 0.30, 2)
    m_t2 = round(capital_asignado * 0.30, 2)
    m_t3 = round(capital_asignado * 0.40, 2)

    noc_t1 = nocional_efectivo * 0.30
    noc_t2 = nocional_efectivo * 0.30
    noc_t3 = nocional_efectivo * 0.40

    qty_t1 = noc_t1 / p_t1
    qty_t2 = noc_t2 / p_t2
    qty_t3 = noc_t3 / p_t3
    total_qty = qty_t1 + qty_t2 + qty_t3

    distancia_sl_pct = (distancia_sl_estructural_usd / p_promedio) * 100.0
    perdida_sl_usdt = round(total_qty * distancia_efectiva_usd, 2)
    perdida_sl_pct_cuenta = round((perdida_sl_usdt / capital_usdt) * 100.0, 2)

    p_tp1 = p_promedio + (distancia_sl_estructural_usd * 1.8)
    p_tp2 = p_promedio + (distancia_sl_estructural_usd * 3.2)

    ganancia_tp1 = round((total_qty * 0.5) * (p_tp1 - p_promedio), 2)
    ganancia_tp2 = round((total_qty * 0.5) * (p_tp2 - p_promedio), 2)
    ganancia_total = round(ganancia_tp1 + ganancia_tp2, 2)
    ratio_rr = round(ganancia_total / perdida_sl_usdt, 1) if perdida_sl_usdt > 0 else 2.5

    # Calculo de Escenario de Seleccion Adversa (Si solo se llena Orden 1 y despega a TP1)
    ganancia_solo_t1_a_tp1 = round(qty_t1 * (p_tp1 - p_t1), 2)

    if recorte_riesgo_aplicado:
        lineas.append("\n" + "[GUARDIAN DE RIESGO DETERMINISTA - AJUSTE AUTOMATICO DE POSICION]")
        lineas.append("-" * 104)
        lineas.append(f"  ! ALERTA DE AMPLITUD: El soporte estructural (${formatear_precision(p_origen_impulso, precio_alerta)}) esta a {amplitud_pct_efectiva:.2f}% de distancia.")
        lineas.append(f"  ! Si entraras con {apalancamiento:.1f}x completo (${nocional_solicitado:,.2f}), arriesgarias -${perdida_potencial_bruta:,.2f} USDT.")
        lineas.append(f"  * ACCION EN CODIGO DURO: Se reduce automaticamente la exposicion a {apalancamiento_efectivo:.2f}x efectivo")
        lineas.append(f"    (Nocional: ${nocional_efectivo:,.2f} | Margen Usado: ${capital_asignado:,.2f} USDT) para que tu perdida maxima")
        lineas.append(f"    incluyendo slippage ({slippage_sl_bps:.0f} bps) y comisiones ({taker_fee_bps:.0f} bps) sea EXACTAMENTE -${perdida_sl_usdt:,.2f} USDT.")

    lineas.append("\n" + f"[PASO 1]: PROGRAMA ESTAS 3 ORDENES LIMITES EN TU EXCHANGE PARA {simbolo_clean}")
    lineas.append("-" * 104)
    lineas.append(f"{'ORDEN':<10} | {'TIPO':<12} | {'PRECIO LIMITE':<18} | {f'CANTIDAD {base_coin}':<16} | {'MARGEN ASIGNADO':<15} | {'ZONA INSTITUCIONAL'}")
    lineas.append("-" * 104)
    lineas.append(f"Orden 1    | Limit Buy    | ${formatear_precision(p_t1, precio_alerta):<17} | {formatear_cantidad(qty_t1):<16} | ${m_t1:<14,.2f} | Retesteo Techo Roto 5m (30%)")
    lineas.append(f"Orden 2    | Limit Buy    | ${formatear_precision(p_t2, precio_alerta):<17} | {formatear_cantidad(qty_t2):<16} | ${m_t2:<14,.2f} | Equilibrio Fibo 50% OTE (30%)")
    lineas.append(f"Orden 3    | Limit Buy    | ${formatear_precision(p_t3, precio_alerta):<17} | {formatear_cantidad(qty_t3):<16} | ${m_t3:<14,.2f} | Suelo Order Block / Mecha (40%)")
    lineas.append("-" * 104)
    lineas.append(f"  >>> SI SE LLENAN LAS 3: Tu Precio Promedio Ponderado quedara en: ${formatear_precision(p_promedio, precio_alerta)}")
    lineas.append(f"      (Ahorro por esperar retroceso: ${formatear_precision(p_quiebre - p_promedio, precio_alerta)} por {base_coin})")

    lineas.append("\n" + "[PASO 2]: PROGRAMA LAS SALIDAS Y TRANSPARENCIA DE ESCENARIOS")
    lineas.append("-" * 104)
    lineas.append(f"  * STOP LOSS OBLIGATORIO (Stop Market) : ${formatear_precision(p_sl, precio_alerta)} (-{distancia_sl_pct:.2f}% bajo promedio | Bajo soporte ${formatear_precision(p_origen_impulso, precio_alerta)})")
    lineas.append(f"    - Riesgo Maximo Real (con Slippage) : -${perdida_sl_usdt:,.2f} USDT (Solo el {perdida_sl_pct_cuenta:.2f}% de tus ${capital_usdt:,.2f})")
    lineas.append(f"    - Saldo Restante si falla la idea   : ${capital_usdt - perdida_sl_usdt:,.2f} USDT (Capital protegido por codigo duro)")
    lineas.append("")
    lineas.append(f"  * TAKE PROFIT 1 (Limit Sell 50% pos)  : ${formatear_precision(p_tp1, precio_alerta)}  -->  Ganancia: +${ganancia_tp1:,.2f} USDT")
    lineas.append(f"    (Al llegar a TP1: Se asegura el 50% y mueves el Stop Loss de lo restante a Break-Even)")
    lineas.append(f"  * TAKE PROFIT 2 (Limit Sell 50% pos)  : ${formatear_precision(p_tp2, precio_alerta)}  -->  Ganancia: +${ganancia_tp2:,.2f} USDT")
    lineas.append(f"  * BENEFICIO TOTAL (Llenado 3/3)       : +${ganancia_total:,.2f} USDT (+{ganancia_total/capital_usdt*100:.2f}% sobre cuenta | R:R 1:{ratio_rr:.1f})")
    lineas.append(f"  * ESCENARIO LLENADO PARCIAL (Orden 1) : Si el precio solo toca la Orden 1 (${formatear_precision(p_t1, precio_alerta)}) y sube a TP1,")
    lineas.append(f"                                          ganas +${ganancia_solo_t1_a_tp1:,.2f} USDT sin haber arriesgado el resto del capital.")

    lineas.append("\n" + "[PASO 3]: PROTOCOLO ANTI-ANSIEDAD PARA CUALQUIER ACTIVO")
    lineas.append("-" * 104)
    lineas.append(f"  1. Deja las 3 ordenes y el Stop Loss programados en el exchange y CIERRA LA GRAFICA.")
    lineas.append(f"  2. El precio de {base_coin} oscilara y retrocedera; NO te asustes, ese retroceso te favorece.")
    lineas.append(f"  3. Si solo entra la Orden 1 y despega: NO agregues mas arriba. Ganas +${ganancia_solo_t1_a_tp1:,.2f} USDT sin riesgo.")
    lineas.append(f"  4. Si toca el Stop Loss: Aceptas perder los -${perdida_sl_usdt:,.2f} USDT calculados. Cero drama.")
    lineas.append("=" * 104 + "\n")

    reporte = "\n".join(lineas)
    ruta_txt = os.path.join(os.path.dirname(__file__), "ULTIMO_PLAN_DE_ACCION.txt")
    with open(ruta_txt, "w", encoding="utf-8") as f:
        f.write(reporte)

    return reporte

def main():
    if "--webhook" in sys.argv:
        try:
            from fastapi import FastAPI, Request
            import uvicorn
        except ImportError:
            print("[ERROR]: FastAPI o Uvicorn no están instalados.")
            return

        app = FastAPI(title="Receptor Universal con Guardián de Riesgo y Detector de Peligro")

        @app.post("/webhook")
        async def recibir_alerta(request: Request):
            try:
                body = await request.body()
                payload = json.loads(body.decode("utf-8"))
                simbolo = str(payload.get("ticker", payload.get("symbol", "BTC/USDT")))
                precio = float(payload.get("price", payload.get("close", 100.0)))
                capital = float(payload.get("capital", 500.0))
                lev = float(payload.get("leverage", 3.0))
                swing_low_val = payload.get("swing_low", payload.get("low"))
                max_risk_val = float(payload.get("max_risk_usdt", 20.0))
                caida = payload.get("drop_pct", payload.get("caida_pct"))
                spread = payload.get("spread_bps")
                vol = payload.get("volume_24h")

                plan = calcular_y_generar_plan(
                    simbolo=simbolo,
                    precio_alerta=precio,
                    capital_usdt=capital,
                    apalancamiento=lev,
                    swing_low=float(swing_low_val) if swing_low_val else None,
                    max_riesgo_usdt=max_risk_val,
                    caida_reciente_pct=float(caida) if caida else None,
                    spread_bps=float(spread) if spread else None,
                    volumen_24h_usdt=float(vol) if vol else None
                )
                print(plan)
                return {"status": "ok", "asset": simbolo, "message": "Plan analizado con éxito"}
            except Exception as e:
                return {"status": "error", "detail": str(e)}

        print(f"\n[SERVIDOR WEBHOOK CON GUARDIAN DE RIESGO ACTIVO]: Escuchando en http://127.0.0.1:8000/webhook\n")
        uvicorn.run(app, host="127.0.0.1", port=8000)

    else:
        # Modo CLI
        simbolo = "BTC"
        precio = 74400.0
        cap = 500.0
        lev = 3.0
        swing_low_cli: Optional[float] = None
        max_riesgo_cli = 20.0
        caida_simulada = None
        spread_simulado = None

        if "--crash" in sys.argv:
            caida_simulada = 9.5
        if "--illiquid" in sys.argv:
            spread_simulado = 45.0

        # Parseo de flags con valor (--low X, --max-risk Y)
        argv = sys.argv[1:]
        args_limpios = []
        i = 0
        while i < len(argv):
            arg = argv[i]
            if arg == "--low" and i + 1 < len(argv):
                try:
                    swing_low_cli = float(argv[i + 1])
                except ValueError:
                    pass
                i += 2
            elif arg == "--max-risk" and i + 1 < len(argv):
                try:
                    max_riesgo_cli = float(argv[i + 1])
                except ValueError:
                    pass
                i += 2
            elif arg.startswith("--"):
                i += 1
            else:
                args_limpios.append(arg)
                i += 1

        if len(args_limpios) > 0:
            arg1 = args_limpios[0].upper()
            try:
                precio = float(arg1)
                simbolo = "BTC"
            except ValueError:
                simbolo = arg1
                if len(args_limpios) > 1:
                    try:
                        precio = float(args_limpios[1])
                    except ValueError:
                        precio = 100.0

        if len(args_limpios) > 2:
            try:
                cap = float(args_limpios[2])
            except ValueError:
                cap = 500.0
        if len(args_limpios) > 3:
            try:
                lev = float(args_limpios[3])
            except ValueError:
                lev = 3.0
        if len(args_limpios) > 4 and swing_low_cli is None:
            try:
                swing_low_cli = float(args_limpios[4])
            except ValueError:
                swing_low_cli = None

        plan = calcular_y_generar_plan(
            simbolo=simbolo,
            precio_alerta=precio,
            capital_usdt=cap,
            apalancamiento=lev,
            swing_low=swing_low_cli,
            max_riesgo_usdt=max_riesgo_cli,
            caida_reciente_pct=caida_simulada,
            spread_bps=spread_simulado
        )
        print(plan)

if __name__ == "__main__":
    main()
