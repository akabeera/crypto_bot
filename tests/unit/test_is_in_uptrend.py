import unittest
import numpy as np
import pandas as pd

from utils.strategies_enhanced import is_in_uptrend


class TestIsInUptrend(unittest.TestCase):

    def _make_candles(self, close_prices):
        """Helper to create a candles DataFrame from a list of close prices."""
        return pd.DataFrame({'close': close_prices})

    def _make_trend_config(self, enabled=True, short_ema=10, long_ema=30):
        return {
            "enabled": enabled,
            "short_ema_period": short_ema,
            "long_ema_period": long_ema,
        }

    def test_uptrend_detected(self):
        """When price > EMA_short > EMA_long, should return True."""
        # Create a steadily rising price series (40 candles going from 100 to 139)
        prices = [100 + i for i in range(40)]
        candles_df = self._make_candles(prices)
        config = self._make_trend_config(enabled=True, short_ema=5, long_ema=10)

        result = is_in_uptrend(candles_df, config)
        self.assertTrue(result)

    def test_downtrend_not_detected_as_uptrend(self):
        """When price < EMA_short < EMA_long, should return False."""
        # Create a steadily falling price series
        prices = [139 - i for i in range(40)]
        candles_df = self._make_candles(prices)
        config = self._make_trend_config(enabled=True, short_ema=5, long_ema=10)

        result = is_in_uptrend(candles_df, config)
        self.assertFalse(result)

    def test_sideways_market(self):
        """When price is flat/choppy, EMAs converge and uptrend should not trigger."""
        prices = [100.0] * 40
        candles_df = self._make_candles(prices)
        config = self._make_trend_config(enabled=True, short_ema=5, long_ema=10)

        result = is_in_uptrend(candles_df, config)
        # Flat market: price == EMA_short == EMA_long, not strictly greater
        self.assertFalse(result)

    def test_disabled_config_returns_false(self):
        """When trend_confirmation is disabled, should always return False."""
        prices = [100 + i for i in range(40)]
        candles_df = self._make_candles(prices)
        config = self._make_trend_config(enabled=False)

        result = is_in_uptrend(candles_df, config)
        self.assertFalse(result)

    def test_none_config_returns_false(self):
        """When trend_config is None, should return False."""
        prices = [100 + i for i in range(40)]
        candles_df = self._make_candles(prices)

        result = is_in_uptrend(candles_df, None)
        self.assertFalse(result)

    def test_empty_config_returns_false(self):
        """When trend_config is empty dict, should return False."""
        prices = [100 + i for i in range(40)]
        candles_df = self._make_candles(prices)

        result = is_in_uptrend(candles_df, {})
        self.assertFalse(result)

    def test_insufficient_data_returns_false(self):
        """When there aren't enough candles for the long EMA, should return False."""
        prices = [100 + i for i in range(5)]  # Only 5 candles
        candles_df = self._make_candles(prices)
        config = self._make_trend_config(enabled=True, short_ema=10, long_ema=30)

        result = is_in_uptrend(candles_df, config)
        self.assertFalse(result)

    def test_uptrend_to_reversal(self):
        """Rising trend that reverses at the end should not be uptrend."""
        # Rise then sharp drop
        prices = [100 + i for i in range(35)] + [110, 105, 100, 95, 90]
        candles_df = self._make_candles(prices)
        config = self._make_trend_config(enabled=True, short_ema=5, long_ema=10)

        result = is_in_uptrend(candles_df, config)
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
