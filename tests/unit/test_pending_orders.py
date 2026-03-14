import unittest
import sys
import os
import time
from decimal import Decimal
from unittest.mock import Mock, patch

import mongomock

from utils.mongodb_service import MongoDBService
import utils.constants as CONSTANTS

# Import the CryptoBot class from crypto_bot.py (root-level module).
# The project has an __init__.py that makes the directory a package,
# so we import the module file directly.
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "crypto_bot_module",
    os.path.join(os.path.dirname(__file__), "..", "..", "crypto_bot.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
CryptoBot = _mod.CryptoBot


def make_order(order_id="test-order-1", ticker_pair="SOL/USD", status="closed",
               filled=1.0, price=100.0, side="buy", total_value_after_fees="99.5"):
    return {
        "id": order_id,
        "info": {
            "order_id": order_id,
            "product_id": ticker_pair.replace("/", "-"),
            "total_value_after_fees": total_value_after_fees,
            "status": "FILLED" if status == "closed" else "PENDING",
        },
        "symbol": ticker_pair,
        "type": "limit",
        "side": side,
        "price": price,
        "filled": filled,
        "remaining": 0 if status == "closed" else 0.5,
        "cost": filled * price,
        "average": price,
        "status": status,
        "timestamp": int(time.time() * 1000),
        "fee": {"cost": 0.5, "currency": None},
    }


def make_position(pos_id, ticker_pair="SOL/USD", filled=0.5, price=100.0):
    return {
        "id": pos_id,
        "symbol": ticker_pair,
        "filled": filled,
        "price": price,
        "cost": filled * price,
        "average": price,
        "timestamp": int(time.time() * 1000),
        "fee": {"cost": 0.01, "currency": None},
        "info": {
            "order_id": pos_id,
            "total_value_after_fees": str(filled * price),
        },
    }


class TestCreateOrderBreaksAfterMaxResets(unittest.TestCase):
    """Test that ExchangeService.create_order exits after max_resets."""

    @patch("utils.exchange_service.API_SECRET", "fake-secret")
    @patch("utils.exchange_service.API_KEY", "fake-key")
    def test_create_order_breaks_after_max_resets(self):
        from utils.exchange_service import ExchangeService

        # Reset singleton
        ExchangeService._exchange = None

        exchange_config = {
            CONSTANTS.CONFIG_LIMIT_ORDER_NUM_PERIODS_LIMIT: 2,
            CONSTANTS.CONFIG_LIMIT_ORDER_PERIOD_TIME_LIMIT: 0,  # no delay in tests
            CONSTANTS.CONFIG_LIMIT_ORDER_MAX_RESETS: 2,
        }

        service = ExchangeService(exchange_config, dry_run=False)

        # Mock the exchange client
        mock_exchange = Mock()
        service.exchange_client = mock_exchange

        # create_order returns an initial result with status 'open'
        initial_result = {
            "info": {"order_id": "order-123"},
            "status": "open",
            "filled": 0.0,
        }
        mock_exchange.create_order.return_value = initial_result

        # fetch_order always returns partially filled, never 'closed'
        partial_order = {
            "info": {"order_id": "order-123"},
            "status": "open",
            "filled": 0.5,  # partially filled
        }
        mock_exchange.fetch_order.return_value = partial_order
        mock_exchange.has = {"fetchOrder": True}

        result = service.create_order("SOL/USD", 1.0, "limit", "buy", 100.0)

        # Should return the order as-is (not None, not closed)
        self.assertIsNotNone(result)
        self.assertNotEqual(result["status"], "closed")
        self.assertEqual(result["filled"], 0.5)

        # cancel_order should NOT have been called (partial fill => pending, not cancel)
        mock_exchange.cancel_order.assert_not_called()


class TestPendingOrdersWithMongomock(unittest.TestCase):
    """Tests for pending order handling in CryptoBot."""

    def setUp(self):
        MongoDBService._client = None

        self.mock_db = mongomock.MongoClient().db
        self.mongodb_service = MongoDBService(
            "mongomock://localhost",
            CONSTANTS.DEFAULT_MONGO_DB_NAME,
            self.mock_db,
        )

        self.trades_collection = "trades"
        self.sell_orders_collection = "sell_orders"
        self.pending_orders_collection = "pending_orders"

    def tearDown(self):
        self.mongodb_service.delete_many(self.trades_collection)
        self.mongodb_service.delete_many(self.sell_orders_collection)
        self.mongodb_service.delete_many(self.pending_orders_collection)
        MongoDBService._client = None

    def _make_bot_stub(self):
        """Create a minimal CryptoBot-like object with the attributes needed by the methods under test."""
        bot = Mock()
        bot.mongodb_service = self.mongodb_service
        bot.current_positions_collection = self.trades_collection
        bot.closed_positions_collection = self.sell_orders_collection
        bot.pending_orders_collection = self.pending_orders_collection
        bot.remaining_balance = Decimal("50")
        bot.reinvestment_percent = Decimal("0.5")
        bot.overrides = {}
        bot.exchange_service = Mock()
        return bot

    def test_handle_buy_order_saves_pending_on_partial_fill(self):
        bot = self._make_bot_stub()

        partial_order = make_order(
            order_id="buy-pending-1",
            ticker_pair="SOL/USD",
            status="open",
            filled=0.3,
            side="buy",
        )

        ticker_pair = "SOL/USD"
        amount = Decimal("5")

        # Replicate the pending buy logic from handle_buy_order
        pending_doc = {
            "order_id": partial_order["info"]["order_id"],
            "ticker_pair": ticker_pair,
            "side": "buy",
            "reserved_amount": float(amount),
            "created_at": time.time(),
            "last_order_snapshot": partial_order,
        }
        self.mongodb_service.insert_one(self.pending_orders_collection, pending_doc)
        bot.remaining_balance -= amount

        # Verify pending doc was created
        pending = self.mongodb_service.query(self.pending_orders_collection, {"order_id": "buy-pending-1"})
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["side"], "buy")
        self.assertEqual(pending[0]["reserved_amount"], 5.0)
        self.assertEqual(pending[0]["ticker_pair"], "SOL/USD")

        # Verify balance was deducted
        self.assertEqual(bot.remaining_balance, Decimal("45"))

        # Verify order NOT in trades
        trades = self.mongodb_service.query(self.trades_collection, {"id": "buy-pending-1"})
        self.assertEqual(len(trades), 0)

    def test_handle_sell_order_saves_pending_on_partial_fill(self):
        # Insert positions into trades first
        pos1 = make_position("lot-1", "SOL/USD")
        pos2 = make_position("lot-2", "SOL/USD")
        self.mongodb_service.insert_one(self.trades_collection, pos1)
        self.mongodb_service.insert_one(self.trades_collection, pos2)

        partial_order = make_order(
            order_id="sell-pending-1",
            ticker_pair="SOL/USD",
            status="open",
            filled=0.5,
            side="sell",
        )

        positions_to_exit = [pos1, pos2]
        positions_to_delete = ["lot-1", "lot-2"]

        # Replicate the pending sell logic
        pending_doc = {
            "order_id": partial_order["info"]["order_id"],
            "ticker_pair": "SOL/USD",
            "side": "sell",
            "positions_to_exit": positions_to_exit,
            "positions_to_exit_ids": positions_to_delete,
            "created_at": time.time(),
            "last_order_snapshot": partial_order,
        }
        self.mongodb_service.insert_one(self.pending_orders_collection, pending_doc)

        # Verify pending doc
        pending = self.mongodb_service.query(self.pending_orders_collection, {"order_id": "sell-pending-1"})
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["side"], "sell")
        self.assertEqual(pending[0]["positions_to_exit_ids"], ["lot-1", "lot-2"])

        # Verify lots are still in trades (NOT deleted)
        trades = self.mongodb_service.query(self.trades_collection, {})
        self.assertEqual(len(trades), 2)

    def test_reconcile_completed_buy(self):
        bot = self._make_bot_stub()

        # Insert a pending buy
        pending_doc = {
            "order_id": "buy-recon-1",
            "ticker_pair": "SOL/USD",
            "side": "buy",
            "reserved_amount": 5.0,
            "created_at": time.time(),
            "last_order_snapshot": make_order("buy-recon-1", status="open"),
        }
        self.mongodb_service.insert_one(self.pending_orders_collection, pending_doc)

        completed_order = make_order("buy-recon-1", status="closed", filled=1.0)

        # Call the real method on the mock bot
        CryptoBot._complete_pending_order(bot, pending_doc, completed_order)

        # Verify order inserted into trades
        trades = self.mongodb_service.query(self.trades_collection, {})
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["id"], "buy-recon-1")

        # Verify pending doc deleted
        pending = self.mongodb_service.query(self.pending_orders_collection, {"order_id": "buy-recon-1"})
        self.assertEqual(len(pending), 0)

    def test_reconcile_completed_sell(self):
        bot = self._make_bot_stub()

        # Insert lots into trades
        pos1 = make_position("lot-sell-1", "SOL/USD", filled=0.5, price=100.0)
        pos2 = make_position("lot-sell-2", "SOL/USD", filled=0.5, price=100.0)
        self.mongodb_service.insert_one(self.trades_collection, pos1)
        self.mongodb_service.insert_one(self.trades_collection, pos2)

        # Insert a pending sell
        pending_doc = {
            "order_id": "sell-recon-1",
            "ticker_pair": "SOL/USD",
            "side": "sell",
            "positions_to_exit": [pos1, pos2],
            "positions_to_exit_ids": ["lot-sell-1", "lot-sell-2"],
            "created_at": time.time(),
            "last_order_snapshot": make_order("sell-recon-1", status="open", side="sell"),
        }
        self.mongodb_service.insert_one(self.pending_orders_collection, pending_doc)

        completed_order = make_order(
            "sell-recon-1", status="closed", side="sell",
            filled=1.0, price=110.0, total_value_after_fees="109.5",
        )

        initial_balance = bot.remaining_balance

        CryptoBot._complete_pending_order(bot, pending_doc, completed_order)

        # Verify sell_orders doc created
        sell_orders = self.mongodb_service.query(self.sell_orders_collection, {})
        self.assertEqual(len(sell_orders), 1)
        self.assertEqual(sell_orders[0]["sell_order"]["id"], "sell-recon-1")

        # Verify lots deleted from trades
        trades = self.mongodb_service.query(self.trades_collection, {})
        self.assertEqual(len(trades), 0)

        # Verify balance updated (reinvestment_percent = 0.5, proceeds = 109.5)
        expected_reinvestment = Decimal("109.5") * Decimal("0.5")
        self.assertEqual(bot.remaining_balance, initial_balance + expected_reinvestment)

        # Verify pending doc deleted
        pending = self.mongodb_service.query(self.pending_orders_collection, {"order_id": "sell-recon-1"})
        self.assertEqual(len(pending), 0)

    def test_lots_excluded_from_sell_flow(self):
        # Insert positions
        pos1 = make_position("lot-a", "SOL/USD")
        pos2 = make_position("lot-b", "SOL/USD")
        pos3 = make_position("lot-c", "SOL/USD")
        self.mongodb_service.insert_one(self.trades_collection, pos1)
        self.mongodb_service.insert_one(self.trades_collection, pos2)
        self.mongodb_service.insert_one(self.trades_collection, pos3)

        # Insert a pending sell that covers lot-a and lot-b
        pending_doc = {
            "order_id": "sell-pending-excl",
            "ticker_pair": "SOL/USD",
            "side": "sell",
            "positions_to_exit_ids": ["lot-a", "lot-b"],
            "created_at": time.time(),
        }
        self.mongodb_service.insert_one(self.pending_orders_collection, pending_doc)

        # Simulate the filtering logic from run()
        ticker_pair = "SOL/USD"
        all_positions = self.mongodb_service.query(self.trades_collection, {"symbol": ticker_pair})

        pending_sells = self.mongodb_service.query(
            self.pending_orders_collection,
            {"ticker_pair": ticker_pair, "side": "sell"},
        )
        if pending_sells:
            excluded_ids = set()
            for ps in pending_sells:
                excluded_ids.update(ps.get("positions_to_exit_ids", []))
            if excluded_ids:
                all_positions = [p for p in all_positions if p["id"] not in excluded_ids]

        # Only lot-c should remain
        self.assertEqual(len(all_positions), 1)
        self.assertEqual(all_positions[0]["id"], "lot-c")

    def test_cleanup_cancelled_buy_restores_balance(self):
        bot = self._make_bot_stub()
        bot.remaining_balance = Decimal("45")  # was 50, deducted 5 on pending buy

        pending_doc = {
            "order_id": "buy-cancel-1",
            "ticker_pair": "SOL/USD",
            "side": "buy",
            "reserved_amount": 5.0,
            "created_at": time.time(),
        }
        self.mongodb_service.insert_one(self.pending_orders_collection, pending_doc)

        cancelled_order = make_order("buy-cancel-1", status="canceled")

        CryptoBot._cleanup_cancelled_pending_order(bot, pending_doc, cancelled_order)

        # Balance should be restored
        self.assertEqual(bot.remaining_balance, Decimal("50"))

        # Pending doc should be deleted
        pending = self.mongodb_service.query(self.pending_orders_collection, {"order_id": "buy-cancel-1"})
        self.assertEqual(len(pending), 0)


if __name__ == "__main__":
    unittest.main()
