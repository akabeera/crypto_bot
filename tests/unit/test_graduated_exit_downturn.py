import unittest
import os
import sys
import time
import importlib.util
from decimal import Decimal
from unittest.mock import Mock

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
TradeAction = _mod.TradeAction


def _make_bot_stub(btc_downturn_threshold=Decimal("0.15")):
    """Create a minimal Mock with the attributes _check_graduated_exit needs."""
    bot = Mock()
    bot.demoted_coins = {}
    bot.ge_max_hold_days = 28
    bot.ge_max_loss_percent = Decimal("0.05")  # 5%
    bot.ge_loss_active_after_days = 14
    bot.ge_underperform_threshold = Decimal("0.10")  # 10%
    bot.ge_btc_downturn_threshold = btc_downturn_threshold
    bot.ge_base_activation = Decimal("0.08")  # 8%
    bot.ge_base_trail = Decimal("0.04")  # 4%
    bot.currency = "USD"
    bot.exchange_service = Mock()
    return bot


def _make_positions(price=100.0, timestamp_ms=None):
    """Create a list with one position."""
    if timestamp_ms is None:
        timestamp_ms = int((time.time() - 15 * 86400) * 1000)  # 15 days ago
    return [{
        "id": "test-lot-1",
        "price": price,
        "amount": 1.0,
        "filled": 1.0,
        "fee": {"cost": 0.5},
        "cost": price,
        "timestamp": timestamp_ms
    }]


def _make_avg_position(price=100.0):
    return {
        "price": price,
        "amount": 1.0,
        "filled": 1.0,
        "fee": {"cost": 0.5},
        "cost": price
    }


