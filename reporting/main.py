import os
import utils.constants as CONSTANTS
from decimal import *

from dotenv import load_dotenv
from utils.mongodb_service import MongoDBService
from utils.trading import calculate_profit_percent, calculate_avg_position
from utils.exchange_service import ExchangeService

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

    exchange_config = {
        'exchange_id': "coinbase",
        'limit_order_num_periods_limit': 10,
        'create_market_buy_order_requires_price': False
    }
    exchange_service = ExchangeService(exchange_config)

    trades_dict = {}
    for position in open_positions:
        symbol = position["symbol"]
        if symbol not in trades_dict:
            trades_dict[symbol] = [position]
        else: 
            trades_dict[symbol].append(position)

    total_market_value = 0
    print("\nOpen Positions\n")
    print("{:20s} {:23s} {:20s} {:22s} {:25s} {:24s} {:15s} {:15s}".format("symbol", "shares", "avg_price", "profit_pct", "market_value", "bid_price", "total_fees", "num_trades"))
    for symbol, trades in trades_dict.items():
        if symbol == "VGX/USD":
            continue 
        ticker_info = exchange_service.execute_op(ticker_pair=symbol, op=CONSTANTS.OP_FETCH_TICKER)
        if not ticker_info:
            print("{:15s} {:35s} {:4s}".format(symbol, "--", "--"))
            continue

        if ticker_info["bid"] is None:
            continue

        bid_price = ticker_info["bid"]
        avg_position = calculate_avg_position(trades)
        profit_pct = calculate_profit_percent(avg_position, bid_price) * 100
        price = ticker_info["bid"]
        shares = avg_position["amount"]
        avg_price = avg_position["price"]
        total_fees = avg_position["fee"]["cost"]
        market_value = price * shares
        total_market_value += market_value
        print("{:10s} {:20.12f}   ${:20.12f} {:20.12f}%    ${:20.12f}    ${:20.12f}    ${:20.12f} {:10d}".format(symbol, shares, avg_price, profit_pct, market_value, bid_price, total_fees, len(trades)))
        
    print(f"\nTotal Market Value: {total_market_value}")

if __name__ == "__main__":

    MONGO_CONNECTION_STRING = os.getenv("MONGO_CONNECTION_STRING")
    DB_NAME = "crypto-bot"

    SELL_ORDERS_COLLECTION = "sell_orders"
    TRADES_COLLECTION = "trades"

    closed_positions_performance(MONGO_CONNECTION_STRING, DB_NAME, SELL_ORDERS_COLLECTION)    
    open_positions_performance(MONGO_CONNECTION_STRING, DB_NAME, TRADES_COLLECTION)

