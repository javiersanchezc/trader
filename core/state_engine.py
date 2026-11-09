"""
state_engine.py - Causal Microstructural State Compiler
Compiles raw orderbook snapshots and historical candles into an immutable,
compact numeric MarketState (< 400 tokens) with zero lookahead bias.
"""

from __future__ import annotations
import math
from typing import List, Optional
from core.types import Candle, OrderBookSnapshot, MarketState
from core.smc_quant import SMCQuantEngine

class StateEngine:
    def __init__(self, symbol: str, book_depth_levels: int = 5, vol_lookback: int = 20):
        self.symbol = symbol
        self.book_depth_levels = book_depth_levels
        self.vol_lookback = vol_lookback
        self.smc_engine = SMCQuantEngine(swing_lookback=5, volume_multiplier=1.4)
        self.peak_equity: float = 100_000.0

    def compute_mid_and_spread(self, book: OrderBookSnapshot) -> tuple[float, float]:
        if not book.bids or not book.asks:
            raise ValueError("OrderBookSnapshot cannot have empty bids or asks")
        best_bid = book.bids[0][0]
        best_ask = book.asks[0][0]
        if best_bid >= best_ask:
            # Crossed order book or invalid feed
            best_bid, best_ask = min(best_bid, best_ask), max(best_bid, best_ask)
            
        mid = (best_bid + best_ask) / 2.0
        spread_bps = ((best_ask - best_bid) / mid) * 10_000.0 if mid > 0 else 0.0
        return mid, spread_bps

    def compute_orderbook_imbalance(self, book: OrderBookSnapshot) -> float:
        top_bids = book.bids[:self.book_depth_levels]
        top_asks = book.asks[:self.book_depth_levels]
        bid_vol = sum(size for _, size in top_bids)
        ask_vol = sum(size for _, size in top_asks)
        total_vol = bid_vol + ask_vol
        if total_vol == 0:
            return 0.0
        return (bid_vol - ask_vol) / total_vol

    def compute_realized_volatility(self, candles: List[Candle]) -> float:
        """
        Computes rolling annualized realized volatility from causal close log returns.
        """
        if len(candles) < 3:
            return 0.0
        lookback = min(len(candles), self.vol_lookback)
        sample = candles[-lookback:]
        log_returns = []
        for i in range(1, len(sample)):
            c_prev = sample[i - 1].close
            c_curr = sample[i].close
            if c_prev > 0 and c_curr > 0:
                log_returns.append(math.log(c_curr / c_prev))

        if len(log_returns) < 2:
            return 0.0

        mean_ret = sum(log_returns) / len(log_returns)
        var = sum((r - mean_ret) ** 2 for r in log_returns) / (len(log_returns) - 1)
        std_ret = math.sqrt(max(0.0, var))
        # Annualized standard deviation (assuming 1-hour candles: sqrt(24 * 365) = sqrt(8760))
        return std_ret * math.sqrt(8760)

    def compute_drawdown(self, current_equity: float) -> float:
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        if self.peak_equity <= 0:
            return 0.0
        return max(0.0, (self.peak_equity - current_equity) / self.peak_equity)

    def compile_state(
        self,
        book: OrderBookSnapshot,
        candles: List[Candle],
        current_inventory: float,
        current_equity: float
    ) -> MarketState:
        """
        Constructs the causal MarketState ensuring zero lookahead bias.
        """
        causal_timestamp = book.timestamp
        mid_price, spread_bps = self.compute_mid_and_spread(book)
        imbalance = self.compute_orderbook_imbalance(book)
        realized_vol = self.compute_realized_volatility(candles)
        drawdown = self.compute_drawdown(current_equity)

        # SMC quantitative signals
        swing_high, swing_low = self.smc_engine.find_swing_levels(candles)
        breakout_type, is_sweep = self.smc_engine.analyze_breakout_and_traps(candles, swing_high, swing_low)
        ob = self.smc_engine.detect_order_block(candles)

        return MarketState(
            symbol=self.symbol,
            causal_timestamp=causal_timestamp,
            mid_price=mid_price,
            spread_bps=spread_bps,
            orderbook_imbalance=imbalance,
            realized_volatility=realized_vol,
            current_inventory=current_inventory,
            current_drawdown=drawdown,
            detected_order_block=ob,
            liquidity_sweep_detected=is_sweep,
            breakout_type=breakout_type
        )
