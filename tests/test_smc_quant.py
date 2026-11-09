import unittest
from core.types import Candle
from core.smc_quant import SMCQuantEngine

class TestSMCQuantEngine(unittest.TestCase):
    def setUp(self):
        self.engine = SMCQuantEngine(swing_lookback=3, volume_multiplier=1.4)

    def test_swing_levels_causal_no_lookahead(self):
        # Construct candles with a swing high at index 5
        candles = []
        base = 100.0
        # 0 to 4: rising
        for i in range(5):
            candles.append(Candle(timestamp=i*1000, open=base+i, high=base+i+1, low=base+i-0.5, close=base+i+0.8, volume=10.0))
        # 5: Peak (high = 115)
        candles.append(Candle(timestamp=5000, open=105, high=115, low=104, close=110, volume=20.0))
        # 6 to 10: falling
        for i in range(6, 12):
            candles.append(Candle(timestamp=i*1000, open=100-(i-5), high=101-(i-5), low=98-(i-5), close=99-(i-5), volume=10.0))

        swing_high, swing_low = self.engine.find_swing_levels(candles)
        self.assertIsNotNone(swing_high)
        self.assertEqual(swing_high, 115.0)

    def test_fake_breakout_liquidity_sweep(self):
        # Candle sweeps swing high of 115.0 up to 118.0 but closes at 112.0 with big upper wick
        sweep_candle = Candle(
            timestamp=20000,
            open=111.0,
            high=118.0,
            low=110.0,
            close=112.0,  # High = 118, Close = 112 <= 115, Upper wick = 118 - 112 = 6 (6/8 = 75% range)
            volume=50.0
        )
        candles = [sweep_candle]
        breakout_type, is_sweep = self.engine.analyze_breakout_and_traps(candles, swing_high=115.0, swing_low=95.0)
        self.assertEqual(breakout_type, "fake_breakout")
        self.assertTrue(is_sweep)

    def test_real_breakout(self):
        # Candle breaks cleanly above 115.0, closing at 122.0
        strong_breakout = Candle(
            timestamp=21000,
            open=114.0,
            high=123.0,
            low=113.5,
            close=122.0,  # Body = 122 - 114 = 8, Range = 123 - 113.5 = 9.5 (body/range > 0.55)
            volume=80.0
        )
        candles = [strong_breakout]
        breakout_type, is_sweep = self.engine.analyze_breakout_and_traps(candles, swing_high=115.0, swing_low=95.0)
        self.assertEqual(breakout_type, "real_breakout")
        self.assertFalse(is_sweep)

    def test_bullish_order_block_detection(self):
        candles = []
        # 10 baseline candles
        for i in range(10):
            candles.append(Candle(timestamp=i*1000, open=100, high=101, low=99, close=100.2, volume=10.0))
        
        # Bearish candle (the Order Block candidate)
        candles.append(Candle(timestamp=10000, open=100.5, high=101.0, low=99.0, close=99.2, volume=12.0))
        
        # Massive bullish expansion candle (Body & Vol > 1.5x avg)
        candles.append(Candle(timestamp=11000, open=99.5, high=106.0, low=99.4, close=105.8, volume=40.0))
        
        # Subsequent retracement into the OB zone (low=99.0, high=101.0)
        candles.append(Candle(timestamp=12000, open=104.0, high=104.2, low=100.0, close=100.5, volume=15.0))

        ob = self.engine.detect_order_block(candles)
        self.assertIsNotNone(ob)
        self.assertEqual(ob["side"], "bullish")
        self.assertEqual(ob["high"], 101.0)
        self.assertEqual(ob["low"], 99.0)

if __name__ == "__main__":
    unittest.main()
