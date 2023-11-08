import os
from decimal import *

from dotenv import load_dotenv
from utils.exchange_service import ExchangeService

load_dotenv()

if __name__ == "__main__":

    exchange_config = {
        'exchange_id': "coinbase",
        'market_order_type_buy': "market",
        'market_order_type_sell': "limit",
        'limit_order_time_limit': 10,
        'create_market_buy_order_requires_price': False
    }
    exchange_service = ExchangeService(exchange_config)


    order_id = "6687ab35-dbfe-47b8-afbc-864ac20d8168"
    ticker_pair = "CRO/USD"
    order = exchange_service.execute_op(ticker_pair, op="fetchOrder", order_id=order_id)
    print (order)