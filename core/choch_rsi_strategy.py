"""
choch_rsi_strategy.py - Estrategia Cuantitativa CHoCH 5m + Divergencia RSI 4H + Escalamiento 30/30/40
Traducción matemática fiel del indicador de Pine Script v6 combinada con el motor
institucional de escalamiento en retroceso para evitar compras en el techo del quiebre.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
import math
from core.types import Candle
from core.position_scaling import ScaleInManager, PlanEscalamiento

@dataclass
class SetupCHoCHRSI:
    confirmado: bool
    timestamp: int
    precio_quiebre_choch: float
    swing_high_roto: float
    swing_low_invalidation: float
    divergencia_4h_activa: bool
    rsi_4h_valor: float
    # Comparativa de ejecución:
    # 1. Entrada Clásica a Mercado (del indicador original)
    entrada_mercado_clasica: float
    stop_loss_clasico: float
    take_profit_clasico: float
    ratio_rr_clasico: float
    # 2. Entrada Optimizada por Escalamiento 30/30/40 (en el retroceso)
    plan_escalamiento: PlanEscalamiento

class ChochRsiStrategy:
    def __init__(
        self,
        rsi_length: int = 14,
        rsi_threshold: float = 35.0,
        pivot_lookback_4h: int = 3,
        swing_length_5m: int = 3,
        sl_buffer_pct: float = 0.1,
        rr_ratio: float = 2.0
    ):
        self.rsi_length = rsi_length
        self.rsi_threshold = rsi_threshold
        self.pivot_lookback_4h = pivot_lookback_4h
        self.swing_length_5m = swing_length_5m
        self.sl_buffer_pct = sl_buffer_pct
        self.rr_ratio = rr_ratio
        self.scale_manager = ScaleInManager(symbol="BTC/USDT")

    def calcular_rsi(self, closes: List[float]) -> List[float]:
        """Calcula el RSI clásico de Wilder exactamente como en Pine Script."""
        if len(closes) <= self.rsi_length:
            return [50.0] * len(closes)

        gains = []
        losses = []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i - 1]
            gains.append(max(0.0, diff))
            losses.append(max(0.0, -diff))

        # Primera media simple
        avg_gain = sum(gains[:self.rsi_length]) / self.rsi_length
        avg_loss = sum(losses[:self.rsi_length]) / self.rsi_length

        rsi_values = [50.0] * (self.rsi_length)
        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100.0 - (100.0 / (1.0 + rs)))

        # Alisado exponencial de Wilder (Pine Script rma)
        for i in range(self.rsi_length, len(gains)):
            avg_gain = (avg_gain * (self.rsi_length - 1) + gains[i]) / self.rsi_length
            avg_loss = (avg_loss * (self.rsi_length - 1) + losses[i]) / self.rsi_length
            if avg_loss == 0:
                rsi_values.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi_values.append(100.0 - (100.0 / (1.0 + rs)))

        return rsi_values

    def detectar_divergencia_alcista_4h(self, candles_4h: List[Candle]) -> Tuple[bool, float]:
        """
        Calcula divergencia regular alcista en 4H sin repainting:
        Precio hace Lower Low mientras RSI hace Higher Low (y al menos uno estuvo en sobreventa <= 35).
        Permite tolerancia de alineación de ±3 barras entre pivotes de precio y RSI.
        Se apaga cuando RSI > 50.
        """
        k = self.pivot_lookback_4h
        if len(candles_4h) < (self.rsi_length + k * 2 + 5):
            return False, 50.0

        closes = [c.close for c in candles_4h]
        lows = [c.low for c in candles_4h]
        rsi_series = self.calcular_rsi(closes)
        current_rsi = rsi_series[-1]

        if current_rsi > 50.0:
            return False, current_rsi

        # 1. Extraer pivotes de precio con su índice
        pivots_price = []
        for i in range(k, len(candles_4h) - k):
            if all(lows[i] <= lows[i - j] for j in range(1, k + 1)) and all(lows[i] <= lows[i + j] for j in range(1, k + 1)):
                pivots_price.append((i, lows[i]))

        # 2. Extraer pivotes de RSI con su índice (ignorando la fase inicial de warmup)
        pivots_rsi = []
        for i in range(max(k, self.rsi_length), len(candles_4h) - k):
            if all(rsi_series[i] <= rsi_series[i - j] for j in range(1, k + 1)) and all(rsi_series[i] <= rsi_series[i + j] for j in range(1, k + 1)):
                pivots_rsi.append((i, rsi_series[i]))

        if len(pivots_price) < 2 or len(pivots_rsi) < 2:
            return False, current_rsi

        # Emparejar el último pivote y el penúltimo pivote dentro de una ventana de ±3 barras
        def buscar_rsi_cercano(idx_precio: int):
            candidatos = [r for idx_r, r in pivots_rsi if abs(idx_r - idx_precio) <= 3]
            return candidatos[-1] if candidatos else None

        p2_idx, p2_price = pivots_price[-1]
        p1_idx, p1_price = pivots_price[-2]

        r2_val = buscar_rsi_cercano(p2_idx)
        r1_val = buscar_rsi_cercano(p1_idx)

        if r1_val is not None and r2_val is not None:
            price_lower_low = p2_price < p1_price
            rsi_higher_low = r2_val > r1_val
            rsi_was_oversold = (r1_val <= self.rsi_threshold) or (r2_val <= self.rsi_threshold)

            if price_lower_low and rsi_higher_low and rsi_was_oversold:
                return True, current_rsi

        return False, current_rsi

    def detectar_choch_5m(self, candles_5m: List[Candle]) -> Tuple[bool, Optional[float], Optional[float]]:
        """
        Detecta si la última vela de 5m cerró con cuerpo por encima del swing high anterior.
        Retorna: (choch_confirmado, last_swing_high, recent_swing_low)
        """
        k = self.swing_length_5m
        if len(candles_5m) < (k * 2 + 5):
            return False, None, None

        highs = [c.high for c in candles_5m]
        lows = [c.low for c in candles_5m]

        # Encontrar el último swing high y swing low confirmados antes de la vela actual
        last_swing_high = None
        last_swing_low = None

        # Escanear hacia atrás desde len - 2
        for i in range(len(candles_5m) - 2 - k, k - 1, -1):
            is_ph = all(highs[i] >= highs[i - j] for j in range(1, k + 1)) and all(highs[i] >= highs[i + j] for j in range(1, k + 1))
            if is_ph and last_swing_high is None:
                last_swing_high = highs[i]
                break

        for i in range(len(candles_5m) - 2 - k, k - 1, -1):
            is_pl = all(lows[i] <= lows[i - j] for j in range(1, k + 1)) and all(lows[i] <= lows[i + j] for j in range(1, k + 1))
            if is_pl and last_swing_low is None:
                last_swing_low = lows[i]
                break

        if last_swing_low is None:
            last_swing_low = min(lows[-10:])

        if last_swing_high is None:
            return False, None, last_swing_low

        curr = candles_5m[-1]
        prev = candles_5m[-2]

        # Quiebre con cuerpo exacto como en el script: close > lastSwingHigh and close[1] <= lastSwingHigh
        choch_confirmado = (curr.close > last_swing_high) and (prev.close <= last_swing_high)

        return choch_confirmado, last_swing_high, last_swing_low

    def evaluar_estrategia(
        self,
        candles_4h: List[Candle],
        candles_5m: List[Candle],
        capital_usdt: float = 500.0,
        apalancamiento: float = 3.0
    ) -> SetupCHoCHRSI:
        div_activa, rsi_val = self.detectar_divergencia_alcista_4h(candles_4h)
        choch_ok, swing_high, swing_low = self.detectar_choch_5m(candles_5m)

        trigger = div_activa and choch_ok and (swing_high is not None) and (swing_low is not None)

        if not trigger:
            # Plan neutral por defecto
            dummy_plan = self.scale_manager.calcular_plan_escalado(
                margen_total_usdt=capital_usdt,
                apalancamiento=apalancamiento,
                zona_alta_demanda=candles_5m[-1].close if candles_5m else 74000.0,
                zona_baja_demanda=(candles_5m[-1].close * 0.99) if candles_5m else 73000.0
            )
            return SetupCHoCHRSI(
                confirmado=False,
                timestamp=candles_5m[-1].timestamp if candles_5m else 0,
                precio_quiebre_choch=candles_5m[-1].close if candles_5m else 0.0,
                swing_high_roto=swing_high or 0.0,
                swing_low_invalidation=swing_low or 0.0,
                divergencia_4h_activa=div_activa,
                rsi_4h_valor=round(rsi_val, 2),
                entrada_mercado_clasica=0.0,
                stop_loss_clasico=0.0,
                take_profit_clasico=0.0,
                ratio_rr_clasico=0.0,
                plan_escalamiento=dummy_plan
            )

        # 1. Parámetros Clásicos del Indicador (Entrada a Mercado)
        entry_price = candles_5m[-1].close
        stop_loss_clasico = swing_low * (1.0 - (self.sl_buffer_pct / 100.0))
        dist_riesgo = entry_price - stop_loss_clasico
        tp_clasico = entry_price + (dist_riesgo * self.rr_ratio)

        # 2. Parámetros Optimizados de Escalamiento 30/30/40 en el Retroceso
        # La zona de retroceso institucional se ubica entre el swing high roto y el swing low
        zona_alta_demanda = swing_high  # El antiguo swing high ahora actúa como soporte/borde superior
        zona_baja_demanda = swing_low + (entry_price - swing_low) * 0.25 # 25% por encima del mínimo

        plan_esc = self.scale_manager.calcular_plan_escalado(
            margen_total_usdt=capital_usdt,
            apalancamiento=apalancamiento,
            zona_alta_demanda=zona_alta_demanda,
            zona_baja_demanda=zona_baja_demanda,
            stop_loss_colchon_pct=(self.sl_buffer_pct / 100.0)
        )

        return SetupCHoCHRSI(
            confirmado=True,
            timestamp=candles_5m[-1].timestamp,
            precio_quiebre_choch=entry_price,
            swing_high_roto=swing_high,
            swing_low_invalidation=stop_loss_clasico,
            divergencia_4h_activa=div_activa,
            rsi_4h_valor=round(rsi_val, 2),
            entrada_mercado_clasica=round(entry_price, 2),
            stop_loss_clasico=round(stop_loss_clasico, 2),
            take_profit_clasico=round(tp_clasico, 2),
            ratio_rr_clasico=self.rr_ratio,
            plan_escalamiento=plan_esc
        )