class TestGraduatedExitDownturnSuppression(unittest.TestCase):

    def test_suppressed_when_btc_down_beyond_threshold(self):
        """BTC down 20%, coin down 50%, days=15 → NOOP (stop-loss suppressed)."""
        bot = _make_bot_stub(btc_downturn_threshold=Decimal("0.15"))
        ticker = "ALT"
        bot.demoted_coins = {ticker: time.time() - 15 * 86400}  # 15 days ago

        avg_position = _make_avg_position(price=100.0)
        ticker_info = {"bid": 50.0}  # coin down 50%
        all_positions = _make_positions(price=100.0)

        # Mock _get_btc_change_since_positions: BTC down 20%
        bot._get_btc_change_since_positions = Mock(
            return_value=(Decimal("-0.20"), Decimal("50000"), Decimal("40000"))
        )

        result = CryptoBot._check_graduated_exit(
            bot, "ALT/USD", avg_position, ticker_info, all_positions
        )

        self.assertEqual(result, TradeAction.NOOP)

    def test_not_suppressed_when_btc_down_below_threshold(self):
        """BTC down 5%, coin down 50%, days=15 → SELL (stop-loss fires normally)."""
        bot = _make_bot_stub(btc_downturn_threshold=Decimal("0.15"))
        ticker = "ALT"
        bot.demoted_coins = {ticker: time.time() - 15 * 86400}

        avg_position = _make_avg_position(price=100.0)
        ticker_info = {"bid": 50.0}  # coin down 50%
        all_positions = _make_positions(price=100.0)

        # Mock _get_btc_change_since_positions: BTC down only 5%
        bot._get_btc_change_since_positions = Mock(
            return_value=(Decimal("-0.05"), Decimal("50000"), Decimal("47500"))
        )

        result = CryptoBot._check_graduated_exit(
            bot, "ALT/USD", avg_position, ticker_info, all_positions
        )

        self.assertEqual(result, TradeAction.SELL)

    def test_take_profit_still_works_during_downturn(self):
        """BTC down 20% but coin is profitable → SELL (tightened take-profit fires
        before the downturn guard is reached)."""
        bot = _make_bot_stub(btc_downturn_threshold=Decimal("0.15"))
        ticker = "ALT"
        bot.demoted_coins = {ticker: time.time() - 15 * 86400}

        avg_position = _make_avg_position(price=100.0)
        # Coin is profitable — bid > position price enough to trigger tightened take-profit
        # After 15 days: tightening_factor ≈ max(0.1, 0.5 - 0.4*15/28) ≈ 0.286
        # effective_activation = 0.08 * 0.286 ≈ 0.0229 (2.29%)
        # So bid of 105 → profit ~4.5% which exceeds activation
        ticker_info = {"bid": 105.0}
        all_positions = _make_positions(price=100.0)

        # BTC is down 20% — but this shouldn't matter because take-profit fires first
        bot._get_btc_change_since_positions = Mock(
            return_value=(Decimal("-0.20"), Decimal("50000"), Decimal("40000"))
        )

        result = CryptoBot._check_graduated_exit(
            bot, "ALT/USD", avg_position, ticker_info, all_positions
        )

        self.assertEqual(result, TradeAction.SELL)

    def test_suppressed_with_default_threshold(self):
        """No config override, uses 15% default — BTC down 18% → NOOP."""
        # Use the actual default constant value
        default_threshold = Decimal(str(CONSTANTS.DEFAULT_DCS_GE_BTC_DOWNTURN_THRESHOLD)) / 100
        bot = _make_bot_stub(btc_downturn_threshold=default_threshold)
        ticker = "ALT"
        bot.demoted_coins = {ticker: time.time() - 15 * 86400}

        avg_position = _make_avg_position(price=100.0)
        ticker_info = {"bid": 50.0}
        all_positions = _make_positions(price=100.0)

        # BTC down 18% — exceeds 15% default threshold
        bot._get_btc_change_since_positions = Mock(
            return_value=(Decimal("-0.18"), Decimal("50000"), Decimal("41000"))
        )

        result = CryptoBot._check_graduated_exit(
            bot, "ALT/USD", avg_position, ticker_info, all_positions
        )

        self.assertEqual(result, TradeAction.NOOP)

    def test_not_suppressed_when_btc_is_up(self):
        """BTC is up 5% — no suppression, normal stop-loss can fire."""
        bot = _make_bot_stub(btc_downturn_threshold=Decimal("0.15"))
        ticker = "ALT"
        bot.demoted_coins = {ticker: time.time() - 15 * 86400}

        avg_position = _make_avg_position(price=100.0)
        ticker_info = {"bid": 50.0}  # coin down 50%
        all_positions = _make_positions(price=100.0)

        # BTC is up — suppression should not activate
        bot._get_btc_change_since_positions = Mock(
            return_value=(Decimal("0.05"), Decimal("50000"), Decimal("52500"))
        )

        result = CryptoBot._check_graduated_exit(
            bot, "ALT/USD", avg_position, ticker_info, all_positions
        )

        self.assertEqual(result, TradeAction.SELL)

    def test_holds_when_btc_fetch_fails(self):
        """BTC benchmark fetch fails → NOOP (never sell without market context)."""
        bot = _make_bot_stub(btc_downturn_threshold=Decimal("0.15"))
        ticker = "ALT"
        bot.demoted_coins = {ticker: time.time() - 18 * 86400}  # 18 days

        avg_position = _make_avg_position(price=100.0)
        ticker_info = {"bid": 50.0}  # coin down 50%
        all_positions = _make_positions(price=100.0)

        # BTC fetch fails — returns (None, None, None)
        bot._get_btc_change_since_positions = Mock(
            return_value=(None, None, None)
        )

        result = CryptoBot._check_graduated_exit(
            bot, "ALT/USD", avg_position, ticker_info, all_positions
        )

        self.assertEqual(result, TradeAction.NOOP)

    def test_holds_when_btc_fetch_fails_even_past_grace_period(self):
        """BTC fetch fails at 20 days demoted, coin at -50% → must still NOOP."""
        bot = _make_bot_stub()
        ticker = "ALT"
        bot.demoted_coins = {ticker: time.time() - 20 * 86400}

        avg_position = _make_avg_position(price=100.0)
        ticker_info = {"bid": 50.0}
        all_positions = _make_positions(price=100.0)

        bot._get_btc_change_since_positions = Mock(
            return_value=(None, None, None)
        )

        result = CryptoBot._check_graduated_exit(
            bot, "ALT/USD", avg_position, ticker_info, all_positions
        )

        self.assertEqual(result, TradeAction.NOOP)

    def test_holds_when_bid_is_none(self):
        """ticker_info has no bid → NOOP (never sell without a price)."""
        bot = _make_bot_stub()
        ticker = "ALT"
        bot.demoted_coins = {ticker: time.time() - 15 * 86400}

        avg_position = _make_avg_position(price=100.0)
        ticker_info = {"ask": 50.0}  # bid missing
        all_positions = _make_positions(price=100.0)

        result = CryptoBot._check_graduated_exit(
            bot, "ALT/USD", avg_position, ticker_info, all_positions
        )

        self.assertEqual(result, TradeAction.NOOP)

    def test_holds_when_bid_is_zero(self):
        """ticker_info bid is 0 → NOOP (never sell at zero price)."""
        bot = _make_bot_stub()
        ticker = "ALT"
        bot.demoted_coins = {ticker: time.time() - 15 * 86400}

        avg_position = _make_avg_position(price=100.0)
        ticker_info = {"bid": 0}
        all_positions = _make_positions(price=100.0)

        result = CryptoBot._check_graduated_exit(
            bot, "ALT/USD", avg_position, ticker_info, all_positions
        )

        self.assertEqual(result, TradeAction.NOOP)

    def test_noop_when_not_demoted(self):
        """Coin not in demoted_coins → NOOP (graduated exit doesn't apply)."""
        bot = _make_bot_stub()
        bot.dcs_enabled = True
        bot.demoted_coins = {}  # ALT not demoted

        avg_position = _make_avg_position(price=100.0)
        ticker_info = {"bid": 50.0}
        all_positions = _make_positions(price=100.0)

        result = CryptoBot._check_graduated_exit(
            bot, "ALT/USD", avg_position, ticker_info, all_positions
        )

        self.assertEqual(result, TradeAction.NOOP)

    def test_noop_when_dcs_disabled(self):
        """DCS disabled → NOOP (graduated exit only runs with DCS)."""
        bot = _make_bot_stub()
        bot.dcs_enabled = False

        avg_position = _make_avg_position(price=100.0)
        ticker_info = {"bid": 50.0}
        all_positions = _make_positions(price=100.0)

        result = CryptoBot._check_graduated_exit(
            bot, "ALT/USD", avg_position, ticker_info, all_positions
        )

        self.assertEqual(result, TradeAction.NOOP)

    def test_noop_when_avg_position_is_none(self):
        """No position → NOOP."""
        bot = _make_bot_stub()
        bot.dcs_enabled = True

        result = CryptoBot._check_graduated_exit(
            bot, "ALT/USD", None, {"bid": 50.0}, []
        )

        self.assertEqual(result, TradeAction.NOOP)

    def test_stop_loss_within_grace_period_does_not_sell(self):
        """Coin down vs BTC but only 10 days demoted (grace=14) → NOOP."""
        bot = _make_bot_stub()
        ticker = "ALT"
        bot.demoted_coins = {ticker: time.time() - 10 * 86400}  # 10 days

        avg_position = _make_avg_position(price=100.0)
        ticker_info = {"bid": 50.0}
        all_positions = _make_positions(price=100.0)

        # BTC flat, coin down 50% → relative loss -50%, but within grace period
        bot._get_btc_change_since_positions = Mock(
            return_value=(Decimal("0.00"), Decimal("50000"), Decimal("50000"))
        )

        result = CryptoBot._check_graduated_exit(
            bot, "ALT/USD", avg_position, ticker_info, all_positions
        )

        self.assertEqual(result, TradeAction.NOOP)

    def test_btc_exactly_at_threshold_suppresses(self):
        """BTC down exactly 15% (== threshold) → NOOP (suppressed)."""
        bot = _make_bot_stub(btc_downturn_threshold=Decimal("0.15"))
        ticker = "ALT"
        bot.demoted_coins = {ticker: time.time() - 15 * 86400}

        avg_position = _make_avg_position(price=100.0)
        ticker_info = {"bid": 50.0}
        all_positions = _make_positions(price=100.0)

        bot._get_btc_change_since_positions = Mock(
            return_value=(Decimal("-0.15"), Decimal("50000"), Decimal("42500"))
        )

        result = CryptoBot._check_graduated_exit(
            bot, "ALT/USD", avg_position, ticker_info, all_positions
        )

        self.assertEqual(result, TradeAction.NOOP)


class TestFindProfitableTradesBidValidation(unittest.TestCase):

    def test_returns_none_when_bid_missing(self):
        """find_profitable_trades with no bid in ticker_info → None."""
        from utils.trading import find_profitable_trades, TakeProfitEvaluationType
        avg_position = _make_avg_position(price=100.0)
        all_positions = [_make_avg_position(price=100.0)]
        ticker_info = {"ask": 105.0}  # no bid

        result = find_profitable_trades(
            "ALT/USD", avg_position, all_positions, ticker_info,
            Decimal("0.05"), TakeProfitEvaluationType.AVERAGE
        )

        self.assertIsNone(result)

    def test_returns_none_when_bid_is_zero(self):
        """find_profitable_trades with bid=0 → None."""
        from utils.trading import find_profitable_trades, TakeProfitEvaluationType
        avg_position = _make_avg_position(price=100.0)
        all_positions = [_make_avg_position(price=100.0)]
        ticker_info = {"bid": 0}

        result = find_profitable_trades(
            "ALT/USD", avg_position, all_positions, ticker_info,
            Decimal("0.05"), TakeProfitEvaluationType.AVERAGE
        )

        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
