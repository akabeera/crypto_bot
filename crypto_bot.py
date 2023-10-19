import json
import os
import ccxt
import time
import pandas as pd
from ccxt import BadSymbol, RequestTimeout, AuthenticationError, NetworkError, ExchangeError
from dotenv import load_dotenv
from pymongo import MongoClient


from strategies.base_strategy import BaseStrategy
from strategies.utils import strategy_factory

import logging
import logging.config

load_dotenv()

logger = logging.getLogger(__name__)

def configureLogger(logLevel: str):
    logging.config.fileConfig("./config/logging.conf", disable_existing_loggers=False)

    if (not logLevel): return
    numeric_level = getattr(logging, logLevel.upper(), None)
    if  not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % logLevel)

    logging.getLogger().setLevel(numeric_level)

configureLogger("INFO")

CONFIG_FILE = 'config.json'
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
MONGO_CONNECTION_STRING = os.getenv('MONGO_CONNECTION_STRING')

class CryptoBot:
    
    client = MongoClient(MONGO_CONNECTION_STRING)

    def __init__(self):
        with open(CONFIG_FILE) as f:
            self.config = json.load(f)
            print (self.config)

        self.max_spend = self.config["max_spend"]
        self.amount_per_transaction = self.config["amount_per_transaction"]
        self.sleep_interval = self.config["sleep_interval"]
        self.currency: str = self.config["currency"]
        self.currency_trading_sleep_interval = self.config["currency_trading_sleep_interval"]
        self.crypto_whitelist = self.config["support_currencies"]
        self.crypto_blacklist = self.config["blacklisted_currencies"]
        self.mongo_db_name = self.config["mongodb_db_name"]

        exchange_id = self.config["exchange_id"]
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({
            'apiKey': API_KEY,
            'secret': API_SECRET
        })

        self.exchange.options["createMarketBuyOrderRequiresPrice"] = False
        
        strategiesJson = self.config["strategies"]
        strategies = []
        self.max_strategy_priority = 0
        for strategyJson in strategiesJson:
            strategies.append(strategy_factory(strategyJson))

        self.db = CryptoBot.client.get_database(self.mongo_db_name)
        self.trades_collection = self.db.trades
        self.sell_orders_collection = self.db.sell_orders
            
        #self.init_strategies(self.config)

    
    def run(self):
        idx = 0
        N = len(self.crypto_whitelist)

        while True:

            if idx == N:
                time.sleep(self.sleep_interval)
                idx = 0

            idx += 1 
            ticker:str = self.crypto_whitelist[N-idx-1]
            ticker_pair = "{}/{}".format(ticker.upper(), self.currency.upper())

            if ticker in self.crypto_blacklist:
                logger.info("blacklisted, skipping {}".format(ticker))
                continue

            ohlcv = self.fetch_ohlcv(ticker_pair)

            if ohlcv == None:
                logger.error("unable to fetch ohlc, skipping")
                continue

            if len(ohlcv) == 0:
                logger.warning(f"fetchOHLCV return empty data for ticker: {ticker_pair}, skipping")
                continue

            df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])

    def fetch_ohlcv(self, ticker_pair:str):
        try:
            if (not self.exchange.has['fetchOHLCV']):
                logger.warn('exchange does not support fetchOHLCV')
                return None
            
            ohlcv = self.exchange.fetch_ohlcv(ticker_pair)
            return ohlcv
            
        except BadSymbol as e:
            logger.error("unable to fetch ohlcv {}, error: {}".format(ticker_pair, e))
            return None
        except RequestTimeout as e:
            logger.warn("fetchOHLCV request timed out for {}, error: {}".format(ticker_pair, e))
            return None
        except AuthenticationError as e:
            logger.warn("fetchOHLCV request auth error for {}, error: {}".format(ticker_pair, e))
            return None
        except NetworkError as e:
            logger.warn("fetchOHLCV network error {}, error: {}".format(ticker_pair, e)) 
            return None
        except ExchangeError as e:
            logger.warn('fetchOHLCV: exchange error: {}'.format(e))
            return None
