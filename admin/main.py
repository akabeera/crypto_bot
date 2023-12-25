import os
import argparse
import pprint
from decimal import *

from dotenv import load_dotenv
from utils.exchange_service import ExchangeService
from utils.mongodb_service import MongoDBService
from utils.reconciliation import ReconciliationActions, reconcile_with_exchange, apply_reconciliation_to_db
from utils.constants import DEFAULT_MONGO_DB_NAME, DEFAULT_MONGO_SELL_ORDERS_COLLECTION, DEFAULT_MONGO_TRADES_COLLECTION

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


def add_orders(orders: str, ticker_pair: str):
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

def get_orders(orders: str, ticker_pair: str):
    order_list = orders.split(",")
    for order_id in order_list:

        order = exchange_service.execute_op(ticker_pair, op="fetchOrder", order_id=order_id)
        if not order:
            print(f"Error fetching order id: {order_id}")
            continue

        pprint.pprint(order)

def reconcile_db_with_exchange(ticker_pairs: list, dry_run: bool):
    for ticker_pair in ticker_pairs:
        print(f"{ticker_pair} Starting recon process")
        exchange_orders = exchange_service.execute_op(ticker_pair, "fetchOrders")
        
        if exchange_orders is None:
            print("ERROR: Failed to fetch orders from exchange for {ticker_pair}, aborting")
            continue

        print(f"{ticker_pair} has {len(exchange_orders)} orders, replaying all orders")
        actions = reconcile_with_exchange(ticker_pair, exchange_orders)

        reconciliation_actions = ReconciliationActions()
        reconciliation_actions.sell_order_collection = SELL_ORDERS_COLLECTION
        reconciliation_actions.buy_order_collection = TRADES_COLLECTION
        reconciliation_actions.sell_order_deletions.extend(actions.sell_order_deletions) 
        reconciliation_actions.sell_order_insertions.extend(actions.sell_order_insertions)
        reconciliation_actions.buy_order_deletions.extend(actions.buy_order_deletions)
        reconciliation_actions.buy_order_updates.extend(actions.buy_order_updates)
        reconciliation_actions.buy_order_insertions.extend(actions.buy_order_insertions)

        if dry_run:
            continue
        
        print(f"{ticker_pair} applying reconciliation actions to DB")
        apply_reconciliation_to_db(reconciliation_actions, mongodb_service)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--op", help="the operation you want to perform")
    parser.add_argument("--orders", help="comma separated list of order numbers")
    parser.add_argument("--ticker_pairs", help="ticker pairs list")
    parser.add_argument("--dry_run", help="dry run", default="True", type=str)

    args = parser.parse_args()

    if args.op:
        if args.op == "add_order":
            add_orders(args.orders, args.ticker_pair)
        if args.op == "get_orders":
            get_orders(args.orders, args.ticker_pair)
        if args.op == "recon":
            dry_run = args.dry_run == "True"
            ticker_pairs = args.ticker_pairs.split(",")
            reconcile_db_with_exchange(ticker_pairs, dry_run)
    else:
        print("no op argument")


