"""
toxicity_detector.py - Detector Cuantitativo de Caídas Extremas y Falta de Liquidez
Evalúa si una señal es peligrosa antes de emitir o ejecutar un plan:
1. Filtro 'Cuchillo Cayendo' (Falling Knife / Flash Crash): Caídas aceleradas sin absorción.
2. Filtro de Liquidez Tóxica: Spreads anchos (> 25 bps), libros anémicos o bajo volumen 24h.
3. Clasificación de Peligro: SEGURO, PRECAUCIÓN o PELIGRO_EXTREMO_BLOQUEADO.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
from core.types import OrderBookSnapshot, Candle

@dataclass
class DiagnosticoSeguridad:
    nivel_peligro: str            # "SEGURO", "PRECAUCION_RIESGO_ALTO", "PELIGRO_EXTREMO_BLOQUEADO"
    aprobado_para_operar: bool
    es_caida_libre_extrema: bool  # True si el activo se está desangrando en picado
    tiene_problemas_liquidez: bool# True si el libro está vacío o el spread es tóxico
    caida_reciente_pct: float     # Caída porcentual en las últimas velas
    spread_bps: float             # Spread en puntos básicos
    volumen_24h_usdt: float       # Volumen estimado en USDT
    motivos_alerta: List[str]
    accion_recomendada: str       # "PROCEDER_NORMAL", "REDUCIR_APALANCAMIENTO_A_1X", "CANCELAR_Y_ESPERAR"

class ToxicityDetector:
    def __init__(
        self,
        max_spread_bps: float = 25.0,         # Máximo 0.25% de spread aceptable
        max_caida_veloz_pct: float = 7.0,     # Si cayó más del 7% en 4H sin freno, es cuchillo cayendo
        min_volumen_24h_usdt: float = 5_000_000.0 # Mínimo $5M de volumen diario
    ):
        self.max_spread_bps = max_spread_bps
        self.max_caida_veloz_pct = max_caida_veloz_pct
        self.min_volumen_24h_usdt = min_volumen_24h_usdt

    def evaluar_seguridad_mercado(
        self,
        precio_actual: float,
        candles_4h: Optional[List[Candle]] = None,
        book: Optional[OrderBookSnapshot] = None,
        caida_pct_forzada: Optional[float] = None,
        spread_bps_forzado: Optional[float] = None,
        volumen_24h_forzado: Optional[float] = None
    ) -> DiagnosticoSeguridad:
        motivos = []
        es_caida_libre = False
        problemas_liquidez = False

        # 1. Análisis de Caída Violenta (Falling Knife)
        caida_pct = 0.0
        if caida_pct_forzada is not None:
            caida_pct = caida_pct_forzada
        elif candles_4h and len(candles_4h) >= 4:
            p_inicio = candles_4h[-4].open
            p_fin = precio_actual
            caida_pct = ((p_inicio - p_fin) / p_inicio) * 100.0

        if caida_pct >= self.max_caida_veloz_pct:
            es_caida_libre = True
            motivos.append(
                f"ALERTA CUCHILLO CAYENDO: Caída violenta del {caida_pct:.2f}% en marco mayor. "
                f"El momentum bajista es demasiado destructivo para compras directas."
            )

        # 2. Análisis de Liquidez y Spread Tóxico
        spread_bps = 2.0
        if spread_bps_forzado is not None:
            spread_bps = spread_bps_forzado
        elif book and book.bids and book.asks:
            best_bid = book.bids[0][0]
            best_ask = book.asks[0][0]
            mid = (best_bid + best_ask) / 2.0
            if mid > 0:
                spread_bps = ((best_ask - best_bid) / mid) * 10000.0

        if spread_bps > self.max_spread_bps:
            problemas_liquidez = True
            motivos.append(
                f"SPREAD TOXICO ({spread_bps:.1f} bps > umbral {self.max_spread_bps:.0f} bps): "
                f"Activo poco líquido. El deslizamiento (slippage) devorará tu beneficio."
            )

        # 3. Análisis de Volumen
        vol_24h = volumen_24h_forzado if volumen_24h_forzado is not None else 50_000_000.0
        if vol_24h < self.min_volumen_24h_usdt:
            problemas_liquidez = True
            motivos.append(
                f"VOLUMEN ANEMICO (${vol_24h:,.0f} < ${self.min_volumen_24h_usdt:,.0f}): "
                f"Poco interés institucional, alto riesgo de manipulación por ballenas (Pump & Dump)."
            )

        # 4. Clasificación del Peligro y Acción Determinista
        if es_caida_libre and problemas_liquidez:
            nivel = "PELIGRO_EXTREMO_BLOQUEADO"
            aprobado = False
            accion = "BLOQUEAR_ORDEN: Caída libre masiva combinada con libro ilíquido. NO OPERAR."
        elif es_caida_libre:
            nivel = "PELIGRO_EXTREMO_BLOQUEADO"
            aprobado = False
            accion = "BLOQUEAR_ORDEN: Esperar que el mercado forme suelo en 4H y divergencia antes de intentar compras."
        elif problemas_liquidez:
            nivel = "PRECAUCION_RIESGO_ALTO"
            aprobado = False
            accion = "BLOQUEAR_ORDEN: El activo carece de liquidez institucional suficiente."
        else:
            nivel = "SEGURO"
            aprobado = True
            accion = "PROCEDER_NORMAL: Condiciones de liquidez y volatilidad saludables."

        return DiagnosticoSeguridad(
            nivel_peligro=nivel,
            aprobado_para_operar=aprobado,
            es_caida_libre_extrema=es_caida_libre,
            tiene_problemas_liquidez=problemas_liquidez,
            caida_reciente_pct=round(caida_pct, 2),
            spread_bps=round(spread_bps, 2),
            volumen_24h_usdt=vol_24h,
            motivos_alerta=motivos,
            accion_recomendada=accion
        )
