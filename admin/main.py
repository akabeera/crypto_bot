import os
import argparse
import pprint
from decimal import *

from dotenv import load_dotenv
from utils.exchange_service import ExchangeService
from utils.mongodb_service import MongoDBService
from utils.reconciliation import ReconciliationActions, reconcile_with_exchange, apply_reconciliation_to_db
from utils.constants import DEFAULT_MONGO_DB_NAME, DEFAULT_MONGO_SELL_ORDERS_COLLECTION, DEFAULT_MONGO_TRADES_COLLECTION, DEFAULT_MONGO_SNAPSHOTS_COLLECTION, FIVE

load_dotenv()

MONGO_CONNECTION_STRING = os.getenv("MONGO_CONNECTION_STRING")
DB_NAME = DEFAULT_MONGO_DB_NAME
SELL_ORDERS_COLLECTION = DEFAULT_MONGO_SELL_ORDERS_COLLECTION
TRADES_COLLECTION = DEFAULT_MONGO_TRADES_COLLECTION

mongodb_service = MongoDBService(MONGO_CONNECTION_STRING, DB_NAME)

exchange_config = {
    'exchange_id': "coinbase",
    'market_order_type_buy': "market",
    'market_order_type_sell': "limit",
    'limit_order_time_limit': 10,
    'create_market_buy_order_requires_price': False
}
exchange_service = ExchangeService(exchange_config)


def add_buy_orders(orders: str, ticker_pair: str):
    order_list = orders.split(",")

    for order_id in order_list:
        order = exchange_service.execute_op(ticker_pair, op="fetchOrder", order_id=order_id)
        if not order:
            print(f"Error fetching order id: {order_id}")
            continue

        order_id_filter = {
                'id': order_id
            }    
        check_order = mongodb_service.query(TRADES_COLLECTION, order_id_filter)
        if len(check_order) > 0:
            print(f"{order_id} already exists in DB, skipping")
            continue

        print(f"Inserting order_id {order_id} into {TRADES_COLLECTION} table")
        mongodb_service.insert_one(TRADES_COLLECTION, order)

def add_sell_orders(orders: str, ticker_pair: str):
    order_list = orders.split(",")

    for order_id in order_list:
        order = exchange_service.execute_op(ticker_pair, op="fetchOrder", order_id=order_id)
        if not order:
            print(f"Error fetching order id: {order_id}")
            continue

        order_id_filter = {
                'id': order_id
            }    
        check_order = mongodb_service.query(SELL_ORDERS_COLLECTION, order_id_filter)
        if len(check_order) > 0:
            print(f"{order_id} already exists in DB, skipping")
            continue

        positions_filter = {
            "symbol": ticker_pair
        }

        positions = mongodb_service.query(TRADES_COLLECTION, positions_filter)
        if len(positions) == 0:
            print(f"no positions found for {ticker_pair} in DB, can't add sell order")
            continue

        sell_order = {
            "sell_order": order,
            "closed_positions": positions
        }

        print(f"Inserting order_id {order_id} into {SELL_ORDERS_COLLECTION} table")
        mongodb_service.insert_one(SELL_ORDERS_COLLECTION, sell_order)
        mongodb_service.delete_many(TRADES_COLLECTION, positions_filter)
        

def get_orders(orders: str, ticker_pair: str):
    order_list = orders.split(",")
    for order_id in order_list:

        order = exchange_service.execute_op(ticker_pair, op="fetchOrder", order_id=order_id)
        if not order:
            print(f"Error fetching order id: {order_id}")
            continue

        pprint.pprint(order)

def reconcile_db_with_exchange(ticker_pairs: list, dry_run: bool):
    
    print(f"Starting recon process")
    total_recon_value = Decimal(0)  
    tickers_applied_recon = []

    if not dry_run:
        print("creating a snapshot of DB")
        collections_to_backup = [
            DEFAULT_MONGO_SELL_ORDERS_COLLECTION,
            DEFAULT_MONGO_TRADES_COLLECTION
        ]
        snapshot = mongodb_service.snapshot(DEFAULT_MONGO_SNAPSHOTS_COLLECTION, collections_to_backup, "backup before IOTX reconciliation")
        if snapshot is None:
            print("An error occurred while backing up, aborting reconciliation")
            return

    for ticker_pair in ticker_pairs:
        print("\n\n")
        print(f"{ticker_pair}")
        exchange_orders = exchange_service.execute_op(ticker_pair, "fetchOrders")
        
        if exchange_orders is None:
            print("ERROR: Failed to fetch orders from exchange for {ticker_pair}, aborting")
            continue

        print(f"{ticker_pair} has {len(exchange_orders)} orders, replaying all orders")
        actions = reconcile_with_exchange(ticker_pair, exchange_orders)
        actions.sell_order_collection = SELL_ORDERS_COLLECTION
        actions.buy_order_collection = TRADES_COLLECTION

        if not actions.can_automatically_reconcile():
            print(f"actions tally don't match replay orders tally, skipping recon")
            continue

        ticker_info = exchange_service.execute_op(ticker_pair=ticker_pair, op="fetchTicker")
        if (not ticker_info or ticker_info['ask'] is None or ticker_info['bid'] is None):
            print(f"{ticker_pair}: unable to fetch ticker info or missing ask/bid prices, skipping")
            continue

        bid_price = Decimal(ticker_info['bid'])
        recon_value = bid_price * actions.recon_actions_shares_tally

        if recon_value < FIVE:
            print(f"{ticker_pair} recon value is only {recon_value}, not worth applying to DB, skipping")
            continue        
        
        print(f"{ticker_pair} recovering value of {recon_value} after recon")
        total_recon_value += recon_value
        tickers_applied_recon.append(ticker_pair)
        if dry_run:
            print(f"{ticker_pair} dry_run flag enabled, skipping apply to DB")
            continue
        
        print(f"{ticker_pair} applying reconciliation actions to DB")
        apply_reconciliation_to_db(actions, mongodb_service)

    print("\nrecon summary:")
    print(f"{ticker_pair} tickers applied recon: {','.join(tickers_applied_recon)}")
    print(f"{ticker_pair} total value of applied recon actions {total_recon_value}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--op", help="the operation you want to perform")
    parser.add_argument("--orders", help="comma separated list of order numbers")
    parser.add_argument("--ticker_pairs", help="ticker pairs list")
    parser.add_argument("--dry_run", help="dry run", default="True", type=str)

    args = parser.parse_args()

    if args.op:
        if args.op == "add_buy_order":
            add_buy_orders(args.orders, args.ticker_pairs)
        if args.op == "add_sell_order":
            add_sell_orders(args.orders, args.ticker_pairs)
        if args.op == "get_orders":
            get_orders(args.orders, args.ticker_pairs)
        if args.op == "recon":
            dry_run = args.dry_run == "True"
            ticker_pairs = args.ticker_pairs.split(",")
            reconcile_db_with_exchange(ticker_pairs, dry_run)
    else:
        print("no op argument")


