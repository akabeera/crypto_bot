import unittest
from decimal import Decimal, ROUND_HALF_UP

from reporting.pnl import fifo_match, filter_closed_orders, calculate_unrealized

QUANTIZE_2 = Decimal("0.01")


def make_order(id, side, filled, price, fee_cost, timestamp, status="closed"):
    """Helper to create a minimal order dict matching ccxt/Coinbase structure."""
    return {
        "id": id,
        "side": side,
        "filled": filled,
        "amount": filled,
        "price": price,
        "average": price,
        "cost": filled * price,
        "fee": {"cost": fee_cost, "currency": "USD"},
        "fees": [{"cost": fee_cost, "currency": "USD"}],
        "timestamp": timestamp,
        "datetime": f"2025-01-01T00:00:00Z",
        "status": status,
        "symbol": "TEST/USD",
    }


class TestFifoMatch(unittest.TestCase):

    def test_simple_round_trip(self):
        """1 buy + 1 sell -> correct realized P&L with fees."""
        orders = [
            make_order("b1", "buy", 10.0, 100.0, 1.0, 1000),
            make_order("s1", "sell", 10.0, 110.0, 1.1, 2000),
        ]
        matched, remaining, total_fees = fifo_match(orders)

        self.assertEqual(len(matched), 1)
        self.assertEqual(len(remaining), 0)

        m = matched[0]
        # realized = (110 * 10) - (100 * 10) - 1.0 - 1.1 = 1100 - 1000 - 2.1 = 97.9
        expected_pnl = Decimal("97.9")
        self.assertEqual(m["realized_pnl"].quantize(QUANTIZE_2), expected_pnl)
        self.assertEqual(m["buy_id"], "b1")
        self.assertEqual(m["sell_id"], "s1")

        expected_fees = Decimal("2.10")
        self.assertEqual(total_fees.quantize(QUANTIZE_2), expected_fees)

    def test_multiple_buys_one_sell_fifo_order(self):
        """Multiple buys, one sell -> FIFO order respected (oldest buy matched first)."""
        orders = [
            make_order("b1", "buy", 5.0, 100.0, 0.5, 1000),
            make_order("b2", "buy", 5.0, 120.0, 0.6, 2000),
            make_order("s1", "sell", 8.0, 130.0, 1.04, 3000),
        ]
        matched, remaining, total_fees = fifo_match(orders)

        # Should match b1 fully (5 shares) then b2 partially (3 shares)
        self.assertEqual(len(matched), 2)
        self.assertEqual(len(remaining), 1)

        # First match: b1 fully consumed (5 shares)
        self.assertEqual(matched[0]["buy_id"], "b1")
        self.assertEqual(matched[0]["shares"], Decimal("5"))

        # Second match: b2 partially consumed (3 shares)
        self.assertEqual(matched[1]["buy_id"], "b2")
        self.assertEqual(matched[1]["shares"], Decimal("3"))

        # Remaining: b2 with 2 shares left
        self.assertEqual(remaining[0]["remaining"], Decimal("2"))

    def test_partial_sell(self):
        """Sell less than one buy lot -> split correctly, remainder stays open."""
        orders = [
            make_order("b1", "buy", 10.0, 100.0, 1.0, 1000),
            make_order("s1", "sell", 3.0, 110.0, 0.33, 2000),
        ]
        matched, remaining, total_fees = fifo_match(orders)

        self.assertEqual(len(matched), 1)
        self.assertEqual(len(remaining), 1)

        m = matched[0]
        self.assertEqual(m["shares"], Decimal("3"))

        # Remaining buy should have 7 shares left
        self.assertEqual(remaining[0]["remaining"], Decimal("7"))
        self.assertEqual(remaining[0]["id"], "b1")

        # Realized: (110*3) - (100*3) - (1.0 * 3/10) - (0.33 * 3/3) = 330 - 300 - 0.3 - 0.33 = 29.37
        expected = Decimal("29.37")
        self.assertEqual(m["realized_pnl"].quantize(QUANTIZE_2), expected)

    def test_all_open_positions(self):
        """Only buys, no sells -> 0 realized, all unrealized."""
        orders = [
            make_order("b1", "buy", 5.0, 100.0, 0.5, 1000),
            make_order("b2", "buy", 3.0, 110.0, 0.33, 2000),
        ]
        matched, remaining, total_fees = fifo_match(orders)

        self.assertEqual(len(matched), 0)
        self.assertEqual(len(remaining), 2)
        self.assertEqual(remaining[0]["id"], "b1")
        self.assertEqual(remaining[1]["id"], "b2")

    def test_cancelled_orders_excluded(self):
        """Non-closed orders are filtered out before matching."""
        orders = [
            make_order("b1", "buy", 10.0, 100.0, 1.0, 1000, status="closed"),
            make_order("b2", "buy", 5.0, 95.0, 0.5, 1500, status="canceled"),
            make_order("s1", "sell", 10.0, 110.0, 1.1, 2000, status="closed"),
        ]
        # Filter first (as the main flow does)
        closed = filter_closed_orders(orders)
        matched, remaining, total_fees = fifo_match(closed)

        # b2 was canceled, so only b1 matched with s1
        self.assertEqual(len(matched), 1)
        self.assertEqual(len(remaining), 0)
        self.assertEqual(matched[0]["buy_id"], "b1")

    def test_since_filter(self):
        """Orders before cutoff date are excluded."""
        since_ms = 1500

        orders = [
            make_order("b1", "buy", 10.0, 100.0, 1.0, 1000, status="closed"),
            make_order("b2", "buy", 5.0, 105.0, 0.5, 2000, status="closed"),
            make_order("s1", "sell", 5.0, 115.0, 0.575, 3000, status="closed"),
        ]
        closed = filter_closed_orders(orders, since_ms=since_ms)

        # b1 (ts=1000) should be excluded
        self.assertEqual(len(closed), 2)
        ids = {o["id"] for o in closed}
        self.assertNotIn("b1", ids)
        self.assertIn("b2", ids)
        self.assertIn("s1", ids)

        matched, remaining, total_fees = fifo_match(closed)
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["buy_id"], "b2")
        self.assertEqual(len(remaining), 0)


