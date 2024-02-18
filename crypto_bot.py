import json
import os
import time
import pandas as pd
from decimal import *
from dotenv import load_dotenv

from strategies.base_strategy import BaseStrategy
from strategies.strategy_factory import strategy_factory
from utils.trading import TradeAction, TakeProfitEvaluationType, find_profitable_trades, calculate_profit_percent, calculate_avg_position, round_down
from utils.mongodb_service import MongoDBService
from utils.exchange_service import ExchangeService
from utils.constants import ZERO, DEFAULT_TAKE_PROFIT_THRESHOLD, DEFAULT_TAKE_PROFIT_EVALUATION_TYPE
from utils.strategies import execute_strategies, init_strategies, init_strategies_overrides
from utils.logger import logger

load_dotenv()

CONFIG_FILE = 'config.json'
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')

class CryptoBot:

    def __init__(self, db_connection_string):
        with open(CONFIG_FILE) as f:
            self.config = json.load(f)
        
        self.ticker_cooldown_periods = {}

        self.max_spend = Decimal(self.config["max_spend"])
        self.amount_per_transaction = Decimal(self.config["amount_per_transaction"])
        self.reinvestment_percent = Decimal(self.config["reinvestment_percent"]/100)
        self.remaining_balance = self.max_spend
        self.limit_order_time_limit = 10
        self.cooldown_num_periods = 10
        if "cooldown_num_periods" in self.config:
            self.cooldown_num_periods = self.config["cooldown_num_periods"]

        self.currency: str = self.config["currency"]
        self.sleep_interval = self.config["sleep_interval"]
        self.inter_currency_sleep_interval = self.config["inter_currency_sleep_interval"]

        self.crypto_whitelist = self.config["support_currencies"]
        self.crypto_blacklist = []
        if "blacklisted_currencies" in self.config:
            self.crypto_blacklist = self.config["blacklisted_currencies"]

        self.supported_crypto_list = list(set(self.crypto_whitelist).difference(self.crypto_blacklist))

        mongodb_config = self.config["mongodb"] 
        self.mongodb_db_name = mongodb_config["db_name"]
        self.current_positions_collection = mongodb_config["current_positions_collection"]
        self.closed_positions_collection = mongodb_config["closed_positions_collection"]
        self.mongodb_service = MongoDBService(db_connection_string, self.mongodb_db_name)

        exchange_config = self.config["exchange"]
        self.exchange_service = ExchangeService(exchange_config)

        for ticker in self.supported_crypto_list:
            self.ticker_cooldown_periods[ticker + "/USD"] = []

        take_profit_threshold = DEFAULT_TAKE_PROFIT_THRESHOLD
        take_profit_evaluation_type = DEFAULT_TAKE_PROFIT_EVALUATION_TYPE

        if "take_profits" in self.config:
            take_profits_config = self.config["take_profits"]
            take_profit_threshold = take_profits_config["threshold_percent"]
            take_profit_evaluation_type = take_profits_config["evaluation_type"]

        self.dry_run = False
        if "dry_run" in self.config:
            self.dry_run = self.config["dry_run"]

        self.take_profit_threshold = Decimal(take_profit_threshold/100)
        self.take_profit_evaluation_type = TakeProfitEvaluationType[take_profit_evaluation_type]

        self.init()

    def init(self):
        self.strategies: dict[str, BaseStrategy] = init_strategies(self.config)
        self.strategies_overrides: dict[str, dict[str, BaseStrategy]] = init_strategies_overrides(self.config)
                        
    def run(self):
        idx = 0
        N = len(self.supported_crypto_list)
        logger.info(f"Running for following cryto currencies: ${self.supported_crypto_list}")

        while True:

            if idx == N:
                logger.debug(f"heartbeat!")
                time.sleep(self.sleep_interval)
                idx = 0

            ticker:str = self.supported_crypto_list[idx]
            idx += 1 

            ticker_pair:str = "{}/{}".format(ticker.upper(), self.currency.upper())      
            ohlcv = self.exchange_service.execute_op(ticker_pair=ticker_pair, op="fetchOHLCV")
            if ohlcv == None or len(ohlcv) == 0:
                logger.error(f"{ticker_pair}: unable to fetch ohlcv, skipping")
                continue

            candles_df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])

            r, c = candles_df.shape
            if r < 4:
                logger.warning(f"{ticker_pair}: not enough candles({r}), skipping")
                continue

            ticker_filter = {
                'symbol': ticker_pair
            }
            all_positions = self.mongodb_service.query(self.current_positions_collection, ticker_filter)
            avg_position = calculate_avg_position(all_positions) 

            ticker_info = self.exchange_service.execute_op(ticker_pair=ticker_pair, op="fetchTicker")
            if ticker_info is None:
                logger.error(f"{ticker_pair}: unable to fetch ticker info, skipping")
                continue

            profitable_positions_to_exit = find_profitable_trades(ticker_pair, 
                                                                  avg_position, 
                                                                  all_positions, 
                                                                  ticker_info, 
                                                                  self.take_profit_threshold, 
                                                                  self.take_profit_evaluation_type)
            if profitable_positions_to_exit is not None:
                logger.info(f"{ticker_pair}: number of profitable positions to exit: {len(profitable_positions_to_exit)}")
                self.handle_sell_order(ticker_pair, ticker_info, profitable_positions_to_exit)
                continue

            self.handle_cooldown(ticker_pair)
            trade_action = execute_strategies(ticker_pair, 
                                              self.strategies, 
                                              avg_position, 
                                              ticker_info, 
                                              candles_df, 
                                              self.strategies_overrides)
            
            self.execute_trade_action(ticker_pair, 
                                      trade_action, 
                                      ticker_info, 
                                      all_positions)    
                    
            time.sleep(self.inter_currency_sleep_interval)

    def execute_trade_action(self, 
                             ticker_pair: str, 
                             trade_action: TradeAction, 
                             ticker_info,
                             all_positions):
        
        if trade_action == TradeAction.BUY:
            logger.info(f"{ticker_pair}: BUY signal triggered")
            return self.handle_buy_order(ticker_pair, ticker_info)    
        elif trade_action == TradeAction.SELL:
            logger.info(f'{ticker_pair}: SELL signal triggered, number of lots being sold: {len(all_positions)}')
            return self.handle_sell_order(ticker_pair, ticker_info, all_positions)
        
        return None
        
    def handle_buy_order(self, ticker_pair: str, ticker_info):
        if self.dry_run:
            logger.info(f"{ticker_pair}: dry_run enabled, skipping buy order execution")
            return None
        
        if self.ticker_in_cooldown(ticker_pair):
            logger.warn(f"{ticker_pair} is in cooldown, skipping buy")
            return None

        if self.remaining_balance < self.amount_per_transaction:
            logger.warn(f"{ticker_pair}: insufficient balance to place buy order, skipping")
            return None
        
        order = self.exchange_service.execute_op(ticker_pair=ticker_pair, op="createOrder", total_cost=self.amount_per_transaction, order_type="buy")
        if not order:
            logger.error(f"{ticker_pair}: FAILED to execute buy order")
            return None
        
        self.remaining_balance -= self.amount_per_transaction
        self.mongodb_service.insert_one(self.current_positions_collection, order)
        self.ticker_cooldown_periods[ticker_pair].append(time.time())
        logger.info(f"{ticker_pair}: BUY executed. price: {order['price']}, shares: {order['filled']}, fees: {order['fee']['cost']}, remaining balance: {self.remaining_balance}")

        return order

    def handle_sell_order(self, ticker_pair: str, ticker_info, positions_to_exit):
        if "bid" not in ticker_info:
            logger.error(f"{ticker_info}: missing bid price in ticker_info, aborting handle_sell_order")
            return None
        
        bid_price = ticker_info["bid"]

        if self.dry_run:
            logger.info(f"{ticker_pair}: dry_run enabled, skipping sell order execution")
            return None
                    
        shares: float = 0.0
        positions_to_delete = []
        for position in positions_to_exit:
            shares += position["filled"]
            positions_to_delete.append(position["id"])

        rounded_shares = round_down(shares)

        order = self.exchange_service.execute_op(ticker_pair=ticker_pair, op="createOrder", shares=rounded_shares, price=bid_price, order_type="sell")
        if not order:
            logger.error(f"{ticker_pair}: FAILED to execute sell order")
            return None

        closed_position = {
            'sell_order': order,
            'closed_positions': positions_to_exit
        }
        self.mongodb_service.insert_one(self.closed_positions_collection, closed_position)
        delete_filter = {
            "id": {"$in": positions_to_delete}
        }

        deletion_result = self.mongodb_service.delete_many(self.current_positions_collection, delete_filter)
        deletion_count = deletion_result.deleted_count
        logger.info(f"{ticker_pair}: deletion result from trades table: {deletion_count}")
        if deletion_count != len(positions_to_exit):
            logger.warn(f"{ticker_pair}: mismatch of deleted positions, deletion count: {deletion_count}, positions exited:{len(positions_to_exit)}")

        proceeds = order['info']['total_value_after_fees']
        if self.reinvestment_percent > ZERO:
            self.remaining_balance += (Decimal(proceeds) * self.reinvestment_percent)

        logger.info(f"{ticker_pair}: SELL EXECUTED. price: {order['average']}, shares: {order['filled']}, proceeds: {proceeds}, remaining_balance: {self.remaining_balance}")
        return closed_position

    def ticker_in_cooldown(self, ticker_pair):
        if ticker_pair not in self.ticker_cooldown_periods:
            logger.error(f"{ticker_pair} no entry in cooldown, aborting")
            return False
        
        periods = self.ticker_cooldown_periods[ticker_pair]
        num_periods = len(periods)        
        if num_periods > 0 and num_periods < self.cooldown_num_periods +  1:
            logger.info(f"{ticker_pair}: current cooldown ${len(periods)} of {self.cooldown_num_periods}")
            return True
        
        return False

    def handle_cooldown(self, ticker_pair):
        if ticker_pair not in self.ticker_cooldown_periods:
            return 
        
        periods = self.ticker_cooldown_periods[ticker_pair]
        if len(periods) == 0:
            return
        
        self.ticker_cooldown_periods[ticker_pair].append(time.time())
        if len(periods) > self.cooldown_num_periods + 1:
            logger.info(f"{ticker_pair}: resetting cooldown")
            periods.clear()

 