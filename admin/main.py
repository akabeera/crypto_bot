import os
import argparse
import pprint
from decimal import *


from dotenv import load_dotenv
from utils.exchange_service import ExchangeService
from utils.mongodb_service import MongoDBService
from utils.reconciliation import ReconciliationActions, handle_partial_order
from utils.constants import ZERO, ONE_HUNDRED, DEFAULT_MONGO_DB_NAME, DEFAULT_MONGO_SELL_ORDERS_COLLECTION, DEFAULT_MONGO_TRADES_COLLECTION


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


def reconcile(ticker_pair: str, dry_run: bool):
    filter = {
        'sell_order.symbol': ticker_pair
    }

    #db_sell_orders = mongodb_service.query(SELL_ORDERS_COLLECTION, filter)
    exchange_orders = exchange_service.execute_op(ticker_pair, "fetchOrders")
    buy_orders = []

    for idx, order in enumerate(exchange_orders):
        side = order['side']

        if side == "buy":
            buy_orders.append(order)
            continue 

        order_info = order["info"]
        completion_pct = Decimal(order_info["completion_percentage"])
        
        if completion_pct == ZERO:
            continue

        if completion_pct == ONE_HUNDRED:
            buy_orders.clear()
            continue

        reconcilation_actions = handle_partial_order(order, buy_orders)
        reconcilation_actions.sell_order_collection = SELL_ORDERS_COLLECTION
        reconcilation_actions.buy_order_collection = TRADES_COLLECTION

        if dry_run:
            pprint.pprint(reconcilation_actions, depth=10)
        else:
            mongodb_service.reconciliation(reconcilation_actions)
        buy_orders.clear()


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--op", help="the operation you want to perform")
    parser.add_argument("--orders", help="comma separated list of order numbers")
    parser.add_argument("--ticker_pair", help="ticker pair")
    parser.add_argument("--dry_run", help="dry run", default=True, type=bool)



    args = parser.parse_args()

    if args.op:
        if args.op == "add_order":
            add_orders(args.orders, args.ticker_pair)
        if args.op == "get_orders":
            get_orders(args.orders, args.ticker_pair)
        if args.op == "recon":
            reconcile(args.ticker_pair, args.dry_run)
    else:
        print("no op argument")


