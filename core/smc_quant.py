"""
smc_quant.py - Quantitative SMC & Microstructural Liquidity Formulator
Translates retail SMC heuristics (Order Blocks, Liquidity Sweeps/Traps, Fake vs Real Breakouts)
into deterministic, zero-lookahead mathematical algorithms.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any, Tuple
import math
from core.types import Candle

class SMCQuantEngine:
    """
    Evaluates microstructural supply/demand pools, order blocks,
    and breakout validity strictly over historical causal candles.
    """
    def __init__(self, swing_lookback: int = 10, volume_multiplier: float = 1.5):
        self.swing_lookback = swing_lookback
        self.volume_multiplier = volume_multiplier

    def find_swing_levels(self, candles: List[Candle]) -> Tuple[Optional[float], Optional[float]]:
        """
        Finds the most recent valid Swing High (Resistance/Buy-Side Liquidity)
        and Swing Low (Support/Sell-Side Liquidity) using strictly causal candles.
        """
        if len(candles) < self.swing_lookback * 2 + 1:
            return None, None

        # Exclude the very latest candles to avoid lookahead peak-finding
        # A swing high at index i requires candles[i].high > candles[i-k].high and candles[i+k].high
        # Using causal past: swing identified at (len - 1 - swing_lookback)
        eval_idx = len(candles) - 1 - self.swing_lookback
        if eval_idx < self.swing_lookback:
            return None, None

        swing_high = None
        swing_low = None

        # Search backward for the most recent validated pivot
        for i in range(len(candles) - 1 - self.swing_lookback, self.swing_lookback - 1, -1):
            target = candles[i]
            is_high = True
            is_low = True
            
            for offset in range(1, self.swing_lookback + 1):
                if candles[i - offset].high >= target.high or candles[i + offset].high >= target.high:
                    is_high = False
                if candles[i - offset].low <= target.low or candles[i + offset].low <= target.low:
                    is_low = False
            
            if is_high and swing_high is None:
                swing_high = target.high
            if is_low and swing_low is None:
                swing_low = target.low
                
            if swing_high is not None and swing_low is not None:
                break

        return swing_high, swing_low

    def detect_order_block(self, candles: List[Candle]) -> Optional[Dict[str, Any]]:
        """
        Detects unmitigated Bullish or Bearish Order Blocks (OB).
        - Bullish OB: Bearish candle followed by an aggressive expansion candle (Body > 1.5x avg range, Vol > 1.5x avg).
        - Bearish OB: Bullish candle followed by an aggressive downward expansion candle.
        """
        if len(candles) < 5:
            return None

        # Calculate average range and volume over available lookback
        lookback_window = min(len(candles) - 1, 15)
        ranges = [c.high - c.low for c in candles[-lookback_window-1:-1]]
        vols = [c.volume for c in candles[-lookback_window-1:-1]]
        avg_range = sum(ranges) / len(ranges) if ranges else 1.0
        avg_vol = sum(vols) / len(vols) if vols else 1.0

        current = candles[-1]

        # Scan the last 6 candles for potential order blocks
        for i in range(len(candles) - 2, max(0, len(candles) - 8), -1):
            prior_candle = candles[i]
            expansion_candle = candles[i + 1]

            expansion_range = expansion_candle.high - expansion_candle.low
            expansion_vol = expansion_candle.volume

            # Condition 1: Expansion candle has institutional impulse
            if expansion_range >= avg_range * self.volume_multiplier and expansion_vol >= avg_vol * self.volume_multiplier:
                # Bullish OB check: Prior candle is bearish (close < open), expansion is bullish (close > open)
                if prior_candle.close < prior_candle.open and expansion_candle.close > expansion_candle.open:
                    ob_high = prior_candle.high
                    ob_low = prior_candle.low
                    # Check if subsequent candles (up to current) have not invalidated the OB (low < ob_low)
                    invalidated = any(c.low < ob_low for c in candles[i+2:])
                    # Check if current price is retracing into the OB zone
                    in_zone = (current.low <= ob_high and current.close >= ob_low)
                    if not invalidated and in_zone:
                        return {
                            "side": "bullish",
                            "high": ob_high,
                            "low": ob_low,
                            "candle_ts": prior_candle.timestamp,
                            "displacement_ratio": expansion_range / avg_range
                        }

                # Bearish OB check: Prior candle is bullish (close > open), expansion is bearish (close < open)
                if prior_candle.close > prior_candle.open and expansion_candle.close < expansion_candle.open:
                    ob_high = prior_candle.high
                    ob_low = prior_candle.low
                    invalidated = any(c.high > ob_high for c in candles[i+2:])
                    in_zone = (current.high >= ob_low and current.close <= ob_high)
                    if not invalidated and in_zone:
                        return {
                            "side": "bearish",
                            "high": ob_high,
                            "low": ob_low,
                            "candle_ts": prior_candle.timestamp,
                            "displacement_ratio": expansion_range / avg_range
                        }

        return None

    def analyze_breakout_and_traps(
        self, candles: List[Candle], swing_high: Optional[float], swing_low: Optional[float]
    ) -> Tuple[str, bool]:
        """
        Classifies current candle action relative to key liquidity pools (Swing High/Low):
        Returns: (breakout_type: "real_breakout" | "fake_breakout" | "none", liquidity_sweep: bool)
        """
        if not candles or swing_high is None or swing_low is None:
            return "none", False

        curr = candles[-1]
        candle_range = curr.high - curr.low
        if candle_range <= 0:
            return "none", False

        # Upper Liquidity Sweep / Bearish Trap (Fake Breakout above Resistance)
        if curr.high > swing_high and curr.close <= swing_high:
            upper_wick = curr.high - max(curr.open, curr.close)
            if upper_wick >= 0.40 * candle_range:
                # Price swept buy-side liquidity but failed to hold: Liquidity Trap
                return "fake_breakout", True

        # Lower Liquidity Sweep / Bullish Trap (Fake Breakout below Support)
        if curr.low < swing_low and curr.close >= swing_low:
            lower_wick = min(curr.open, curr.close) - curr.low
            if lower_wick >= 0.40 * candle_range:
                # Price swept sell-side liquidity and reclaimed level: Bullish Trap / Stop Hunt
                return "fake_breakout", True

        # Real Breakout Upside
        if curr.close > swing_high:
            body = abs(curr.close - curr.open)
            if body >= 0.55 * candle_range:
                return "real_breakout", False

        # Real Breakout Downside
        if curr.close < swing_low:
            body = abs(curr.close - curr.open)
            if body >= 0.55 * candle_range:
                return "real_breakout", False

        return "none", False
