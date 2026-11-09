"""
risk_layer.py - Guardián Determinista de Riesgo y Ejecución
Compuertas inmutables en código duro, dimensionamiento por Quarter-Kelly
y botón de parada de emergencia (kill-switch).
El modelo del Reflejo solo juzga; este motor tiene la autoridad absoluta sobre el capital.
"""

from __future__ import annotations
from typing import Optional, Tuple
from core.types import (
    DecisionSchema,
    MarketState,
    Order,
    Position,
    RiskParameters,
    Regime,
    Direction,
    RiskState
)

class RiskEngine:
    def __init__(self, params: Optional[RiskParameters] = None, starting_equity: float = 100_000.0):
        self.params = params or RiskParameters()
        self.starting_equity = starting_equity
        self.daily_starting_equity = starting_equity
        self.current_equity = starting_equity
        self.daily_realized_loss = 0.0
        self.kill_switch_triggered = False
        self.kill_switch_reason = ""
        self.brain_escalation_required = False
        self.escalation_reason = ""

    def trigger_kill_switch(self, reason: str) -> None:
        self.kill_switch_triggered = True
        self.kill_switch_reason = reason

    def reset_daily_equity(self, current_equity: float) -> None:
        self.daily_starting_equity = current_equity
        self.daily_realized_loss = 0.0

    def evaluate_execution_gates(self, decision: DecisionSchema, state: MarketState) -> Tuple[bool, str]:
        """
        Compuertas de Ejecución Inmutables:
        Regla 1: El botón de parada de emergencia (kill-switch) no debe estar activo.
        Regla 2: El drawdown no debe superar el límite estricto (<= 15%).
        Regla 3: La pérdida diaria no debe superar el límite (<= 3%).
        Regla 4: Régimen de crisis o baja confianza (< 0.60) escala al Cerebro y congela órdenes.
        Regla 5: Calidad de configuración (setup_quality) >= 2.
        Regla 6: Confianza de dirección > 0.80.
        Regla 7: Estado de riesgo == 'safe' (seguro).
        Regla 8: El spread debe ser razonable (<= 25 bps) para evitar enrutamiento tóxico.
        """
        # 1. Kill switch
        if self.kill_switch_triggered or self.params.kill_switch_active:
            return False, f"Botón de emergencia activo (Kill-switch): {self.kill_switch_reason or 'Activación manual'}"

        # 2. Compuerta de Drawdown Máximo
        if state.current_drawdown > self.params.max_drawdown_limit:
            self.trigger_kill_switch(f"Ruptura de drawdown máximo: {state.current_drawdown * 100:.2f}% > {self.params.max_drawdown_limit * 100:.1f}%")
            return False, self.kill_switch_reason

        # 3. Compuerta de Pérdida Diaria
        daily_loss_pct = (self.daily_starting_equity - self.current_equity) / self.daily_starting_equity
        if daily_loss_pct > self.params.max_daily_loss:
            return False, f"Límite de pérdida diaria superado: {daily_loss_pct * 100:.2f}% > {self.params.max_daily_loss * 100:.1f}%"

        # 4. Escalado Estructural al Cerebro
        if decision.regime == Regime.CRISIS or decision.confidence < 0.60:
            self.brain_escalation_required = True
            self.escalation_reason = f"Confianza {decision.confidence:.2f} < 0.60 o Régimen {decision.regime.value}"
            return False, f"Escalado al Cerebro: {self.escalation_reason}"

        # 5. Compuerta de Calidad de Configuración
        if decision.setup_quality < self.params.min_setup_quality:
            return False, f"Calidad de configuración {decision.setup_quality} por debajo del umbral {self.params.min_setup_quality}"

        # 6. Compuerta de Dirección y Confianza
        if decision.direction == Direction.NEUTRAL:
            return False, "Dirección neutral; no se requiere generación de órdenes"

        if decision.confidence <= self.params.min_confidence_threshold:
            return False, f"Confianza {decision.confidence:.2f} <= {self.params.min_confidence_threshold}"

        # 7. Compuerta de Estado de Riesgo
        if decision.risk_state != RiskState.SAFE:
            return False, f"El estado de riesgo '{decision.risk_state.value}' no es 'seguro' (safe)"

        # 8. Compuerta de Toxicidad por Spread
        if state.spread_bps > 25.0:
            return False, f"Spread de mercado excesivo: {state.spread_bps:.1f} bps"

        return True, "Todas las compuertas superadas con éxito"

    def compute_quarter_kelly_size(
        self,
        confidence: float,
        mid_price: float,
        reward_risk_ratio: float = 1.8
    ) -> float:
        """
        Calcula el tamaño de la posición en moneda base usando Quarter-Kelly:
        f* = (b * p - q) / b
        f_qk = 0.25 * f*
        Acotado por max_position_notional y límites de capital.
        """
        p = confidence
        q = 1.0 - p
        b = max(1.0, reward_risk_ratio)

        kelly_full = (b * p - q) / b
        if kelly_full <= 0:
            return 0.0

        fraction = kelly_full * self.params.quarter_kelly_fraction
        # Tope conservador máximo por operación (15% del patrimonio)
        fraction = min(fraction, 0.15)

        target_notional = self.current_equity * fraction
        target_notional = min(target_notional, self.params.max_position_notional)

        if mid_price <= 0:
            return 0.0

        raw_size = target_notional / mid_price
        return round(raw_size, 4)

    def size_and_create_order(
        self,
        decision: DecisionSchema,
        state: MarketState,
        position: Position,
        order_id: str
    ) -> Optional[Order]:
        """
        Valida compuertas y genera la Orden tipada. Retorna None si las compuertas fallan.
        """
        passed, reason = self.evaluate_execution_gates(decision, state)
        if not passed:
            return None

        side = "buy" if decision.direction == Direction.LONG else "sell"

        # Evitar sobreexposición acumulada en la misma dirección
        if side == "buy" and position.size > 0 and (position.size * state.mid_price) >= self.params.max_position_notional:
            return None
        if side == "sell" and position.size < 0 and (abs(position.size) * state.mid_price) >= self.params.max_position_notional:
            return None

        quantity = self.compute_quarter_kelly_size(decision.confidence, state.mid_price)
        if quantity <= 0:
            return None

        return Order(
            order_id=order_id,
            symbol=state.symbol,
            side=side,
            quantity=quantity,
            price=state.mid_price,
            order_type="market",
            timestamp=state.causal_timestamp,
            status="pending"
        )
