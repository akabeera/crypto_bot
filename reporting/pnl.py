"""
Exchange-Based P&L Report

Fetches all historical orders from Coinbase, replays FIFO buy/sell matching,
and calculates realized + unrealized P&L per ticker.

Usage:
    python reporting/pnl.py
    python reporting/pnl.py --since 2025-01-01
    python reporting/pnl.py --since 2025-01-01 --tickers "SOL/USD,BTC/USD"
"""

import argparse
import copy
import csv
import os
import sys
from collections import deque
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import utils.constants as CONSTANTS
from utils.exchange_service import ExchangeService
from utils.mongodb_service import MongoDBService
from utils.logger import logger
from dotenv import load_dotenv

load_dotenv()

ZERO = Decimal("0")
QUANTIZE_2 = Decimal("0.01")


def filter_closed_orders(orders, since_ms=None):
    """Filter to only closed orders, optionally after a since timestamp."""
    filtered = []
    for o in orders:
        if o.get("status") != "closed":
            continue
        if since_ms and o.get("timestamp", 0) < since_ms:
            continue
        filtered.append(o)
    return filtered


def fifo_match(orders):
    """
    Replay orders chronologically with FIFO matching.

    Returns:
        matched_pairs: list of (buy_portion, sell_portion, realized_pnl, buy_fee, sell_fee)
        remaining_buys: list of unmatched buy orders (open positions)
        total_fees: total fees across all matched orders
    """
    sorted_orders = sorted(orders, key=lambda o: o.get("timestamp", 0))

    buy_queue = deque()
    matched_pairs = []
    total_fees = ZERO

    for order in sorted_orders:
        side = order.get("side", "").lower()
        filled = Decimal(str(order.get("filled", 0)))

        if filled <= ZERO:
            continue

        fee_cost = Decimal(str(order.get("fee", {}).get("cost", 0) or 0))
        total_fees += fee_cost

        if side == "buy":
            buy_entry = {
                "id": order.get("id"),
                "timestamp": order.get("timestamp"),
                "datetime": order.get("datetime"),
                "price": Decimal(str(order.get("average") or order.get("price", 0))),
                "remaining": filled,
                "original_filled": filled,
                "fee_cost": fee_cost,
                "cost": Decimal(str(order.get("cost", 0))),
            }
            buy_queue.append(buy_entry)

        elif side == "sell":
            sell_price = Decimal(str(order.get("average") or order.get("price", 0)))
            sell_remaining = filled
            sell_fee = fee_cost

            while sell_remaining > ZERO and buy_queue:
                buy = buy_queue[0]

                if buy["remaining"] <= sell_remaining:
                    # Consume entire buy lot
                    matched_shares = buy["remaining"]
                    buy_fee_portion = buy["fee_cost"] * (matched_shares / buy["original_filled"])
                    sell_fee_portion = sell_fee * (matched_shares / filled)

                    realized = (sell_price * matched_shares) - (buy["price"] * matched_shares) - buy_fee_portion - sell_fee_portion

                    matched_pairs.append({
                        "buy_id": buy["id"],
                        "sell_id": order.get("id"),
                        "shares": matched_shares,
                        "buy_price": buy["price"],
                        "sell_price": sell_price,
                        "realized_pnl": realized,
                        "buy_fee": buy_fee_portion,
                        "sell_fee": sell_fee_portion,
                    })

                    sell_remaining -= matched_shares
                    buy_queue.popleft()
                else:
                    # Partial consume of buy lot
                    matched_shares = sell_remaining
                    buy_fee_portion = buy["fee_cost"] * (matched_shares / buy["original_filled"])
                    sell_fee_portion = sell_fee * (matched_shares / filled)

                    realized = (sell_price * matched_shares) - (buy["price"] * matched_shares) - buy_fee_portion - sell_fee_portion

                    matched_pairs.append({
                        "buy_id": buy["id"],
                        "sell_id": order.get("id"),
                        "shares": matched_shares,
                        "buy_price": buy["price"],
                        "sell_price": sell_price,
                        "realized_pnl": realized,
                        "buy_fee": buy_fee_portion,
                        "sell_fee": sell_fee_portion,
                    })

                    buy["remaining"] -= matched_shares
                    sell_remaining = ZERO

    remaining_buys = list(buy_queue)
    return matched_pairs, remaining_buys, total_fees


