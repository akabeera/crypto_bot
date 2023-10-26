import os
import ccxt
import time
import talib
import pandas as pd
from decimal import *
from dotenv import load_dotenv
from pymongo import MongoClient

from crypto_utils import fetch_ticker, fetch_ohlcv, create_buy_order, create_sell_order
from supported_crypto import crpto_whitelist, crypto_blacklist
from constants import TICKS_INTERVAL, TAKE_PROFIT_THRESHOLDS, MAX_SPEND, BUY_AMOUNT, AVG_DOWN_THRESHOLD
from trading_utils import calculate_bollinger_bands, calculate_cost_basis, is_oversold, is_overbought
from trading.trade import Trade
from crypto_bot import CryptoBot

import logging
import logging.config

logger = logging.getLogger(__name__)

def configureLogger(logLevel: str):
    logging.config.fileConfig("./config/logging.conf", disable_existing_loggers=False)

    if (not logLevel): return
    numeric_level = getattr(logging, logLevel.upper(), None)
    if  not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % logLevel)

    logging.getLogger().setLevel(numeric_level)


configureLogger("INFO")

load_dotenv()

API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')

MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_CONNECTION_STRING = "localhost:27017"

client = MongoClient(MONGO_CONNECTION_STRING)
db = client.get_database("crypto-bot")
trades_collection = db.trades
sell_orders_collection = db.sell_orders

exchange_id = 'coinbase'
exchange_class = getattr(ccxt, exchange_id)
exchange = exchange_class({
    'apiKey': API_KEY,
    'secret': API_SECRET
})
exchange.options["createMarketBuyOrderRequiresPrice"] = False

