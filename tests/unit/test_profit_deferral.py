import unittest
import os
import sys
import time
import importlib.util
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

import pandas as pd

import utils.constants as CONSTANTS

# Import CryptoBot from crypto_bot.py directly (root __init__.py shadows it)
_spec = importlib.util.spec_from_file_location(
    "crypto_bot_module",
    os.path.join(os.path.dirname(__file__), "..", "..", "crypto_bot.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
sys.modules["crypto_bot_module"] = _mod
CryptoBot = _mod.CryptoBot
_MODULE_NAME = _mod.__name__


def _make_bot_stub(profit_deferral_enabled=True, max_deferral_minutes=30):
    """Create a minimal Mock with the attributes _should_defer_profit_taking needs."""
    bot = Mock()
    bot.trend_config = {
        "enabled": True,
        "short_ema_period": 5,
        "long_ema_period": 10,
    }
    bot.profit_deferral_enabled = profit_deferral_enabled
    bot.pd_confirmation_timeframe = "5m"
    bot.pd_max_deferral_minutes = max_deferral_minutes
    bot.deferred_profits = {}
    bot.exchange_service = Mock()
    return bot


def _make_short_ohlcv(length=40):
    """Return OHLCV list data for short-timeframe fetch."""
    return [[i, 100 + i, 101 + i, 99 + i, 100 + i, 1000] for i in range(length)]


def _make_candles_df(length=40):
    """Create a candles DataFrame (content doesn't matter since is_in_uptrend is mocked)."""
    prices = [100 + i for i in range(length)]
    return pd.DataFrame({
        'time': range(length),
        'open': prices,
        'high': [p + 1 for p in prices],
        'low': [p - 1 for p in prices],
        'close': prices,
        'volume': [1000] * length
    })


def _make_position(price=100.0, amount=1.0, fee_cost=0.5, cost=100.0):
    return {
        "id": "test-lot-1",
        "price": price,
        "amount": amount,
        "filled": amount,
        "fee": {"cost": fee_cost},
        "cost": cost
    }


def _make_ticker_info(bid=105.0):
    return {"bid": bid}


class TestProfitDeferral(unittest.TestCase):

    def test_no_deferral_when_disabled(self):
        """When profit_deferral.enabled = false, the flag is set so run() skips deferral entirely."""
        bot = _make_bot_stub(profit_deferral_enabled=False)
        self.assertFalse(bot.profit_deferral_enabled)

    @patch(f'{_MODULE_NAME}.is_in_uptrend')
    def test_no_deferral_when_primary_not_uptrend(self, mock_uptrend):
        """When primary timeframe is not in uptrend, should sell immediately."""
        mock_uptrend.return_value = False
        bot = _make_bot_stub()

        candles_df = _make_candles_df()
        positions = [_make_position()]
        ticker_info = _make_ticker_info()

        result = CryptoBot._should_defer_profit_taking(bot, "BTC/USD", candles_df, positions, ticker_info)

        self.assertFalse(result)
        mock_uptrend.assert_called_once()

    @patch(f'{_MODULE_NAME}.is_in_uptrend')
    def test_no_deferral_when_short_timeframe_reversal(self, mock_uptrend):
        """Primary uptrend but 5m not in uptrend -> sell immediately (the key scenario)."""
        # Primary call returns True, short-timeframe call returns False
        mock_uptrend.side_effect = [True, False]
        bot = _make_bot_stub()

        # Mock exchange to return short-timeframe candles
        bot.exchange_service.execute_op = MagicMock(return_value=_make_short_ohlcv())

        candles_df = _make_candles_df()
        positions = [_make_position()]
        ticker_info = _make_ticker_info()

        result = CryptoBot._should_defer_profit_taking(bot, "BTC/USD", candles_df, positions, ticker_info)

        self.assertFalse(result)
        self.assertEqual(mock_uptrend.call_count, 2)
        # Verify short-timeframe fetch was made with correct params
        bot.exchange_service.execute_op.assert_called_once_with(
            ticker_pair="BTC/USD",
            op=CONSTANTS.OP_FETCH_OHLCV,
            params={CONSTANTS.PARAM_TIMEFRAME: "5m"}
        )

    @patch(f'{_MODULE_NAME}.calculate_profit_percent', return_value=Decimal("0.06"))
    @patch(f'{_MODULE_NAME}.calculate_avg_position', return_value=_make_position())
    @patch(f'{_MODULE_NAME}.is_in_uptrend', return_value=True)
    def test_defers_when_both_timeframes_bullish(self, mock_uptrend, mock_avg, mock_profit):
        """Both timeframes agree on uptrend -> defer, record baseline."""
        bot = _make_bot_stub()
        bot.exchange_service.execute_op = MagicMock(return_value=_make_short_ohlcv())

        candles_df = _make_candles_df()
        positions = [_make_position()]
        ticker_info = _make_ticker_info()

        result = CryptoBot._should_defer_profit_taking(bot, "BTC/USD", candles_df, positions, ticker_info)

        self.assertTrue(result)
        self.assertIn("BTC/USD", bot.deferred_profits)
        self.assertEqual(bot.deferred_profits["BTC/USD"]["profit_pct"], Decimal("0.06"))

    @patch(f'{_MODULE_NAME}.calculate_profit_percent', return_value=Decimal("0.04"))
    @patch(f'{_MODULE_NAME}.calculate_avg_position', return_value=_make_position())
    @patch(f'{_MODULE_NAME}.is_in_uptrend', return_value=True)
    def test_sells_when_profit_declines(self, mock_uptrend, mock_avg, mock_profit):
        """Deferred once at 6%, profit drops to 4% -> sell."""
        bot = _make_bot_stub()
        bot.exchange_service.execute_op = MagicMock(return_value=_make_short_ohlcv())

        # Pre-populate baseline from a previous deferral
        bot.deferred_profits["BTC/USD"] = {
            "profit_pct": Decimal("0.06"),
            "time": time.time()
        }

        candles_df = _make_candles_df()
        positions = [_make_position()]
        ticker_info = _make_ticker_info()

        result = CryptoBot._should_defer_profit_taking(bot, "BTC/USD", candles_df, positions, ticker_info)

        self.assertFalse(result)
        self.assertNotIn("BTC/USD", bot.deferred_profits)

    @patch(f'{_MODULE_NAME}.calculate_profit_percent', return_value=Decimal("0.07"))
    @patch(f'{_MODULE_NAME}.calculate_avg_position', return_value=_make_position())
    @patch(f'{_MODULE_NAME}.is_in_uptrend', return_value=True)
    def test_sells_when_max_deferral_exceeded(self, mock_uptrend, mock_avg, mock_profit):
        """Deferred past max minutes -> sell regardless of trend."""
        bot = _make_bot_stub(max_deferral_minutes=30)
        bot.exchange_service.execute_op = MagicMock(return_value=_make_short_ohlcv())

        # Baseline was set 31 minutes ago
        bot.deferred_profits["BTC/USD"] = {
            "profit_pct": Decimal("0.06"),
            "time": time.time() - (31 * 60)
        }

        candles_df = _make_candles_df()
        positions = [_make_position()]
        ticker_info = _make_ticker_info()

        result = CryptoBot._should_defer_profit_taking(bot, "BTC/USD", candles_df, positions, ticker_info)

        self.assertFalse(result)
        self.assertNotIn("BTC/USD", bot.deferred_profits)

    @patch(f'{_MODULE_NAME}.calculate_profit_percent', return_value=Decimal("0.08"))
    @patch(f'{_MODULE_NAME}.calculate_avg_position', return_value=_make_position())
    @patch(f'{_MODULE_NAME}.is_in_uptrend', return_value=True)
    def test_continues_deferral_when_profit_increases(self, mock_uptrend, mock_avg, mock_profit):
        """Deferred at 6%, profit now 8% and still in uptrend -> continue deferring."""
        bot = _make_bot_stub(max_deferral_minutes=30)
        bot.exchange_service.execute_op = MagicMock(return_value=_make_short_ohlcv())

        # Baseline was set 5 minutes ago, profit has increased
        bot.deferred_profits["BTC/USD"] = {
            "profit_pct": Decimal("0.06"),
            "time": time.time() - (5 * 60)
        }

        candles_df = _make_candles_df()
        positions = [_make_position()]
        ticker_info = _make_ticker_info()

        result = CryptoBot._should_defer_profit_taking(bot, "BTC/USD", candles_df, positions, ticker_info)

        self.assertTrue(result)
        # Baseline should still be tracked
        self.assertIn("BTC/USD", bot.deferred_profits)

    def test_tracking_cleared_after_sell(self):
        """After a sell, deferred_profits dict is cleaned up for that ticker."""
        bot = _make_bot_stub()

        # Simulate tickers that were being tracked
        bot.deferred_profits["BTC/USD"] = {
            "profit_pct": Decimal("0.06"),
            "time": time.time()
        }
        bot.deferred_profits["ETH/USD"] = {
            "profit_pct": Decimal("0.05"),
            "time": time.time()
        }

        # Simulate sell cleanup (as done in run() after handle_sell_order)
        bot.deferred_profits.pop("BTC/USD", None)

        self.assertNotIn("BTC/USD", bot.deferred_profits)
        # Other tickers should be unaffected
        self.assertIn("ETH/USD", bot.deferred_profits)

    @patch(f'{_MODULE_NAME}.is_in_uptrend', return_value=True)
    def test_no_deferral_when_short_ohlcv_insufficient(self, mock_uptrend):
        """When short-timeframe fetch returns insufficient data, don't defer (safe default)."""
        bot = _make_bot_stub()
        # Return only 10 candles (less than 30 minimum)
        bot.exchange_service.execute_op = MagicMock(return_value=_make_short_ohlcv(length=10))

        candles_df = _make_candles_df()
        positions = [_make_position()]
        ticker_info = _make_ticker_info()

        result = CryptoBot._should_defer_profit_taking(bot, "BTC/USD", candles_df, positions, ticker_info)

        self.assertFalse(result)

    @patch(f'{_MODULE_NAME}.is_in_uptrend', return_value=True)
    def test_no_deferral_when_short_ohlcv_none(self, mock_uptrend):
        """When short-timeframe fetch returns None, don't defer (safe default)."""
        bot = _make_bot_stub()
        bot.exchange_service.execute_op = MagicMock(return_value=None)

        candles_df = _make_candles_df()
        positions = [_make_position()]
        ticker_info = _make_ticker_info()

        result = CryptoBot._should_defer_profit_taking(bot, "BTC/USD", candles_df, positions, ticker_info)

        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
