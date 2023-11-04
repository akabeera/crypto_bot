import json
import os
import ccxt
import time
import pandas as pd
from decimal import *
from ccxt import BadSymbol, RequestTimeout, AuthenticationError, NetworkError, ExchangeError
from dotenv import load_dotenv

from strategies.strategy_factory import strategy_factory
from strategies.utils import calculate_profit_percent, calculate_avg_position
from trading.trade_action import TradeAction
from trading.trade import Trade
from utils.mongodb_service import MongoDBService
from utils.constants import ZERO

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

class CryptoBot:

    def __init__(self, db_connection_string):
        with open(CONFIG_FILE) as f:
            self.config = json.load(f)

        self.max_spend = Decimal(self.config["max_spend"])
        self.amount_per_transaction = Decimal(self.config["amount_per_transaction"])
        self.reinvestment_percent = Decimal(self.config["reinvestment_percent"]/100)
        self.remaining_balance = self.max_spend
        self.limit_order_time_limit = 10

        self.currency: str = self.config["currency"]
        self.sleep_interval = self.config["sleep_interval"]
        self.inter_currency_sleep_interval = self.config["inter_currency_sleep_interval"]
        self.crypto_whitelist = self.config["support_currencies"]
        self.crypto_blacklist = self.config["blacklisted_currencies"]

        mongodb_config = self.config["mongodb"] 
        self.mongodb_db_name = mongodb_config["db_name"]
        self.current_positions_collection = mongodb_config["current_positions_collection"]
        self.closed_positions_collection = mongodb_config["closed_positions_collection"]
        self.mongodb_service = MongoDBService(db_connection_string, self.mongodb_db_name)

        exchange_id = self.config["exchange_id"]
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({
            'apiKey': API_KEY,
            'secret': API_SECRET
        })

        self.exchange.options["createMarketBuyOrderRequiresPrice"] = False            
        self.init_strategies()

    def init_strategies(self):
        strategies_json = self.config["strategies"]

        self.strategies = {}
        self.strategies_priorities = []
        
        for strategy_json in strategies_json:
            strategy_priority = strategy_json["priority"]
            strategy_object = strategy_factory(strategy_json)

            if strategy_object is None:
                logger.warn(f"Encountered unsupported strategy config: {strategy_json}")
                continue

            if strategy_priority in self.strategies:
                self.strategies[strategy_priority].append(strategy_object)
            else:
                self.strategies[strategy_priority] = [strategy_object]

            if strategy_priority not in self.strategies_priorities:
                self.strategies_priorities.append(strategy_priority)

        self.strategies_priorities.sort()
            

    def run(self):
        idx = 0
        N = len(self.crypto_whitelist)

        while True:

            if idx == N:
                logger.info(f"heartbeat!")
                time.sleep(self.sleep_interval)
                idx = 0

            ticker:str = self.crypto_whitelist[N-idx-1]
            idx += 1 

            ticker_pair:str = "{}/{}".format(ticker.upper(), self.currency.upper())

            if ticker in self.crypto_blacklist:
                logger.info(f"{ticker_pair}: blacklisted, skipping")
                continue

            ticker_filter = {
                'symbol': ticker_pair
            }
            trades = self.mongodb_service.query(self.current_positions_collection, ticker_filter)
            avg_position = calculate_avg_position(trades)            

            ohlcv = self.fetch_ohlcv(ticker_pair)
            if ohlcv == None or len(ohlcv) == 0:
                logger.error(f"{ticker_pair}: unable to fetch ohlcv, skipping")
                continue

            candles_df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            ticker_info = self.fetch_ticker(ticker_pair)

            if (not ticker_info or ticker_info['ask'] is None or ticker_info['bid'] is None):
                logger.error(f"{ticker_pair}: unable to fetch ticker info or missing ask/bid prices, skipping")
                continue

            ask_price = ticker_info['ask']
            bid_price = ticker_info['bid']
    
            for priority in self.strategies_priorities:
                cuurrent_strategies = self.strategies[priority]

                action = TradeAction.NOOP
                for s_idx, strgy in enumerate(cuurrent_strategies):
                    curr_action = strgy.eval(avg_position, candles_df, ticker_info)    
                    if s_idx == 0:
                        action = curr_action
                    else:
                        if action != curr_action:
                            action = TradeAction.NOOP
                            break

                if action == TradeAction.BUY:
                    logger.info(f"{ticker_pair}: executing BUY @ ask price: ${ask_price}")
                    self.handle_buy_order(ticker_pair)
                    break
                elif action == TradeAction.SELL:
                    logger.info(f"{ticker_pair}: executing SELL @ bid price: ${bid_price}, shares:{avg_position["amount"]}")
                    self.handle_sell_order(ticker_pair, float(avg_position["amount"]), float(bid_price))
                    break
            
            expected_profit = calculate_profit_percent(avg_position, ticker_info)
            logger.info(f"{ticker_pair}: executed {action} action, expected profit: {expected_profit}")
            time.sleep(self.inter_currency_sleep_interval)
    
    def handle_buy_order(self, ticker_pair: str):
        if self.remaining_balance < self.amount_per_transaction:
            logger.warn(f"{ticker_pair}: insufficient balance to place buy order, skipping")
            return
        
        order = self.create_buy_order(ticker_pair, self.amount_per_transaction)
        if not order:
            logger.error(f"{ticker_pair}: FAILED to execute buy order")
            return
        self.remaining_balance -= self.amount_per_transaction

        self.mongodb_service.insert_one(self.current_positions_collection, order)
        logger.info(f"{ticker_pair}: BUY executed. price: {order['price']}, shares: {order['filled']}, fees: {order['fee']['cost']}, remaining balance: {self.remaining_balance}")


    def handle_sell_order(self, ticker_pair: str, shares: float, bid_price: float):
        order = self.create_sell_limit_order(ticker_pair, shares, bid_price)

        if not order:
            logger.error(f"{ticker_pair}: FAILED to execute set order")
            return

        proceeds = order['info']['total_value_after_fees']
        ticker_filter = {
            'symbol': ticker_pair
        }
        current_positions = self.mongodb_service.query(self.current_positions_collection, ticker_filter)
        closed_position = {
            'sell_order': order,
            'closed_positions': current_positions
        }

        self.mongodb_service.insert_one(self.closed_positions_collection, closed_position)
        self.mongodb_service.delete_many(self.current_positions_collection, ticker_filter)

        if self.reinvestment_percent > ZERO:
            self.remaining_balance += (Decimal(proceeds) * self.reinvestment_percent)

        logger.info(f"{ticker_pair}: SELL EXECUTED. price: {order['average']}, shares: {order['filled']}, proceeds: {proceeds}, remaining_balance: {self.remaining_balance}")

    
    def fetch_ohlcv(self, ticker_pair:str):
        try:
            if (not self.exchange.has['fetchOHLCV']):
                logger.warn(f"{ticker_pair}: xchange does not support fetchOHLCV")
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
        
    def fetch_ticker(self, ticker_pair: str):
        try:
            if (self.exchange.has['fetchTicker']):
                tickerInfo = self.exchange.fetch_ticker(ticker_pair)
                return tickerInfo
            else:
                logger.warn('unable to fetch ticker: {ticker}')
                return None
        except BadSymbol as e:
            logger.error("unablet to fetch ticker {}, error: {}".format(ticker_pair, e))
            return None
        except RequestTimeout as e:
            logger.warn("fetch_ticker request timed out for {}, error: {}".format(ticker_pair, e))
            return None
        except AuthenticationError as e:
            logger.warn("WARNING: fetch_ticker authentication error {}, error: {}".format(ticker_pair, e))
            return None
        except NetworkError as e:
            logger.warn("WARNING: fetch_ticker network error {}".format(ticker_pair)) 
            return None
        except IndexError as e:
            logger.warn("WARNING: fetch_ticker returned IndexError: {}".format(e))
            return None
        except ExchangeError as e:
            logger.warn('WARNING: fetch_ticker exchange error: {}'.format(e))
            return None
    
    def create_buy_order(self, ticker_pair, amount):
        try:
            order_results = self.exchange.create_market_buy_order(ticker_pair, amount)
            order_id = order_results['info']['order_id']

            order = None
            status = order_results['status']
            while (status != 'closed'):
                time.sleep(1)
                order = self.fetch_order(order_id)
                if (order == None):
                    return None
            
                status = order['status']

            return order
        except BadSymbol as e:
            logger.error("unable to submit create_buy_order for ticker {}, error: {}".format(ticker_pair, e))
            return None
        except RequestTimeout as e:
            logger.warn("create_buy_order request timed out for {}, error: {}".format(ticker_pair, e))
            return None
        except AuthenticationError as e:
            logger.warn("create_buy_order request timed out for {}, error: {}".format(ticker_pair, e))
            return None
        except NetworkError as e:
            logger.warn("create_buy_order network error {}, error: {}".format(ticker_pair, e)) 
            return None
        except ExchangeError as e:
            logger.warn("create_buy_order exchange error {}, error: {}".format(ticker_pair, e)) 
            return None


    def create_sell_order(self, ticker_pair, shares: float, price: float):
        try:
            type = "market"
            side = "sell"
            order_results = self.exchange.create_order(ticker_pair, type, side, shares, price)
            order_id = order_results['info']['order_id']

            order = None
            status = order_results['status']
            while (status != 'closed'):
                time.sleep(1)
                order = self.fetch_order(order_id)
                if (order == None):
                    return None
            
                status = order['status']

            return order

        except BadSymbol as e:
            logger.error("unable to submit create_sell_order for ticker {}, error: {}".format(ticker_pair, e))
            return None
        except RequestTimeout as e:
            logger.warn("create_sell_order request timed out for {}, error: {}".format(ticker_pair, e))
            return None
        except AuthenticationError as e:
            logger.warn("create_sell_order request timed out for {}, error: {}".format(ticker_pair, e))
            return None
        except NetworkError as e:
            logger.warn("create_sell_order network error {}, error: {}".format(ticker_pair, e)) 
            return None
        except ExchangeError as e:
            logger.warn("create_sell_order exchange error {}, error: {}".format(ticker_pair, e)) 
            if e.args and len(e.args) > 0:
                if e.args[0] == 'coinbase {"error":"PERMISSION_DENIED","error_details":"Orderbook is in limit only mode","message":"Orderbook is in limit only mode"}':
                    return self.create_sell_limit_order(ticker_pair, shares, price)

            return None
            
    def create_sell_limit_order(self, ticker_pair, amount: float, price: float):
        try:
            type = "limit"
            side = "sell"
            order_results = self.exchange.create_order(ticker_pair, type, side, amount, price)
            order_id = order_results['info']['order_id']

            order = None
            status = order_results['status']
            idx = 0
            while (status != 'closed'):
                
                if idx == self.limit_order_time_limit:
                    logger.warn(f"{ticker_pair}: limit order not fulfilled within time limit, cancelling order")
                    cancelled_order = self.exchange.cancel_order(order_id, ticker_pair) 
                    logger.warn(f"{ticker_pair}: cancelled_order output: {cancelled_order}")
                    return None

                logger.info(f"{ticker_pair}: waiting for limit_order to be fulfilled, time: {idx}")

                time.sleep(1)
                order = self.fetch_order(order_id)
                if (order == None):
                    return None
                
                idx += 1
                status = order['status']

            return order

        except BadSymbol as e:
            logger.error("create_sell_limit_order unable to submit order for ticker {}, error: {}".format(ticker_pair, e))
            return None
        except RequestTimeout as e:
            logger.warn("create_sell_limit_order request timed out for {}, error: {}".format(ticker_pair, e))
            return None
        except AuthenticationError as e:
            logger.warn("create_sell_limit_order request timed out for {}, error: {}".format(ticker_pair, e))
            return None
        except NetworkError as e:
            logger.warn("create_sell_limit_order network error {}, error: {}".format(ticker_pair, e)) 
            return None
        except ExchangeError as e:
            logger.warn("create_sell_limit_order exchange error {}, error: {}".format(ticker_pair, e)) 
            return None

    def fetch_order(self, orderId):
        try:
            if (not self.exchange.has['fetchOrder']):
                print("WARNING: exhange does not support fetchOrder")
                return None

            order = self.exchange.fetch_order(orderId)
            return order

        except RequestTimeout as e:
            logger.warn("fetch_order request timed out for {}, error: {}".format(orderId, e))
            return None
        except AuthenticationError as e:
            logger.warn("fetch_order authentication error for {}, error: {}".format(orderId, e))
            return None
        except NetworkError as e:
            logger.warn("fetch_order network error {}, error: {}".format(orderId, e)) 
            return None