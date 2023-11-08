import os
from decimal import *

from dotenv import load_dotenv
from utils.mongodb_service import MongoDBService

load_dotenv()

def closed_positions_performance(mongo_connection_string, db_name, table_name):
    mongodb_service = MongoDBService(mongo_connection_string, db_name)
    closed_positions = mongodb_service.query(table_name)

    print(f"Number of Trades: {len(closed_positions)}")

    ticker_dict = {}

    SELL_ORDER = "sell_order"
    CLOSED_POSITIONS = "closed_positions"

    for position in closed_positions:
        sell_order = position[SELL_ORDER]
        closed_positions = position[CLOSED_POSITIONS]

        ticker = sell_order["symbol"]

        if ticker not in ticker_dict:
            ticker_dict[ticker] = {
                "ticker": "",
                "count": 0,
                "sell_amount": Decimal(0),
                "sell_fee": Decimal(0),
                "buy_amount": Decimal(0),
                "buy_fee": Decimal(0)
            }

        sell_amount = Decimal(sell_order["cost"])
        sell_fee = Decimal(sell_order["fee"]["cost"])

        ticker_object = ticker_dict[ticker]
        ticker_object["ticker"] = ticker
        ticker_object["count"] += 1
        ticker_object["sell_fee"] += sell_fee
        ticker_object["sell_amount"] += sell_amount

        for cp in closed_positions:
            ticker_object["buy_amount"] += Decimal(cp["cost"])
            ticker_object["buy_fee"] += Decimal(cp["fee"]["cost"])

    total_profit = Decimal(0)
    for ticker, ticker_info in ticker_dict.items():
        profit = ticker_info["sell_amount"] - ticker_info["sell_fee"] - ticker_info["buy_amount"] - ticker_info["buy_fee"]
        ticker_info["profit"] = profit 
        total_profit += profit

    sorted_by_profit = sorted(ticker_dict.items(), key=lambda item: item[1]["profit"], reverse=True)
    
    for item in sorted_by_profit:
        ticker_info = item[1]
        print("{:15s} {:35.30f} {:4d}".format(ticker_info["ticker"], ticker_info["profit"], ticker_info["count"]))
    
    
    print(f"Total Performance($): ${total_profit}")
    

def open_positions_performance(mongo_connection_string, db_name, table_name):
    mongodb_service = MongoDBService(mongo_connection_string, db_name)
    open_positions = mongodb_service.query(table_name)

if __name__ == "__main__":

    MONGO_CONNECTION_STRING = os.getenv("MONGO_CONNECTION_STRING")
    DB_NAME = "crypto-bot"

    SELL_ORDERS_COLLECTION = "sell_orders"
    TRADES_COLLECTION = "TRADES"

    closed_positions_performance(MONGO_CONNECTION_STRING, DB_NAME, SELL_ORDERS_COLLECTION)
    open_positions_performance(MONGO_CONNECTION_STRING, DB_NAME, TRADES_COLLECTION)

