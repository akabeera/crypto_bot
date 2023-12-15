import os
import argparse
from decimal import *

from dotenv import load_dotenv
from utils.exchange_service import ExchangeService
from utils.mongodb_service import MongoDBService

load_dotenv()


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

    MONGO_CONNECTION_STRING = os.getenv("MONGO_CONNECTION_STRING")

    DB_NAME = "crypto-bot"
    SELL_ORDERS_COLLECTION = "sell_orders"
    TRADES_COLLECTION = "trades"

    mongodb_service = MongoDBService(MONGO_CONNECTION_STRING, DB_NAME)

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


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--op", help="the operation you want to perform")
    parser.add_argument("--orders", help="comma separated list of order numbers")
    parser.add_argument("--ticker_pair", help="ticker pair")

    args = parser.parse_args()

    if args.op:
        if args.op == "add_order":
            add_orders(args.orders, args.ticker_pair)
    else:
        print("no op argument")


