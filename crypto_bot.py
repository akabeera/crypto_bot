import json
import os
import time
import pandas as pd
from decimal import *
from dotenv import load_dotenv

from strategies.strategy_factory import strategy_factory
from strategies.utils import calculate_profit_percent, calculate_avg_position
from utils.trading import TradeAction
from utils.mongodb_service import MongoDBService
from utils.exchange_service import ExchangeService
from utils.constants import ZERO
from utils.logger import logger

load_dotenv()

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

        exchange_config = self.config["exchange"]
        self.exchange_service = ExchangeService(exchange_config)       

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
            ticker_filter = {
                'symbol': ticker_pair
            }
            trades = self.mongodb_service.query(self.current_positions_collection, ticker_filter)
            avg_position = calculate_avg_position(trades)       


            if ticker in self.crypto_blacklist and avg_position is None:
                continue     

            ohlcv = self.exchange_service.execute_op(ticker_pair=ticker_pair, op="fetchOHLCV")
            if ohlcv == None or len(ohlcv) == 0:
                logger.error(f"{ticker_pair}: unable to fetch ohlcv, skipping")
                continue

            candles_df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])

            r, c = candles_df.shape
            if r < 4:
                logger.warn(f"{ticker_pair}: not enough candles({r}), skipping")
                continue

            ticker_info = self.exchange_service.execute_op(ticker_pair=ticker_pair, op="fetchTicker")
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

                if action == TradeAction.BUY and ticker not in self.crypto_blacklist:
                    logger.info(f"{ticker_pair}: executing BUY @ ask price: ${ask_price}")
                    self.handle_buy_order(ticker_pair)
                    break
                elif action == TradeAction.SELL:
                    logger.info(f'{ticker_pair}: executing SELL @ bid price: ${bid_price}, shares:{avg_position["amount"]}')
                    self.handle_sell_order(ticker_pair, float(avg_position["amount"]), float(bid_price))
                    break
            
            expected_profit = calculate_profit_percent(avg_position, ticker_info)
            time.sleep(self.inter_currency_sleep_interval)
    
    def handle_buy_order(self, ticker_pair: str):
        if self.remaining_balance < self.amount_per_transaction:
            logger.warn(f"{ticker_pair}: insufficient balance to place buy order, skipping")
            return
        
        #order = self.create_buy_order(ticker_pair, self.amount_per_transaction)
        order = self.exchange_service.execute_op(ticker_pair=ticker_pair, op="createOrder", total_cost=self.amount_per_transaction, order_type="buy")
        if not order:
            logger.error(f"{ticker_pair}: FAILED to execute buy order")
            return
        self.remaining_balance -= self.amount_per_transaction

        self.mongodb_service.insert_one(self.current_positions_collection, order)
        logger.info(f"{ticker_pair}: BUY executed. price: {order['price']}, shares: {order['filled']}, fees: {order['fee']['cost']}, remaining balance: {self.remaining_balance}")


    def handle_sell_order(self, ticker_pair: str, shares: float, bid_price: float):
        #order = self.create_sell_limit_order(ticker_pair, shares, bid_price)
        order = self.exchange_service.execute_op(ticker_pair=ticker_pair, op="createOrder", shares=shares, price=bid_price, order_type="sell")

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