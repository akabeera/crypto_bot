import ccxt
import os
import time
from dotenv import load_dotenv
from decimal import *
from ccxt import BadSymbol, RequestTimeout, AuthenticationError, NetworkError, ExchangeError
from utils.logger import logger
import utils.constants as CONSTANTS

load_dotenv()
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')

class ExchangeService:
    _exchange = None

    @classmethod
    def _get_exchange(cls, exchange_config):

        if cls._exchange is None:
            exchange_id = "coinbase"
            if CONSTANTS.CONFIG_EXCHANGE_ID in exchange_config:
                exchange_id = exchange_config[CONSTANTS.CONFIG_EXCHANGE_ID]
            
            create_market_buy_order_requires_price = False
            if CONSTANTS.CONFIG_CREATE_MARKET_BUY_ORDER_REQUIRES_PRICE in exchange_config:
                create_market_buy_order_requires_price = exchange_config[CONSTANTS.CONFIG_CREATE_MARKET_BUY_ORDER_REQUIRES_PRICE]

            exchange_class = getattr(ccxt, exchange_id)
            cls._exchange = exchange_class({
                'apiKey': API_KEY,
                'secret': API_SECRET
            })

            cls._exchange.options["createMarketBuyOrderRequiresPrice"] = create_market_buy_order_requires_price    
            return cls._exchange
    
    def __init__(self, exchange_config, dry_run=False):
        self.exchange_client = self._get_exchange(exchange_config)
        self.dry_run = dry_run
        self.limit_order_num_periods_limit = CONSTANTS.CONFIG_DEFAULT_LIMIT_ORDER_NUM_PERIODS_LIMIT
        if CONSTANTS.CONFIG_LIMIT_ORDER_NUM_PERIODS_LIMIT in exchange_config:
            self.limit_order_num_periods_limit = exchange_config[CONSTANTS.CONFIG_LIMIT_ORDER_NUM_PERIODS_LIMIT]

        self.limit_order_period_time_limit = CONSTANTS.CONFIG_DEFAULT_LIMIT_ORDER_PERIOD_TIME_LIMIT
        if CONSTANTS.CONFIG_LIMIT_ORDER_PERIOD_TIME_LIMIT in exchange_config:
            self.limit_order_period_time_limit = exchange_config[CONSTANTS.CONFIG_LIMIT_ORDER_PERIOD_TIME_LIMIT]

    def execute_op(self, ticker_pair: str, op: str, params = {}):
        try:
            if not self.exchange_client.has[op]:
                logger.warn(f"{ticker_pair}: exchange does not support op: {op}")
                return None
                        
            if op == CONSTANTS.OP_FETCH_TICKER:
                ticker_info = self.exchange_client.fetch_ticker(ticker_pair)
                if ticker_info is None or "bid" not in ticker_info or ticker_info["bid"] is None:
                    logger.warn(f"{ticker_pair}: bid info missing from tickerInfo")
                    return None
                return ticker_info
            
            elif op == CONSTANTS.OP_FETCH_OHLCV:
                timeframe = "1m"
                if CONSTANTS.PARAM_TIMEFRAME in params:
                    timeframe = params[CONSTANTS.PARAM_TIMEFRAME]
                if CONSTANTS.PARAM_SINCE in params:
                    since = params[CONSTANTS.PARAM_SINCE]
                return self.exchange_client.fetch_ohlcv(ticker_pair)
            elif op == CONSTANTS.OP_FETCH_ORDER: 
                if CONSTANTS.PARAM_ORDER_ID not in params or params[CONSTANTS.PARAM_ORDER_ID] is None:
                    logger.error(f"{ticker_pair}: missing or invalid 'order_id' param is fetchOrder")
                    return None
                order_id = params[CONSTANTS.PARAM_ORDER_ID]
                order = self.exchange_client.fetch_order(order_id)
                return order
            elif op == CONSTANTS.OP_FETCH_ORDERS:
                return self.exchange_client.fetch_orders(ticker_pair, CONSTANTS.AUG_FIRST_TIMESTAMP_MS, CONSTANTS.NUM_ORDERS_LIMIT)
            elif op == CONSTANTS.OP_CANCEL_ORDER:
                 if CONSTANTS.PARAM_ORDER_ID not in params or params[CONSTANTS.PARAM_ORDER_ID] is None:
                    logger.error(f"{ticker_pair}: missing or invalid 'order_id' param is cancelOrder")
                    return None
                 order_id = params[CONSTANTS.PARAM_ORDER_ID]
                 return self.exchange_client.cancel_order(order_id, ticker_pair)
            elif op == CONSTANTS.OP_CREATE_ORDER:

                if CONSTANTS.PARAM_ORDER_TYPE not in params:
                    logger.error(f"{ticker_pair}: missing 'order_type' param")
                    return None
                order_type = params[CONSTANTS.PARAM_ORDER_TYPE]

                market_order_type = "market"
                if CONSTANTS.PARAM_MARKET_ORDER_TYPE in params:
                    market_order_type = params[CONSTANTS.PARAM_MARKET_ORDER_TYPE]

                if market_order_type == "market":
                    if order_type == "buy":
                        if CONSTANTS.PARAM_TOTAL_COST not in params or params[CONSTANTS.PARAM_TOTAL_COST] is None:
                            logger.error(f"{ticker_pair}: missing or invalid 'total_cost' param for buy order")
                            return None
                        total_cost = params[CONSTANTS.PARAM_TOTAL_COST]
                        return self.create_market_buy_order(ticker_pair, total_cost)
                    if order_type == "sell":
                        if CONSTANTS.PARAM_SHARES not in params or params[CONSTANTS.PARAM_SHARES] is None:
                            logger.error(f"{ticker_pair}: missing or invalid 'shares' param for sell order")
                            return None
                        shares = params[CONSTANTS.PARAM_SHARES]
                        return self.create_market_sell_order(ticker_pair, shares)
                elif market_order_type == "limit":

                    if CONSTANTS.PARAM_PRICE not in params or params[CONSTANTS.PARAM_PRICE] is None or CONSTANTS.PARAM_SHARES not in params or params[CONSTANTS.PARAM_SHARES] is None:
                        logger.error(f"{ticker_pair}: invalid params for limit order, params: {params}")
                        return None

                    price = params[CONSTANTS.PARAM_PRICE]
                    shares = params[CONSTANTS.PARAM_SHARES]

                    return self.create_order(ticker_pair, shares, market_order_type, order_type, price)
                else:
                    logger.error(f"{ticker_pair}: invalid market_order_type:{market_order_type}")
                    return None
            elif op == CONSTANTS.OP_FETCH_MY_TRADES:
                return self.exchange_client.fetch_my_trades(ticker_pair, CONSTANTS.AUG_FIRST_TIMESTAMP_MS, 1000)
            elif op == CONSTANTS.OP_FETCH_TRANSACTIONS:
                return self.exchange_client.fetch_transactions(ticker_pair, CONSTANTS.AUG_FIRST_TIMESTAMP_MS, 1000)
            else:
                logger.error(f"{ticker_pair}: unsupported exchange operation: {op}")
                return None
            
        except BadSymbol as e:
            logger.error(f"{ticker_pair}: {op} BadSymbol error: {e}")
            return None
        except RequestTimeout as e:
            logger.error(f"{ticker_pair}: {op} request timed out error: {e}")
            return None
        except AuthenticationError as e:
            logger.error(f"{ticker_pair}: {op} authentication error: {e}")
            return None
        except NetworkError as e:
            logger.error(f"{ticker_pair}: {op} network error: {e}") 
            return None
        except IndexError as e:
            logger.error(f"{ticker_pair}: {op} index error: {e}")
            return None
        except ExchangeError as e:
            logger.error(f"{ticker_pair}: {op} exchange error: {e}")
            return None
        
    def create_order(self, ticker_pair: str, shares: float, type: str, side: str, price: float = None):
        if self.dry_run:
            logger.info(f"{ticker_pair}: dry_run enaled, skiping create_order")
            return None
        
        order_results = self.exchange_client.create_order(ticker_pair, type, side, shares, price)
        order_id = order_results['info']['order_id']
        params = {
            "order_id": order_id
        }

        order = None
        status = order_results['status']
        idx = 0
        filled = CONSTANTS.ZERO
        while (status != 'closed'):
            prev_filled = filled
            
            if idx == self.limit_order_num_periods_limit:

                if order is not None:
                    filled = Decimal(str(order["filled"]))

                if filled == CONSTANTS.ZERO:
                    logger.warn(f"{ticker_pair}: limit order not fulfilled, cancelling order")
                    self.execute_op(ticker_pair=ticker_pair, op=CONSTANTS.OP_CANCEL_ORDER, params=params)

                idx = 0
                
                # if filled > prev_filled:
                #     logger.info(f"{ticker_pair}: order is still being filled, extending time")
                #     idx = 0
                #     continue

                # logger.warn(f"{ticker_pair}: limit order not fulfilled within time limit, cancelling order")
                # self.execute_op(ticker_pair=ticker_pair, op=CONSTANTS.OP_CANCEL_ORDER, params=params)
                # logger.warn(f"{ticker_pair}: cancelled_order, last order status: {order}")
                
                return None

            logger.info(f"{ticker_pair}: waiting for limit_order to be fulfilled, time: {idx}")

            time.sleep(self.limit_order_period_time_limit)
            order = self.execute_op(ticker_pair=ticker_pair, op=CONSTANTS.OP_FETCH_ORDER, params=params)
            if (order == None):
                return None
            
            idx += 1
            status = order['status']

        return order
    
    def create_market_buy_order(self, ticker_pair: str, amount: float):
        if self.dry_run:
            logger.info(f"{ticker_pair}: dry_run enaled, skiping create_market_buy_order")
            return None
        
        order_results = self.exchange_client.create_market_buy_order(ticker_pair, amount)
        order_id = order_results['info']['order_id']

        params = {
            "order_id": order_id
        }

        order = None
        status = order_results['status']
        while (status != 'closed'):
            time.sleep(1)
            order = self.execute_op(ticker_pair=ticker_pair, op=CONSTANTS.OP_FETCH_ORDER, params=params)
            if (order == None):
                return None

            status = order['status']

        return order

    def create_market_sell_order(self, ticker_pair, shares: float):
        if self.dry_run:
            logger.info(f"{ticker_pair}: dry_run enaled, skiping create_market_sell_order")
            return None

        order_results = self.exchange.create_market_sell_order(ticker_pair, shares)
        order_id = order_results['info']['order_id']

        params = {
            "order_id": order_id
        }

        order = None
        status = order_results['status']
        while (status != 'closed'):
            time.sleep(1)
            order = self.execute_op(ticker_pair=ticker_pair, op=CONSTANTS.OP_FETCH_ORDER, params=params)
            if (order == None):
                return None

            status = order['status']

        return order