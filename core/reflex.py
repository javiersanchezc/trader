"""
reflex.py - Motor de Decisión Sub-100ms
Consume el estado numérico compacto (< 400 tokens) y produce
objetos DecisionSchema estrictamente tipados con probabilidades calibradas.
"""

from __future__ import annotations
import time
from typing import Optional
from core.types import (
    MarketState,
    DecisionSchema,
    Regime,
    Direction,
    RiskState,
    ToxicFlow
)

class ReflexEngine:
    """
    Evaluador determinista de ejecución en sub-100ms.
    Procesa estados compactos y emite DecisionSchema tipado.
    """
    def __init__(self, high_vol_threshold: float = 0.85):
        self.high_vol_threshold = high_vol_threshold

    def evaluate(self, state: MarketState) -> DecisionSchema:
        start_time = time.perf_counter()

        # 1. Identificación del Régimen de Mercado
        if state.realized_volatility > self.high_vol_threshold:
            regime = Regime.HIGH_VOL
        elif state.spread_bps > 30.0:
            regime = Regime.CRISIS
        elif state.breakout_type == "real_breakout":
            regime = Regime.TRENDING
        else:
            regime = Regime.MEAN_REVERTING

        # 2. Evaluación de Flujo Tóxico
        if state.spread_bps > 20.0 or abs(state.orderbook_imbalance) > 0.80:
            toxic_flow = ToxicFlow.ADVERSE_QUOTE
        elif state.liquidity_sweep_detected:
            toxic_flow = ToxicFlow.INFORMED_SWEEP
        else:
            toxic_flow = ToxicFlow.BENIGN

        # 3. Evaluación de Dirección y Calidad (SMC Cuantitativo & Microestructura)
        direction = Direction.NEUTRAL
        setup_quality = 0
        confidence = 0.50
        rationale_parts = []

        # Caso A: Retesteo de Order Block Alcista + Desbalance L2 Positivo
        if state.detected_order_block and state.detected_order_block.get("side") == "bullish":
            if state.orderbook_imbalance > 0.15:
                direction = Direction.LONG
                setup_quality = 3
                confidence = 0.86
                rationale_parts.append("Retesteo de Order Block alcista confirmado por fuerte desbalance comprador en el libro L2")
            else:
                direction = Direction.LONG
                setup_quality = 2
                confidence = 0.78
                rationale_parts.append("Retesteo de Order Block alcista con profundidad de libro neutral")

        # Caso B: Retesteo de Order Block Bajista + Desbalance L2 Negativo
        elif state.detected_order_block and state.detected_order_block.get("side") == "bearish":
            if state.orderbook_imbalance < -0.15:
                direction = Direction.SHORT
                setup_quality = 3
                confidence = 0.85
                rationale_parts.append("Retesteo de Order Block bajista confirmado por fuerte presión vendedora en el libro")
            else:
                direction = Direction.SHORT
                setup_quality = 2
                confidence = 0.77
                rationale_parts.append("Retesteo de Order Block bajista con profundidad vendedora moderada")

        # Caso C: Barrido de Liquidez / Ruptura Falsa (Trampa de Reversión)
        elif state.liquidity_sweep_detected and state.breakout_type == "fake_breakout":
            if state.orderbook_imbalance < 0:
                direction = Direction.SHORT
                setup_quality = 2
                confidence = 0.82
                rationale_parts.append("Barrido de liquidez de compra con absorción de delta negativo (Trampa de Toros)")
            else:
                direction = Direction.LONG
                setup_quality = 2
                confidence = 0.82
                rationale_parts.append("Barrido de liquidez de venta y recuperación de nivel (Trampa de Osos)")

        # Caso D: Expansión por Ruptura Real
        elif state.breakout_type == "real_breakout":
            if state.orderbook_imbalance > 0.25:
                direction = Direction.LONG
                setup_quality = 2
                confidence = 0.81
                rationale_parts.append("Ruptura alcista real respaldada por profundidad en el libro de órdenes")
            elif state.orderbook_imbalance < -0.25:
                direction = Direction.SHORT
                setup_quality = 2
                confidence = 0.81
                rationale_parts.append("Ruptura bajista real respaldada por pesado muro de venta")

        # Caso por Defecto: Neutral
        if direction == Direction.NEUTRAL:
            setup_quality = 0
            confidence = 0.50
            rationale_parts.append("Sin confluencia estructural de alta probabilidad")

        # 4. Evaluación de Estado de Riesgo
        if state.current_drawdown > 0.10:
            risk_state = RiskState.REDUCE
        elif state.current_drawdown > 0.06:
            risk_state = RiskState.NEAR_LIMIT
        else:
            risk_state = RiskState.SAFE

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        rationale_str = f"[{elapsed_ms:.2f}ms] " + "; ".join(rationale_parts)

        decision = DecisionSchema(
            regime=regime,
            direction=direction,
            confidence=confidence,
            setup_quality=setup_quality,
            risk_state=risk_state,
            toxic_flow=toxic_flow,
            rationale=rationale_str,
            timestamp=state.causal_timestamp
        )
        decision.validate()
        return decision