def calculate_unrealized(remaining_buys, current_bid):
    """Calculate unrealized P&L for remaining open positions."""
    if not remaining_buys or current_bid is None:
        return ZERO, ZERO

    bid = Decimal(str(current_bid))
    total_unrealized = ZERO
    total_open_cost = ZERO

    for buy in remaining_buys:
        shares = buy["remaining"]
        buy_price = buy["price"]
        fee_portion = buy["fee_cost"] * (shares / buy["original_filled"])

        # Estimate sell fee using same rate as buy fee
        buy_cost = buy_price * shares
        if buy_cost > ZERO:
            fee_rate = fee_portion / buy_cost
        else:
            fee_rate = ZERO
        estimated_sell_fee = bid * shares * fee_rate

        unrealized = (bid * shares) - (buy_price * shares) - fee_portion - estimated_sell_fee
        total_unrealized += unrealized
        total_open_cost += buy_cost

    return total_unrealized, total_open_cost


def discover_tickers(mongodb_service, trades_collection, sell_orders_collection):
    """Discover all tickers from MongoDB trades and sell_orders collections."""
    trade_symbols = mongodb_service.distinct(trades_collection, "symbol")
    sell_symbols = mongodb_service.distinct(sell_orders_collection, "sell_order.symbol")
    all_symbols = set(trade_symbols or []) | set(sell_symbols or [])
    return sorted(all_symbols)


def generate_report(exchange_service, mongodb_service, since_date=None, ticker_filter=None,
                    trades_collection="trades", sell_orders_collection="sell_orders"):
    """Generate the full P&L report."""
    since_ms = None
    if since_date:
        since_ms = int(datetime.strptime(since_date, "%Y-%m-%d").timestamp() * 1000)

    # Discover tickers
    if ticker_filter:
        tickers = [t.strip() for t in ticker_filter.split(",")]
    else:
        tickers = discover_tickers(mongodb_service, trades_collection, sell_orders_collection)

    if not tickers:
        print("No tickers found.")
        return []

    results = []

    for ticker in tickers:
        logger.info(f"Processing {ticker}...")

        # Fetch all orders from exchange
        orders = exchange_service.fetch_all_orders(ticker, since_ms=since_ms)
        if not orders:
            logger.info(f"{ticker}: no orders found")
            continue

        # Filter to closed orders only
        closed_orders = filter_closed_orders(orders, since_ms=since_ms)
        if not closed_orders:
            logger.info(f"{ticker}: no closed orders found")
            continue

        # FIFO matching
        matched_pairs, remaining_buys, total_fees = fifo_match(closed_orders)

        # Realized P&L
        realized_pnl = sum((m["realized_pnl"] for m in matched_pairs), ZERO)
        closed_count = len(matched_pairs)

        # Unrealized P&L
        open_count = len(remaining_buys)
        unrealized_pnl = ZERO
        if remaining_buys:
            ticker_info = exchange_service.execute_op(ticker, CONSTANTS.OP_FETCH_TICKER)
            if ticker_info and ticker_info.get("bid"):
                unrealized_pnl, _ = calculate_unrealized(remaining_buys, ticker_info["bid"])

        total_pnl = realized_pnl + unrealized_pnl

        results.append({
            "ticker": ticker,
            "realized_pnl": realized_pnl.quantize(QUANTIZE_2, rounding=ROUND_HALF_UP),
            "unrealized_pnl": unrealized_pnl.quantize(QUANTIZE_2, rounding=ROUND_HALF_UP),
            "total_pnl": total_pnl.quantize(QUANTIZE_2, rounding=ROUND_HALF_UP),
            "closed_trades": closed_count,
            "open_positions": open_count,
            "fees": total_fees.quantize(QUANTIZE_2, rounding=ROUND_HALF_UP),
        })

    return results