if __name__ == "__main__":

    crypto_bot =  CryptoBot()

    idx = 0

    remaining_spend = MAX_SPEND
    testing_overbought = {}

    while True:
        N = len(crpto_whitelist)
        ticker = crpto_whitelist[N-idx-1]

        idx += 1
        if idx == N:
            logger.info("sleeping {} seconds".format(TICKS_INTERVAL))
            time.sleep(TICKS_INTERVAL)
            idx = 0

        ticker_pair = "{}/USD".format(ticker)

        if ticker in crypto_blacklist:
            logger.info("blacklisted, skipping {}".format(ticker))
            continue

        ohlcv = fetch_ohlcv(exchange, ticker_pair)

        if (ohlcv == None):
            logger.error("unable to fetch ohlc, skipping")
            continue

        if len(ohlcv) == 0:
            logger.warning(f"fetchOHLCV return empty data for ticker: {ticker_pair}, skipping")
            continue

        df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        df = calculate_bollinger_bands(df, window=20, std_dev=2)

        # Add RSI and MACD to the dataframe
        df['RSI'] = talib.RSI(df['close'])
        df['MACD'], df['MACD_signal'], _ = talib.MACD(df['close'])

        last_row = df.iloc[-1]

        ticker_filter = {
            'symbol': ticker_pair
        }
        num_positions = trades_collection.count_documents(ticker_filter)

        my_positions = None
        if (num_positions > 0):
            positions = trades_collection.find(ticker_filter)
            my_positions = calculate_cost_basis(ticker_pair, positions)

        ticker_info = fetch_ticker(exchange, ticker)
        if (not ticker_info):
            logger.error("unable to fetch ticker info for ticker: {}".format(ticker))
            continue
    
        if (not ticker_info['ask']):
            logger.error('no ask proce for ticker: {}'.format(ticker))
            continue

        ask = Decimal(ticker_info['ask'])

        take_profit = False
        profit = Decimal(0)
        avg_trade = None
        if my_positions != None: 
            avg_trade = my_positions[0]
            profit = Decimal(((ask * avg_trade.shares) - (avg_trade.price * avg_trade.shares) - (avg_trade.fee*2)) / (avg_trade.price * avg_trade.shares))
            for profit_threshold in TAKE_PROFIT_THRESHOLDS:
                if profit >= Decimal(profit_threshold):
                    take_profit = True
                    break
        
        if avg_trade:
            logger.info(f"{ticker_pair}: unrealized_gain: {profit*100}%")
        else:
            logger.info(f"{ticker_pair}: na")

        # Sell condition
        if take_profit:
            take_profit = False

            # if (not is_overbought(last_row)):
            #     logger.info(f"{ticker_pair}: overbought signal didn't trigger, current profit at {profit*100}% but price may go higher skipping buy")
            #     continue

            logger.info(f"{ticker_pair}: overbought signal triggered, taking profit: {profit*100}%")
            sell_order = create_sell_order(exchange, ticker_pair, float(avg_trade.shares), float(ask))
            if (sell_order != None):

                logger.info(f"{ticker_pair}: SELL EXECUTED at price: {sell_order['average']}, amount: {sell_order['filled']}, total: {sell_order['info']['total_value_after_fees']}")
                closed_position = {
                    'sell_order': sell_order,
                    'closed_positions': my_positions[1]
                }
                sell_orders_inserted_id = sell_orders_collection.insert_one(closed_position).inserted_id
                deleteResult = trades_collection.delete_many(ticker_filter)

                cost = sell_order['cost']
                #remaining_spend = remaining_spend + (cost/2)

        if profit < Decimal(AVG_DOWN_THRESHOLD):
            amount = BUY_AMOUNT
            logger.info(f"{ticker_pair}: current price lower than current position at {profit*100}%, averaging down")


            # if not is_oversold(last_row):
            #     logger.info(f"{ticker_pair}: OVERSOLD not triggered yet, waiting to average down")
            #     continue
            # else:
            #     logger.info(f"{ticker_pair}: OVERSOLD signal triggered!")

            if (remaining_spend <= amount):
                logger.warning(f"{ticker_pair}: surpassed max spend amount, skipping buy order")
                continue

            order = create_buy_order(exchange, ticker_pair, amount)
            if (not order):
                logger.error(f"{ticker_pair}: FAILED to execute buy order")
                continue

            remaining_spend = remaining_spend - amount
            inserted_id = trades_collection.insert_one(order).inserted_id
            logger.info(f"inserted trade into DB, id: {inserted_id}")
            logger.info(f"BUY order executed. symbol: {ticker}, price: {order['price']}, amount: {order['filled']}, fees: {order['fee']['cost']}, cost: {order['cost']}")

        elif is_oversold(last_row):
            # Buy condition
            amount = BUY_AMOUNT
            # TODO: uncomment for testing
            #amount = 1
            #ticker = "BTC/USD"
            logger.info(f"{ticker_pair}: BUY SIGNAL triggered. remaing_spend: {remaining_spend}")

            if (remaining_spend <= 0):
                logger.warning(f"{ticker_pair}: surpassed max spend amount, skipping buy order")
                continue
            
            if (profit > Decimal(-0.1)):
                logger.info(f"{ticker_pair}: ABORTING BUY, current price is not yet worth averaging down")
                continue
            else: 
                logger.info(f"{ticker_pair}: current price lower than threshold to AVG DOWN current position")

            # if (avg_trade != None):
            #     avg_down_threshold = Decimal(AVG_DOWN_THRESHOLD)
            #     diff = (avg_trade.price - ask)/avg_trade.price
            #     if diff < avg_down_threshold:
            #         logger.info(f"{ticker_pair}: ABORTING BUY, current price: {ask}, current_position: {avg_trade.price}, difference: {diff*100}%, skip buy order")
            #         continue
            #     else:
            #         logger.info(f"{ticker_pair}: EXECUTING BUY, current price difference {diff*100}% (more than {avg_down_threshold * 100}%), buying to average down cost")

            order = create_buy_order(exchange, ticker_pair, amount)
            if (not order):
                logger.error(f"{ticker_pair}: FAILED to execute buy order")
                continue

            remaining_spend = remaining_spend - amount
            inserted_id = trades_collection.insert_one(order).inserted_id
            logger.info(f"inserted trade into DB, id: {inserted_id}")
            logger.info(f"BUY order executed. symbol: {ticker}, price: {order['price']}, amount: {order['filled']}, fees: {order['fee']['cost']}, cost: {order['cost']}")
        
        time.sleep(1)
   