import os
import ccxt
import time
import talib
import pandas as pd
from decimal import *
from dotenv import load_dotenv

from crypto_utils import fetch_ticker, fetch_ohlcv, create_buy_order, create_sell_order
from supported_crypto import crpto_whitelist, crypto_blacklist
from constants import TICKS_INTERVAL, TAKE_PROFIT_THRESHOLDS, MAX_SPEND, BUY_AMOUNT, AVG_DOWN_THRESHOLD
from trading_utils import calculate_bollinger_bands, calculate_cost_basis, is_oversold, is_overbought
from trading.trade import Trade
from crypto_bot import CryptoBot
from utils.mongodb_service import MongoDBService

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

exchange_id = 'coinbase'
exchange_class = getattr(ccxt, exchange_id)
exchange = exchange_class({
    'apiKey': API_KEY,
    'secret': API_SECRET
})

exchange.options["createMarketBuyOrderRequiresPrice"] = False

if __name__ == "__main__":

    MONGO_CONNECTION_STRING = os.getenv("MONGO_CONNECTION_STRING")
    if MONGO_CONNECTION_STRING is None:
        logger.error("MongoDB connection string is not defined.  Aborting!")
        exit()
    
    crypto_bot =  CryptoBot(MONGO_CONNECTION_STRING)
    crypto_bot.run()

    remaining_spend = MAX_SPEND