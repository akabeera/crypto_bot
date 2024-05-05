import os
import utils.constants as CONSTANTS
import time
from decimal import *


from dotenv import load_dotenv
from utils.mongodb_service import MongoDBService
from utils.trading import calculate_profit_percent, calculate_avg_position
from utils.exchange_service import ExchangeService

exchange_config = {
    CONSTANTS.CONFIG_EXCHANGE_ID: "coinbase",
    CONSTANTS.CONFIG_LIMIT_ORDER_NUM_PERIODS_LIMIT: 10,
    'create_market_buy_order_requires_price': False
}
exchange_service = ExchangeService(exchange_config)

if __name__ == "__main__":

    MONGO_CONNECTION_STRING = os.getenv("MONGO_CONNECTION_STRING")
    DB_NAME = "crypto-bot"

    SELL_ORDERS_COLLECTION = "sell_orders"
    TRADES_COLLECTION = "trades"


    tickers = ["FET/USD", "IOTX/USD", "BTC/USD", "SHIB/USD", "ETH/USD", "SOL/USD", "MATIC/USD", "LPT/USD", "ATOM/USD", "AVAX/USD", "ICP/USD", "FIL/USD", "DOT/USD", "AAVE/USD", "MKR/USD", "MANA/USD", "COMP/USD", "AMP/USD", "DOGE/USD", "ASM/USD"]
    orders = dict()

    balance = 500
    transaction_amount = 100
    fee_pct = 0.003
    profit = 0
    profit_threshold = .007
    buy_pct_threshold = -0.005

    while True:
        for ticker in tickers:
            ohlcvs = exchange_service.execute_op(ticker, op=CONSTANTS.OP_FETCH_OHLCV)
            tickerInfo = exchange_service.execute_op(ticker, op=CONSTANTS.OP_FETCH_TICKER)

            if ohlcvs is None or tickerInfo is None:
                print(f"{ticker}: error hitting API, skipping")
                continue

            bid = tickerInfo["bid"]
            ask = tickerInfo["ask"]

            if ticker in orders:
                order = orders[ticker]
                shares = order['shares']
                cost = order['price'] * shares
                profit_dollars = ((shares * bid) - (cost + (order['fee']*2)))
                profit_pct = profit_dollars/cost 

                if profit_dollars > profit_threshold:
                    print(f"{ticker}: selling, profit($): {profit_dollars}, profit(%): {profit_pct}")
                    profit += profit_dollars
                    balance += profit_dollars

                    del orders[ticker]
                    continue

            if len(ohlcvs) < 250:
                #print (f"{ticker}: not enouch candles: {len(ohlcvs)}, skipping")
                continue
            
            lowest_pct_diff = 0
            for idx, ohlcv in reversed(list(enumerate(ohlcvs))):
                close = ohlcv[4]
                pct_diff = (ask - close)/bid
                if pct_diff < lowest_pct_diff:
                    lowest_pct_diff = pct_diff
                if pct_diff < buy_pct_threshold:
                    print(f"{ticker}: buy at idx: {idx}, pct_dif: {pct_diff}, timestamp: {ohlcv[0]}")
                    if ticker in orders:
                        print(f"{ticker}: WARNING already have positing, abort buying")
                    else:
                        if balance >= transaction_amount:
                            fee = transaction_amount * fee_pct
                            orders[ticker] = {
                                'ticker': ticker,
                                'price': ask,
                                'fee': fee,
                                'shares': ((transaction_amount-fee)/ask)
                            }

                            balance -= transaction_amount
                            print(f"{ticker}: remaining balance: {balance}")
                        else:
                            print(f"{ticker}: WARNING: insufficient balance")
                    break

            #print(f"{ticker}: lowest pct diff: {lowest_pct_diff}")
            time.sleep(5)

        print(f"profit so far: {profit}")
        time.sleep(300) 
        
    pass
