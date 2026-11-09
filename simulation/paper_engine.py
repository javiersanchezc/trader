"""
paper_engine.py - 24/7 Paper Trading & Market Replay Harness
Simulates high-fidelity execution with realistic slippage, exchange taker fees,
and strict two-layer (Brain/Reflex) coordination.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
import time
from core.types import (
    Candle,
    OrderBookSnapshot,
    Position,
    Order,
    MarketState,
    DecisionSchema,
    RiskParameters
)
from core.state_engine import StateEngine
from core.reflex import ReflexEngine
from core.risk_layer import RiskEngine
from core.brain import BrainEngine

class PaperTradingHarness:
    def __init__(
        self,
        symbol: str = "BTC/USDT",
        initial_balance: float = 100_000.0,
        taker_fee_bps: float = 4.0,  # 0.04% institutional VIP taker fee
        slippage_bps: float = 2.0    # 0.02% conservative execution slippage
    ):
        self.symbol = symbol
        self.balance = initial_balance
        self.taker_fee_bps = taker_fee_bps
        self.slippage_bps = slippage_bps
        
        self.position = Position(symbol=symbol)
        self.state_engine = StateEngine(symbol=symbol)
        self.reflex_engine = ReflexEngine()
        self.risk_engine = RiskEngine(RiskParameters(), starting_equity=initial_balance)
        self.brain_engine = BrainEngine()

        self.execution_history: List[Order] = []
        self.equity_curve: List[float] = [initial_balance]

    def get_equity(self, current_price: float) -> float:
        # Cash balance + mark-to-market position value
        position_market_value = self.position.size * current_price
        return self.balance + position_market_value

    def process_tick(
        self,
        book: OrderBookSnapshot,
        historical_candles: List[Candle]
    ) -> Dict[str, Any]:
        """
        Processes a single market tick through the full two-layer architecture.
        """
        # 1. Update equity & inventory
        mid_price = (book.bids[0][0] + book.asks[0][0]) / 2.0
        current_equity = self.get_equity(mid_price)
        self.risk_engine.current_equity = current_equity
        self.equity_curve.append(current_equity)

        # 2. State Engine: compile compact numeric state (< 400 tokens)
        state: MarketState = self.state_engine.compile_state(
            book=book,
            candles=historical_candles,
            current_inventory=self.position.size,
            current_equity=current_equity
        )

        # 3. Reflex Engine: high-speed evaluation (<100ms)
        decision: DecisionSchema = self.reflex_engine.evaluate(state)

        # 4. Deterministic Risk Layer: hardcoded gates & Quarter-Kelly sizing
        passed, gate_reason = self.risk_engine.evaluate_execution_gates(decision, state)
        order_placed: Optional[Order] = None

        if passed:
            order_id = f"ORD_{book.timestamp}_{len(self.execution_history) + 1}"
            order_placed = self.risk_engine.size_and_create_order(decision, state, self.position, order_id)

        # 5. Execution Simulation (if order was generated)
        executed_trade = None
        if order_placed:
            # Apply slippage & fees
            slippage_mult = (1.0 + (self.slippage_bps / 10000.0)) if order_placed.side == "buy" else (1.0 - (self.slippage_bps / 10000.0))
            fill_price = order_placed.price * slippage_mult
            fee = (fill_price * order_placed.quantity) * (self.taker_fee_bps / 10000.0)

            # Update inventory & cash
            if order_placed.side == "buy":
                # Average entry price calculation
                prev_notional = self.position.size * self.position.entry_price if self.position.size > 0 else 0.0
                new_notional = prev_notional + (order_placed.quantity * fill_price)
                new_size = self.position.size + order_placed.quantity
                self.position.entry_price = new_notional / new_size if new_size > 0 else fill_price
                self.position.size = new_size
                self.balance -= (order_placed.quantity * fill_price + fee)
            else: # sell / short
                new_size = self.position.size - order_placed.quantity
                self.position.size = new_size
                self.balance += (order_placed.quantity * fill_price - fee)

            order_placed.status = "filled"
            self.execution_history.append(order_placed)
            executed_trade = {
                "order_id": order_placed.order_id,
                "side": order_placed.side,
                "qty": order_placed.quantity,
                "fill_price": fill_price,
                "fee": fee
            }

        # 6. Log into Brain's continuous calibration trail
        # Compute forward return proxy for calibration
        next_ret_bps = ((historical_candles[-1].close - historical_candles[-2].close) / historical_candles[-2].close) * 10000.0 if len(historical_candles) >= 2 else 0.0
        directional_ret = next_ret_bps if decision.direction.value == "long" else (-next_ret_bps if decision.direction.value == "short" else 0.0)

        self.brain_engine.log_decision_and_outcome(
            timestamp=state.causal_timestamp,
            symbol=self.symbol,
            direction=decision.direction.value,
            confidence=decision.confidence,
            setup_quality=decision.setup_quality,
            executed=order_placed is not None,
            rejection_reason=gate_reason if not passed else None,
            actual_return_bps=directional_ret
        )

        return {
            "timestamp": state.causal_timestamp,
            "mid": mid_price,
            "decision": decision,
            "gate_passed": passed,
            "gate_reason": gate_reason,
            "order": executed_trade,
            "equity": self.get_equity(mid_price)
        }
