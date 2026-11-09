"""
multi_timeframe.py - Analizador de Acción del Precio Limpia Multi-Temporal
Estructura el análisis en tres horizontes complementarios:
1. Largo Plazo (1D / 1W): Sesgo Direccional Macro (Bias) y Zonas Mayores de Liquidez.
2. Mediano Plazo (4H / 1H): Estructura de Mercado (BOS/CHoCH) y Rango de Negociación (Premium vs Discount).
3. Corto Plazo (15M / 5M): Gatillo de Entrada (Order Blocks, Sweeps, R:R exacto, SL y TPs).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from core.types import Candle

@dataclass
class VisionLargoPlazo:
    tendencia_macro: str          # "ALCISTA_FUERTE", "BAJISTA_FUERTE", "RANGO_LATERAL"
    sesgo_direccional: str        # "SOLO_LARGOS", "SOLO_CORTOS", "CAUTELA_NEUTRAL"
    resistencia_clave_macro: float
    soporte_clave_macro: float
    nivel_invalidacion_macro: float
    racional_limpio: str

@dataclass
class VisionMedianoPlazo:
    estructura_mercado: str       # "CONTINUACION_ALCISTA", "QUIEBRE_DE_ESTRUCTURA_BOS", "CAMBIO_DE_CARACTER_CHOCH", "RANGO"
    rango_minimo: float           # Rango de negociación actual
    rango_maximo: float
    precio_equilibrio: float      # Nivel del 50% (Equilibrium)
    ubicacion_actual: str         # "ZONA_DESCUENTO_COMPRA" (barato < 50%) o "ZONA_PREMIUM_VENTA" (caro > 50%)
    zona_demanda_h4: tuple[float, float]
    zona_oferta_h4: tuple[float, float]
    racional_limpio: str

@dataclass
class VisionCortoPlazo:
    estado_gatillo: str           # "DISPARAR_COMPRA", "DISPARAR_VENTA", "ESPERAR_CONFIRMACION", "SIN_OPERACION"
    tipo_patron: str              # "RETESTEO_ORDER_BLOCK", "BARRIDO_LIQUIDEZ_TRAMPA", "RUPTURA_REAL"
    precio_entrada: float
    stop_loss_tecnico: float
    take_profit_1: float
    take_profit_2: float
    ratio_riesgo_beneficio: float # e.g. 2.5 (1:2.5)
    invalidation_gatillo: float
    racional_limpio: str

@dataclass
class HojaDeRutaDecision:
    simbolo: str
    precio_spot: float
    largo_plazo: VisionLargoPlazo
    mediano_plazo: VisionMedianoPlazo
    corto_plazo: VisionCortoPlazo
    plan_de_accion_ejecutivo: str

class PriceActionEngine:
    """
    Motor determinista que traduce datos de velas a una visión limpia multi-temporal.
    """
    def __init__(self, symbol: str = "BTC/USDT"):
        self.symbol = symbol

    def analizar_largo_plazo(self, candles_daily: List[Candle], precio_actual: float) -> VisionLargoPlazo:
        if len(candles_daily) < 10:
            return VisionLargoPlazo("RANGO", "CAUTELA_NEUTRAL", precio_actual * 1.1, precio_actual * 0.9, precio_actual * 0.85, "Datos insuficientes")

        highs = [c.high for c in candles_daily[-20:]]
        lows = [c.low for c in candles_daily[-20:]]
        max_h = max(highs)
        min_l = min(lows)

        c_first = candles_daily[-10].close
        c_last = precio_actual
        cambio_pct = (c_last - c_first) / c_first

        if cambio_pct > 0.05:
            tendencia = "ALCISTA_ESTRUCTURAL"
            sesgo = "SOLO_LARGOS (Favorecer compras en retrocesos)"
        elif cambio_pct < -0.05:
            tendencia = "BAJISTA_ESTRUCTURAL"
            sesgo = "SOLO_CORTOS (Favorecer ventas en rebotes)"
        else:
            tendencia = "CONSOLIDACIÓN_LATERAL"
            sesgo = "NEUTRAL / RANGO (Operar solo extremos)"

        soporte_macro = min_l
        resistencia_macro = max_h
        invalidacion = soporte_macro * 0.98 if "ALCISTA" in tendencia else resistencia_macro * 1.02

        racional = (
            f"El gráfico diario muestra una tendencia {tendencia}. "
            f"El sesgo rector es {sesgo}. La invalidación del marco mayor ocurre en ${invalidacion:,.2f}."
        )

        return VisionLargoPlazo(
            tendencia_macro=tendencia,
            sesgo_direccional=sesgo,
            resistencia_clave_macro=resistencia_macro,
            soporte_clave_macro=soporte_macro,
            nivel_invalidacion_macro=invalidacion,
            racional_limpio=racional
        )

    def analizar_mediano_plazo(self, candles_h4: List[Candle], precio_actual: float) -> VisionMedianoPlazo:
        if len(candles_h4) < 15:
            return VisionMedianoPlazo("RANGO", precio_actual * 0.95, precio_actual * 1.05, precio_actual, "EQUILIBRIO", (0, 0), (0, 0), "Datos insuficientes")

        ultimas_15 = candles_h4[-15:]
        rango_max = max(c.high for c in ultimas_15)
        rango_min = min(c.low for c in ultimas_15)
        eq = (rango_max + rango_min) / 2.0

        if precio_actual < eq:
            ubicacion = "ZONA_DESCUENTO (Zona barata para buscar compras)"
        else:
            ubicacion = "ZONA_PREMIUM (Zona cara / buscar toma de ganancias o ventas)"

        # Determinar estructura
        c_ant = ultimas_15[-3].close
        if precio_actual > c_ant and precio_actual > eq:
            estructura = "EXPANSIÓN_ALCISTA (BOS alcista confirmado)"
        elif precio_actual < c_ant and precio_actual < eq:
            estructura = "PRESION_BAJISTA (BOS bajista en desarrollo)"
        else:
            estructura = "CONSOLIDACIÓN_DE_RANGO (Acumulación/Distribución)"

        zona_demanda = (rango_min, rango_min + (eq - rango_min) * 0.35)
        zona_oferta = (rango_max - (rango_max - eq) * 0.35, rango_max)

        racional = (
            f"Rango de 4H delimitado entre ${rango_min:,.2f} y ${rango_max:,.2f}. "
            f"El precio cotiza a ${precio_actual:,.2f}, situándose en {ubicacion}. "
            f"Nivel de equilibrio (50% Fibo) en ${eq:,.2f}."
        )

        return VisionMedianoPlazo(
            estructura_mercado=estructura,
            rango_minimo=rango_min,
            rango_maximo=rango_max,
            precio_equilibrio=eq,
            ubicacion_actual=ubicacion,
            zona_demanda_h4=zona_demanda,
            zona_oferta_h4=zona_oferta,
            racional_limpio=racional
        )

    def analizar_corto_plazo(
        self,
        candles_m15: List[Candle],
        precio_actual: float,
        sesgo_macro: str,
        zona_demanda_h4: tuple[float, float],
        precio_equilibrio_h4: float
    ) -> VisionCortoPlazo:
        if len(candles_m15) < 5:
            return VisionCortoPlazo("ESPERAR", "NINGUNO", precio_actual, precio_actual * 0.98, precio_actual * 1.04, precio_actual * 1.08, 2.0, precio_actual * 0.98, "Datos insuficientes")

        # Regla de Hierro Institucional:
        # Solo se permite gatillar compra si el precio está en ZONA DE DESCUENTO (< equilibrio 50%)
        # y retesteando la zona de demanda de 4H.
        esta_en_descuento = precio_actual < precio_equilibrio_h4
        en_demanda = esta_en_descuento and (zona_demanda_h4[0] * 0.998 <= precio_actual <= zona_demanda_h4[1] * 1.002)
        swing_low_local = min(c.low for c in candles_m15[-5:])
        swing_high_local = max(c.high for c in candles_m15[-5:])

        if "LARGOS" in sesgo_macro and en_demanda:
            estado = "DISPARAR_COMPRA (Condiciones Óptimas de Descuento Cumplidas)"
            patron = "RETESTEO_ORDER_BLOCK_EN_DESCUENTO"
            entrada = precio_actual
            stop_loss = swing_low_local - (precio_actual * 0.003)
            tp1 = precio_equilibrio_h4
            tp2 = swing_high_local
            riesgo = entrada - stop_loss
            beneficio = tp1 - entrada
            rr = beneficio / riesgo if riesgo > 0 else 2.0
            racional = (
                f"El precio está en Zona de Descuento (${precio_actual:,.2f} < Eq ${precio_equilibrio_h4:,.2f}) "
                f"retesteando demanda institucional. Entrada en ${entrada:,.2f} con SL técnico en ${stop_loss:,.2f} (R:R 1:{rr:.1f})."
            )
        elif "LARGOS" in sesgo_macro and not esta_en_descuento:
            estado = "ESPERAR_RETROCESO (No comprar en Zona Premium / Cara)"
            patron = "PRECIO_EN_ZONA_PREMIUM_EXTENDIDO"
            entrada = zona_demanda_h4[1]
            stop_loss = zona_demanda_h4[0] * 0.995
            tp1 = precio_equilibrio_h4
            tp2 = swing_high_local
            riesgo = entrada - stop_loss
            beneficio = tp2 - entrada
            rr = beneficio / riesgo if riesgo > 0 else 2.2
            racional = (
                f"El sesgo macro es ALCISTA, pero el precio actual (${precio_actual:,.2f}) está en ZONA PREMIUM "
                f"(por encima del 50% en ${precio_equilibrio_h4:,.2f}). Comprar aquí implica asumir riesgo asimétrico negativo. "
                f"Paciencia activa: esperar retroceso hacia la Zona de Descuento en ${entrada:,.2f}."
            )
        else:
            estado = "CAUTELA_SIN_OPERACION"
            patron = "RANGO_INDEFINIDO"
            entrada = precio_actual
            stop_loss = precio_actual * 0.985
            tp1 = precio_actual * 1.02
            tp2 = precio_actual * 1.04
            rr = 1.5
            racional = "Mercado sin ventaja matemática clara. Preservar capital fuera de mercado."

        return VisionCortoPlazo(
            estado_gatillo=estado,
            tipo_patron=patron,
            precio_entrada=round(entrada, 2),
            stop_loss_tecnico=round(stop_loss, 2),
            take_profit_1=round(tp1, 2),
            take_profit_2=round(tp2, 2),
            ratio_riesgo_beneficio=round(rr, 2),
            invalidation_gatillo=round(stop_loss, 2),
            racional_limpio=racional
        )

    def generar_hoja_de_ruta(
        self,
        candles_daily: List[Candle],
        candles_h4: List[Candle],
        candles_m15: List[Candle],
        precio_actual: float
    ) -> HojaDeRutaDecision:
        largo = self.analizar_largo_plazo(candles_daily, precio_actual)
        mediano = self.analizar_mediano_plazo(candles_h4, precio_actual)
        corto = self.analizar_corto_plazo(
            candles_m15=candles_m15,
            precio_actual=precio_actual,
            sesgo_macro=largo.sesgo_direccional,
            zona_demanda_h4=mediano.zona_demanda_h4,
            precio_equilibrio_h4=mediano.precio_equilibrio
        )

        if "DISPARAR" in corto.estado_gatillo:
            plan = f"COMPRA EN DESCUENTO: Gatillar en ${corto.precio_entrada:,.2f}. SL: ${corto.stop_loss_tecnico:,.2f} | TP1: ${corto.take_profit_1:,.2f} (R:R 1:{corto.ratio_riesgo_beneficio:.1f})."
        elif "ESPERAR" in corto.estado_gatillo:
            plan = f"PACIENCIA ACTIVA (NO PERSEGUIR EL PRECIO): El precio cotiza en Zona Premium (${precio_actual:,.2f} > Eq ${mediano.precio_equilibrio:,.2f}). Colocar orden límite de compra en zona barata (${corto.precio_entrada:,.2f}) con SL en ${corto.stop_loss_tecnico:,.2f}."
        else:
            plan = "FUERA DE MERCADO: No hay configuración de alta probabilidad con ventaja matemática."

        return HojaDeRutaDecision(
            simbolo=self.symbol,
            precio_spot=precio_actual,
            largo_plazo=largo,
            mediano_plazo=mediano,
            corto_plazo=corto,
            plan_de_accion_ejecutivo=plan
        )