class TestCalculateUnrealized(unittest.TestCase):

    def test_unrealized_pnl(self):
        """Remaining buys valued at current bid produce correct unrealized P&L."""
        remaining_buys = [
            {
                "id": "b1",
                "price": Decimal("100"),
                "remaining": Decimal("5"),
                "original_filled": Decimal("10"),
                "fee_cost": Decimal("1.0"),
                "cost": Decimal("1000"),
            }
        ]
        # bid at 120: value = 600, cost = 500, fee_portion = 1.0 * 5/10 = 0.5
        # fee_rate = 0.5/500 = 0.001, est_sell_fee = 600 * 0.001 = 0.6
        # unrealized = 600 - 500 - 0.5 - 0.6 = 98.9
        unrealized, _ = calculate_unrealized(remaining_buys, 120)
        self.assertEqual(unrealized.quantize(QUANTIZE_2), Decimal("98.90"))

    def test_no_remaining_buys(self):
        """No remaining buys -> zero unrealized."""
        unrealized, _ = calculate_unrealized([], 120)
        self.assertEqual(unrealized, Decimal("0"))

    def test_no_bid(self):
        """No bid price -> zero unrealized."""
        remaining_buys = [
            {
                "id": "b1",
                "price": Decimal("100"),
                "remaining": Decimal("5"),
                "original_filled": Decimal("10"),
                "fee_cost": Decimal("1.0"),
                "cost": Decimal("1000"),
            }
        ]
        unrealized, _ = calculate_unrealized(remaining_buys, None)
        self.assertEqual(unrealized, Decimal("0"))


if __name__ == "__main__":
    unittest.main()
