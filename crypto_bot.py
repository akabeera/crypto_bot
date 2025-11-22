import json
import os
import time
import pandas as pd
import utils.constants as CONSTANTS
from decimal import *
from dotenv import load_dotenv

from strategies.base_strategy import BaseStrategy
from utils.trading import TradeAction, TakeProfitEvaluationType, find_profitable_trades, calculate_avg_position, round_down
from utils.mongodb_service import MongoDBService
from utils.exchange_service import ExchangeService
# from utils.strategies import execute_strategies, init_strategies, init_strategies_overrides
from utils.strategies_enhanced import execute_strategies, init_strategies, init_strategies_overrides

from utils.logger import logger

load_dotenv()

CONFIG_FILE = 'config_enhanced.json'

class CryptoBot:

    def __init__(self, db_connection_string):
        with open(CONFIG_FILE) as f:
            self.config = json.load(f)
        
        self.ticker_trades_cooldown_periods = {}

        self.max_spend = Decimal(self.config[CONSTANTS.CONFIG_MAX_SPEND])
        self.amount_per_transaction = Decimal(self.config[CONSTANTS.CONFIG_AMOUNT_PER_TRANSACTION])

        if CONSTANTS.CONFIG_DB not in self.config:
            logger.error(f"missing db config, aborting")
            exit(1)

        self.reinvestment_percent = CONSTANTS.CONFIG_DEFAULT_REINVESTMENT_PERCENT
        if CONSTANTS.CONFIG_REINVESTMENT_PERCENT in self.config:
            self.reinvestment_percent = Decimal(self.config[CONSTANTS.CONFIG_REINVESTMENT_PERCENT]/100)

        self.remaining_balance = self.max_spend
        self.trade_cooldown_period = 10
        if CONSTANTS.CONFIG_TRADE_COOLDOWN_PERIOD in self.config:
            self.trade_cooldown_period = self.config[CONSTANTS.CONFIG_TRADE_COOLDOWN_PERIOD]

        self.currency: str = CONSTANTS.CONFIG_DEFAULT_CURRENCY
        if CONSTANTS.CONFIG_CURRENCY in self.config:
            self.currency =self.config[CONSTANTS.CONFIG_CURRENCY]

        self.sleep_interval = CONSTANTS.CONFIG_DEFAULT_SLEEP_INTERVAL
        if CONSTANTS.CONFIG_DEFAULT_SLEEP_INTERVAL in self.config:
            self.sleep_interval = self.config[CONSTANTS.CONFIG_SLEEP_INTERVAL]

        self.crypto_currency_sleep_interval = CONSTANTS.CONFIG_DEFAULT_CRYPTO_CURRENCY_SLEEP_INTERVAL
        if CONSTANTS.CONFIG_CRYPTO_CURRENCY_SLEEP_INTERVAL in self.config:
            self.crypto_currency_sleep_interval = self.config[CONSTANTS.CONFIG_CRYPTO_CURRENCY_SLEEP_INTERVAL]

        self.crypto_whitelist = self.config[CONSTANTS.CONFIG_SUPPORTED_CRYPTO_CURRENCIES]
        self.crypto_blacklist = []
        if CONSTANTS.CONFIG_BLACKLISTED_CRYPTO_CURRENCIES in self.config:
            self.crypto_blacklist = self.config[CONSTANTS.CONFIG_BLACKLISTED_CRYPTO_CURRENCIES]

        self.supported_crypto_list = list(set(self.crypto_whitelist).difference(self.crypto_blacklist))

        self.dry_run = False
        if CONSTANTS.CONFIG_DRY_RUN in self.config:
            self.dry_run = self.config[CONSTANTS.CONFIG_DRY_RUN]

        #TODO: Abstract mongodb service into a data_service
        db_config = self.config[CONSTANTS.CONFIG_DB]
        db_type = db_config[CONSTANTS.CONFIG_DB_TYPE] 
        self.mongodb_db_name = db_config[CONSTANTS.CONFIG_DB_NAME]
        self.current_positions_collection = db_config[CONSTANTS.CONFIG_DB_CURRENT_POSITIONS_COLLECTION]
        self.closed_positions_collection = db_config[CONSTANTS.CONFIG_DB_CLOSED_POSITIONS_COLLECTION]
        self.mongodb_service = MongoDBService(db_connection_string, self.mongodb_db_name)

        exchange_config = self.config[CONSTANTS.CONFIG_EXCHANGE]
        self.exchange_service = ExchangeService(exchange_config, self.dry_run)

        self.init()

    def init(self):
        (self.take_profit_threshold, self.take_profit_evaluation_type) = self.init_take_profits_config(self.config[CONSTANTS.CONFIG_TAKE_PROFITS])

        self.strategies: dict[str, BaseStrategy] = init_strategies(self.config, self.mongodb_service)
        self.init_overrides()

    def init_take_profits_config(self, take_profits_config):

        take_profit_threshold = CONSTANTS.DEFAULT_TAKE_PROFIT_THRESHOLD
        take_profit_evaluation_type = CONSTANTS.DEFAULT_TAKE_PROFIT_EVALUATION_TYPE

        if take_profits_config is not None:
            if CONSTANTS.CONFIG_TAKE_PROFITS_THRESHOLD_PERCENT in take_profits_config:
                take_profit_threshold = take_profits_config[CONSTANTS.CONFIG_TAKE_PROFITS_THRESHOLD_PERCENT]

            if CONSTANTS.CONFIG_TAKE_PROFITS_EVALUATION_TYPE in take_profits_config:
                take_profit_evaluation_type = take_profits_config[CONSTANTS.CONFIG_TAKE_PROFITS_EVALUATION_TYPE]

        take_profit_threshold = Decimal(take_profit_threshold/100)
        take_profit_evaluation_type = TakeProfitEvaluationType[take_profit_evaluation_type]

        return (take_profit_threshold, take_profit_evaluation_type)

    def init_overrides(self):
        if CONSTANTS.CONFIG_OVERRIDES not in self.config:
            return
        
        self.strategies_overrides: dict[str, dict[str, BaseStrategy]] = init_strategies_overrides(self.config, self.mongodb_service)
        self.overrides: dict[str, dict[str, any]] = dict()

        overrides_config = self.config[CONSTANTS.CONFIG_OVERRIDES]
        overrideable_attributes = set(CONSTANTS.CONFIG_OVERRIDEABLE_ATTRIBUTES)

        for oc in overrides_config:
            tickers = oc[CONSTANTS.CONFIG_TICKERS]

            attributes = oc.keys()
            
            for ticker in tickers:
                if ticker not in self.overrides:
                    self.overrides[ticker] = dict()

                for attribute in attributes:
                    if attribute not in overrideable_attributes:
                        continue
                    
                    self.overrides[ticker][attribute] = oc[attribute]
                    logger.info(f"{ticker}: setting override for {attribute}: {oc[attribute]}")
                        
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
            ohlcv = self.exchange_service.execute_op(ticker_pair=ticker_pair, op=CONSTANTS.OP_FETCH_OHLCV, params={"timeframe": '15m'})
            if ohlcv == None or len(ohlcv) == 0:
                logger.error(f"{ticker_pair}: unable to fetch ohlcv, skipping")
                continue

            if len(ohlcv) < 4:
                logger.warning(f"{ticker_pair}: not enough candles, candles len: {len(ohlcv)}, skipping")
                continue

            candles_df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])

            take_profit_threshold = self.take_profit_threshold
            take_profit_evaluation_type = self.take_profit_evaluation_type

            if ticker_pair in self.overrides and CONSTANTS.CONFIG_TAKE_PROFITS in self.overrides[ticker_pair]:
                (take_profit_threshold, take_profit_evaluation_type) = self.init_take_profits_config(self.overrides[ticker_pair][CONSTANTS.CONFIG_TAKE_PROFITS])

            ticker_filter = {
                'symbol': ticker_pair
            }
            all_positions = self.mongodb_service.query(self.current_positions_collection, ticker_filter)
            avg_position = calculate_avg_position(all_positions) 

            ticker_info = self.exchange_service.execute_op(ticker_pair=ticker_pair, op=CONSTANTS.OP_FETCH_TICKER)
            if ticker_info is None:
                logger.error(f"{ticker_pair}: error fetching ticker_info, skipping")
                continue
            
            profitable_positions_to_exit = find_profitable_trades(ticker_pair, 
                                                                  avg_position, 
                                                                  all_positions, 
                                                                  ticker_info, 
                                                                  take_profit_threshold, 
                                                                  take_profit_evaluation_type)
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
            
            if trade_action == TradeAction.BUY:
                logger.info(f"{ticker_pair}: BUY signal triggered")
                self.handle_buy_order(ticker_pair, ticker_info)    
            elif trade_action == TradeAction.SELL:
                logger.info(f'{ticker_pair}: SELL signal triggered but skipping selling until profit thresholds are met.')

                # logger.info(f'{ticker_pair}: SELL signal triggered, number of lots being sold: {len(all_positions)}')
                # self.handle_sell_order(ticker_pair, ticker_info, all_positions)
      
            time.sleep(self.crypto_currency_sleep_interval)
        
    def handle_buy_order(self, ticker_pair: str, ticker_info = None):        
        if self.ticker_in_cooldown(ticker_pair):
            logger.warn(f"{ticker_pair} is in cooldown, skipping buy")
            return None
        
        amount = self.amount_per_transaction
        if ticker_pair in self.overrides:
            if CONSTANTS.CONFIG_AMOUNT_PER_TRANSACTION in self.overrides[ticker_pair]:
                amount = Decimal(self.overrides[ticker_pair][CONSTANTS.CONFIG_AMOUNT_PER_TRANSACTION])

        if self.remaining_balance < amount:
            logger.warn(f"{ticker_pair}: insufficient balance to place buy order, skipping")
            return None
        
        params = None
        if ticker_info is None:
            return None
        
        if "ask" in ticker_info:

            ask_price = Decimal(ticker_info["ask"])
            shares = float(amount / ask_price)
            rounded_shares = round_down(shares)
            
            params = {
                CONSTANTS.PARAM_ORDER_TYPE: "buy",
                CONSTANTS.PARAM_MARKET_ORDER_TYPE: 'limit',
                CONSTANTS.PARAM_SHARES: rounded_shares,
                CONSTANTS.PARAM_PRICE: ask_price   
            }

        else:

            params = {
                CONSTANTS.PARAM_TOTAL_COST: amount,
                CONSTANTS.PARAM_ORDER_TYPE: 'buy',
                CONSTANTS.PARAM_MARKET_ORDER_TYPE: 'market'
            }
        
        order = self.exchange_service.execute_op(ticker_pair=ticker_pair, op=CONSTANTS.OP_CREATE_ORDER, params=params)
        if not order:
            logger.error(f"{ticker_pair}: FAILED to execute buy order")
            return None
        
        self.remaining_balance -= amount
        self.mongodb_service.insert_one(self.current_positions_collection, order)
        self.start_cooldown(ticker_pair)
        logger.info(f"{ticker_pair}: BUY executed. price: {order['price']}, shares: {order['filled']}, fees: {order['fee']['cost']}, remaining balance: {self.remaining_balance}")

        return order

    def handle_sell_order(self, ticker_pair: str, ticker_info, positions_to_exit):
        if "bid" not in ticker_info:
            logger.error(f"{ticker_info}: missing bid price in ticker_info, aborting handle_sell_order")
            return None
        
        bid_price = ticker_info["bid"]
                    
        shares: float = 0.0
        positions_to_delete = []
        for position in positions_to_exit:
            shares += position["filled"]
            positions_to_delete.append(position["id"])

        rounded_shares = round_down(shares)

        params = {
            CONSTANTS.PARAM_ORDER_TYPE: "sell",
            CONSTANTS.PARAM_MARKET_ORDER_TYPE: 'limit',
            CONSTANTS.PARAM_SHARES: rounded_shares,
            CONSTANTS.PARAM_PRICE: bid_price    
        }

        order = self.exchange_service.execute_op(ticker_pair=ticker_pair, op=CONSTANTS.OP_CREATE_ORDER, params=params)
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
        if deletion_count != len(positions_to_exit):
            logger.warn(f"{ticker_pair}: mismatch of deleted positions, deletion count: {deletion_count}, positions exited:{len(positions_to_exit)}")

        to_reinvest_percent = self.reinvestment_percent
        if ticker_pair in self.overrides:
            if CONSTANTS.CONFIG_REINVESTMENT_PERCENT in self.overrides[ticker_pair]:
                to_reinvest_percent = Decimal(self.overrides[ticker_pair][CONSTANTS.CONFIG_REINVESTMENT_PERCENT])

        proceeds = Decimal(order['info']['total_value_after_fees'])
        if to_reinvest_percent > CONSTANTS.ZERO:
            self.remaining_balance += (proceeds * to_reinvest_percent)

        logger.info(f"{ticker_pair}: SELL EXECUTED. price: {order['average']}, shares: {order['filled']}, proceeds: {proceeds}, remaining_balance: {self.remaining_balance}")
        return closed_position

    def start_cooldown(self, ticker_pair):
        self.ticker_trades_cooldown_periods[ticker_pair] = time.time()

    def ticker_in_cooldown(self, ticker_pair):
        if ticker_pair not in self.ticker_trades_cooldown_periods:
            return False
        
        last_trade_timestamp = self.ticker_trades_cooldown_periods[ticker_pair]
        elapse_time_minutes = self.get_elapse_time_mins(last_trade_timestamp)

        trade_cooldown_period = self.trade_cooldown_period
        if ticker_pair in self.overrides and CONSTANTS.CONFIG_TRADE_COOLDOWN_PERIOD in self.overrides[ticker_pair]:
            trade_cooldown_period = self.overrides[ticker_pair][CONSTANTS.CONFIG_TRADE_COOLDOWN_PERIOD]

        if elapse_time_minutes < trade_cooldown_period:
            logger.info(f"{ticker_pair}: currently in cooldown, elapse {elapse_time_minutes} of {trade_cooldown_period} minutes so far")
            return True
        
        return False

    def handle_cooldown(self, ticker_pair):
        if ticker_pair not in self.ticker_trades_cooldown_periods:
            return 
        
        last_trade_timestamp = self.ticker_trades_cooldown_periods[ticker_pair]
        elapse_time_minutes = self.get_elapse_time_mins(last_trade_timestamp)
        
        if elapse_time_minutes >= self.trade_cooldown_period:
            logger.info(f"{ticker_pair}: resetting cooldown")
            del self.ticker_trades_cooldown_periods[ticker_pair]

    def get_elapse_time_mins(self, timestamp):
        current_time = time.time()
        elapsed_time = current_time - timestamp
        elapse_time_minutes = elapsed_time/60

        return elapse_time_minutes