def print_report(results, since_date=None):
    """Print the report as a formatted console table."""
    since_label = f"since {since_date}" if since_date else "all time"
    header = f" P&L Report ({since_label}) "
    print(f"\n{'=' * 20}{header}{'=' * 20}\n")

    fmt = "{:<16} {:>14} {:>16} {:>12} {:>8} {:>6} {:>8}"
    print(fmt.format("Ticker", "Realized P&L", "Unrealized P&L", "Total P&L", "Closed", "Open", "Fees"))
    print("-" * 84)

    total_realized = ZERO
    total_unrealized = ZERO
    total_pnl = ZERO
    total_closed = 0
    total_open = 0
    total_fees = ZERO

    for r in results:
        print(fmt.format(
            r["ticker"],
            f"${r['realized_pnl']}",
            f"${r['unrealized_pnl']}",
            f"${r['total_pnl']}",
            str(r["closed_trades"]),
            str(r["open_positions"]),
            f"${r['fees']}",
        ))
        total_realized += r["realized_pnl"]
        total_unrealized += r["unrealized_pnl"]
        total_pnl += r["total_pnl"]
        total_closed += r["closed_trades"]
        total_open += r["open_positions"]
        total_fees += r["fees"]

    print("-" * 84)
    print(fmt.format(
        "TOTAL",
        f"${total_realized.quantize(QUANTIZE_2)}",
        f"${total_unrealized.quantize(QUANTIZE_2)}",
        f"${total_pnl.quantize(QUANTIZE_2)}",
        str(total_closed),
        str(total_open),
        f"${total_fees.quantize(QUANTIZE_2)}",
    ))
    print()


def write_csv(results, since_date=None):
    """Write results to a CSV file in the reports/ directory."""
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
    os.makedirs(reports_dir, exist_ok=True)

    if since_date:
        filename = f"pnl_since_{since_date}.csv"
    else:
        filename = f"pnl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    filepath = os.path.join(reports_dir, filename)

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "ticker", "realized_pnl", "unrealized_pnl", "total_pnl",
            "closed_trades", "open_positions", "fees"
        ])
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    print(f"CSV written to: {filepath}")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="Exchange-Based P&L Report")
    parser.add_argument("--since", type=str, default=None,
                        help="Start date (YYYY-MM-DD) for the report")
    parser.add_argument("--tickers", type=str, default=None,
                        help="Comma-separated list of ticker pairs (e.g., 'SOL/USD,BTC/USD')")
    args = parser.parse_args()

    import json
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config_enhanced.json")
    with open(config_path) as f:
        config = json.load(f)

    exchange_config = config.get(CONSTANTS.CONFIG_EXCHANGE, {})
    exchange_service = ExchangeService(exchange_config)

    db_config = config.get(CONSTANTS.CONFIG_DB, {})
    db_url = os.getenv("DB_CONNECTION_STRING")
    db_name = db_config.get(CONSTANTS.CONFIG_DB_NAME, CONSTANTS.DEFAULT_MONGO_DB_NAME)
    trades_collection = db_config.get(CONSTANTS.CONFIG_DB_CURRENT_POSITIONS_COLLECTION, CONSTANTS.DEFAULT_MONGO_TRADES_COLLECTION)
    sell_orders_collection = db_config.get(CONSTANTS.CONFIG_DB_CLOSED_POSITIONS_COLLECTION, CONSTANTS.DEFAULT_MONGO_SELL_ORDERS_COLLECTION)

    mongodb_service = MongoDBService(db_url, db_name)

    results = generate_report(
        exchange_service=exchange_service,
        mongodb_service=mongodb_service,
        since_date=args.since,
        ticker_filter=args.tickers,
        trades_collection=trades_collection,
        sell_orders_collection=sell_orders_collection,
    )

    if results:
        print_report(results, args.since)
        write_csv(results, args.since)
    else:
        print("No data to report.")


if __name__ == "__main__":
    main()
