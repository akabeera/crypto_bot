import os
import argparse
import pprint
from decimal import *
from operator import itemgetter

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

def db_sell_order_reconciliation(sell_order, amount) -> Decimal:
    total = 0
    closed_positions = sell_order["closed_positions"]

    for cp in closed_positions:
        total += Decimal(cp["filled"])

    return total - amount


def reconcile_with_exchange(ticker_pair: str, dry_run: bool):

    #transactions = exchange_service.execute_op(ticker_pair, "fetchMyTrades")

    exchange_orders = exchange_service.execute_op(ticker_pair, "fetchOrders")
    if exchange_orders is None:
        print("ERROR: Failed to fetch orders from exchange, aborting")
        return
    
    order_cache = {}
    for order in exchange_orders:
        order_cache[order["id"]] = order
    
    print(f"{ticker_pair} has {len(exchange_orders)} orders")
    reconciliation_actions = ReconciliationActions()
    reconciliation_actions.sell_order_collection = SELL_ORDERS_COLLECTION
    reconciliation_actions.buy_order_collection = TRADES_COLLECTION

    sell_orders_count = 0
    buy_orders_count = 0

    total = Decimal(0)

    buy_orders = []
    for idx, order in enumerate(exchange_orders):

        side = order['side']
        id = order["id"]
        filled = Decimal(order["filled"])
        amount = Decimal(order["amount"])

        if side == "buy":
            buy_orders_count += 1
            if filled != amount:
                print(f"WARNING: buy order {id} was partially filled")
            buy_orders.append(order)
            total += filled
        else:
            sell_orders_count += 1
            order_info = order["info"]
            completion_pct = Decimal(order_info["completion_percentage"])
            total -= filled
            print(f"{ticker_pair} evaluating sell order:{id}, date: {order['datetime']}, completion percent: {completion_pct}, running total: {total}")

            if completion_pct == ZERO:
                continue

            # db_sell_order = mongodb_service.query(SELL_ORDERS_COLLECTION, {"sell_order.id": id})
            # if len(db_sell_order) > 0:
            #     if completion_pct < ONE_HUNDRED:
            #         print(f"{ticker_pair} WARNING: partial sell_order already in DB, aborting")
            #         break

            #     db_sell_order_diff = db_sell_order_reconciliation(db_sell_order[0], filled)
            #     #print(f"{ticker_pair} db sell order's closed positions diff: {db_sell_order_diff}")
                
            #     closed_positions = db_sell_order[0]["closed_positions"]

            #     for cp in closed_positions:
            #         order_from_cb = order_cache[cp["id"]]
            #         cp_filled = cp["filled"]
            #         cb_filled = order_from_cb["filled"]
            #         if cp_filled != cb_filled:
            #             print(f"{ticker_pair} WARNING, order {cp['id']} from DB doesn't match up, filled from DB: {cp_filled}, filled from CB: {cb_filled}")

            #     order_ids_to_remove = {pos["id"] for pos in closed_positions}
            #     buy_orders = [bo for bo in buy_orders if bo["id"] not in order_ids_to_remove]
            #     continue


            buy_orders_blacklist = set()

            # next_idx = idx+1
            # while next_idx < len(exchange_orders):
            #     next_order = exchange_orders[next_idx]
            #     next_completion_pct = Decimal(next_order["info"]["completion_percentage"])
            #     if next_completion_pct == ONE_HUNDRED:
            #         next_db_sell_order = mongodb_service.query(SELL_ORDERS_COLLECTION, {"sell_order.id": next_order["id"]})
            #         if len(next_db_sell_order) > 0:
            #             next_closed_positions = next_db_sell_order[0]["closed_positions"]
            #             buy_orders_blacklist = {np["id"] for np in next_closed_positions}
            #             break
            #     next_idx += 1

            actions = handle_partial_order(order, buy_orders, buy_orders_blacklist)
            buy_orders_total = ZERO
            for db in actions.buy_order_deletions:
                buy_orders_total += Decimal(db["filled"])
            buy_order_update = ZERO
            if len(actions.buy_order_updates) > 0:
                buy_order_update = Decimal(actions.buy_order_updates[0]['filled'])
            print(f"{ticker_pair} filled from CB order: {filled}, tally after handling partial sell order: {buy_orders_total - buy_order_update}")

            reconciliation_actions.sell_order_deletions.extend(actions.sell_order_deletions) 
            reconciliation_actions.sell_order_insertions.extend(actions.sell_order_insertions)
            reconciliation_actions.buy_order_deletions.extend(actions.buy_order_deletions)
            reconciliation_actions.buy_order_updates.extend(actions.buy_order_updates)
            reconciliation_actions.buy_order_insertions.extend(actions.buy_order_insertions)

            ids_to_cleanup = {bod["id"] for bod in actions.buy_order_deletions}
            buy_orders = [bo for bo in buy_orders if bo["id"] not in ids_to_cleanup]
            if len(actions.buy_order_updates) > 0:
                buy_orders.insert(0, actions.buy_order_updates[0])

            reconciliation_actions.buy_order_updates = [bu for bu in reconciliation_actions.buy_order_updates if bu["id"] not in ids_to_cleanup]
            
        if idx == len(exchange_orders) - 1:
            reconciliation_actions.buy_order_insertions.extend(buy_orders)

    print (f"{ticker_pair} had {buy_orders_count} buys & {sell_orders_count} sells and final tally of {total} shares")
    pprint.pprint(reconciliation_actions, depth=10)

    #calculate current position based on the recon actions
    
    recon_total = 0
    for buy_inserts in reconciliation_actions.buy_order_insertions:
        recon_total += buy_inserts["filled"]
    for buy_updates in reconciliation_actions.buy_order_updates:
        recon_total += buy_updates["filled"]

    print(f"{ticker_pair} tally of recon actions, {recon_total} shares")

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


