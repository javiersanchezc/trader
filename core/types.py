from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Optional, Dict, Any
import json
import time

class Regime(str, Enum):
    TRENDING = "trending"
    MEAN_REVERTING = "mean_reverting"
    HIGH_VOL = "high_vol"
    CRISIS = "crisis"

class Direction(str, Enum):
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"

class RiskState(str, Enum):
    SAFE = "safe"
    NEAR_LIMIT = "near_limit"
    REDUCE = "reduce"

class ToxicFlow(str, Enum):
    BENIGN = "benign"
    ADVERSE_QUOTE = "adverse_quote"
    INFORMED_SWEEP = "informed_sweep"
    TOXIC_CLUSTER = "toxic_cluster"

@dataclass(frozen=True)
class Candle:
    timestamp: int  # ms epoch (causal close time)
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass(frozen=True)
class OrderBookSnapshot:
    timestamp: int
    bids: List[Tuple[float, float]]  # [(price, size), ...] descending
    asks: List[Tuple[float, float]]  # [(price, size), ...] ascending

@dataclass
class MarketState:
    symbol: str
    causal_timestamp: int
    mid_price: float
    spread_bps: float
    orderbook_imbalance: float  # [-1.0 (100% asks), +1.0 (100% bids)]
    realized_volatility: float  # annualized volatility
    current_inventory: float    # units held
    current_drawdown: float     # 0.0 to 1.0 (e.g. 0.05 = 5%)
    # SMC Quantitative Metrics (translated from chart heuristics to microstructural metrics)
    detected_order_block: Optional[Dict[str, Any]] = None
    liquidity_sweep_detected: bool = False
    breakout_type: str = "none" # "none", "fake_breakout", "real_breakout"
    
    def to_compact_token_state(self) -> str:
        """
        Generates an ultra-compact numeric state string guaranteed < 400 tokens
        for the Reflex LLM/Heuristic model, strictly free of lookahead bias.
        """
        payload = {
            "s": self.symbol,
            "ts": self.causal_timestamp,
            "mid": round(self.mid_price, 4),
            "spd_bps": round(self.spread_bps, 2),
            "imb": round(self.orderbook_imbalance, 3),
            "rvol": round(self.realized_volatility, 4),
            "inv": round(self.current_inventory, 4),
            "dd": round(self.current_drawdown, 4),
            "smc": {
                "ob": 1 if self.detected_order_block else 0,
                "ob_type": self.detected_order_block.get("side") if self.detected_order_block else "none",
                "swp": 1 if self.liquidity_sweep_detected else 0,
                "brk": self.breakout_type
            }
        }
        return json.dumps(payload, separators=(',', ':'))

@dataclass(frozen=True)
class DecisionSchema:
    regime: Regime
    direction: Direction
    confidence: float          # Calibrated probability [0.0, 1.0]
    setup_quality: int         # 0, 1, 2, 3
    risk_state: RiskState
    toxic_flow: ToxicFlow
    rationale: str
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))

    def validate(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence {self.confidence} must be between 0.0 and 1.0")
        if self.setup_quality not in (0, 1, 2, 3):
            raise ValueError(f"Setup quality {self.setup_quality} must be 0, 1, 2, or 3")

@dataclass
class Order:
    order_id: str
    symbol: str
    side: str  # "buy" | "sell"
    quantity: float
    price: float
    order_type: str  # "limit" | "market"
    timestamp: int
    status: str = "pending" # "pending", "filled", "rejected", "cancelled"

@dataclass
class Position:
    symbol: str
    size: float = 0.0
    entry_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

@dataclass
class RiskParameters:
    max_drawdown_limit: float = 0.15      # Hard limit 15%
    max_daily_loss: float = 0.03          # Hard limit 3%
    max_leverage: float = 3.0
    max_position_notional: float = 50_000.0
    quarter_kelly_fraction: float = 0.25  # 1/4 Kelly for safety
    min_confidence_threshold: float = 0.80
    min_setup_quality: int = 2
    kill_switch_active: bool = False
