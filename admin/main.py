import os
import argparse
import pprint
from decimal import *


from dotenv import load_dotenv
from utils.exchange_service import ExchangeService
from utils.mongodb_service import MongoDBService
from utils.reconciliation import ReconciliationActions, handle_partial_order, reconcile
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


def reconcile_with_exchange(ticker_pair: str, dry_run: bool):
    exchange_orders = exchange_service.execute_op(ticker_pair, "fetchOrders")
    if exchange_orders is None:
        print("ERROR: Failed to fetch orders from exchange, aborting")
        return
    
    print(f"{ticker_pair} has {len(exchange_orders)} orders")
    
    buy_orders = []
    reconciliation_actions = ReconciliationActions()
    reconciliation_actions.sell_order_collection = SELL_ORDERS_COLLECTION
    reconciliation_actions.buy_order_collection = TRADES_COLLECTION

    sell_orders_count = 0
    buy_orders_count = 0

    total = Decimal(0)
    for idx, order in enumerate(exchange_orders):
        side = order['side']
        id = order["id"]

        if side == "buy":
            buy_orders_count += 1
            if order["filled"] != order["amount"]:
                print(f"WARNING: buy order {order["id"]} was partially filled")
            buy_orders.append(order)
            total += Decimal(order["filled"])
        else:
            sell_orders_count += 1
            order_info = order["info"]
            completion_pct = Decimal(order_info["completion_percentage"])
            print(f"{ticker_pair} evaluating sell order:{order["id"]}, date: {order["datetime"]}, completion percent: {completion_pct}")

            if completion_pct == ZERO:
                continue

            total -= Decimal(order["filled"])

            if completion_pct == ONE_HUNDRED:
                db_sell_order = mongodb_service.query(SELL_ORDERS_COLLECTION, {"sell_order.id": id})
                if len(db_sell_order) > 0:
                    closed_positions = db_sell_order[0]["closed_positions"]
                    ids_in_db = {pos["id"] for pos in closed_positions}
                    if len(closed_positions) != len(buy_orders):
                        print(f"WARNING: sell order {id} missing positions")
                        missing_buy_orders = [bo for bo in buy_orders if bo["id"] not in ids_in_db]
                        print (f"WARNING: num of missing buy orders: {len(missing_buy_orders)}")
                        reconciliation_actions.buy_order_insertions.extend(missing_buy_orders)

                buy_orders.clear()
                continue

            actions = handle_partial_order(order, buy_orders)
            buy_orders.clear()

            reconciliation_actions.sell_order_deletions.extend(actions.sell_order_deletions) 
            reconciliation_actions.sell_order_insertions.extend(actions.sell_order_insertions)
            reconciliation_actions.buy_order_deletions.extend(actions.buy_order_deletions)
            reconciliation_actions.buy_order_updates.extend(actions.buy_order_updates)

        if idx == len(exchange_orders) - 1:
            reconciliation_actions.buy_order_insertions.extend(buy_orders)

    print (f"{ticker_pair} had {buy_orders_count} buys & {sell_orders_count} sells and final tally of {total} shares")
    pprint.pprint(reconciliation_actions, depth=10)
    if dry_run:
        return
    
    reconcile(reconciliation_actions, mongodb_service)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--op", help="the operation you want to perform")
    parser.add_argument("--orders", help="comma separated list of order numbers")
    parser.add_argument("--ticker_pair", help="ticker pair")
    parser.add_argument("--dry_run", help="dry run", default="True", type=str)

    args = parser.parse_args()

    if args.op:
        if args.op == "add_order":
            add_orders(args.orders, args.ticker_pair)
        if args.op == "get_orders":
            get_orders(args.orders, args.ticker_pair)
        if args.op == "recon":
            dry_run = args.dry_run == "True"
            reconcile_with_exchange(args.ticker_pair, dry_run)
    else:
        print("no op argument")


