import ccxt
import os
import json
import time
from dotenv import load_dotenv
from ccxt import BadSymbol, RequestTimeout, AuthenticationError, NetworkError, ExchangeError

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

API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')

class ExchangeService:
    _exchange = None

    @classmethod
    def _get_exchange(cls, exchange_config):
        if cls._exchange is None:
            exchange_id = exchange_config["exchange_id"]

            create_market_buy_order_requires_price = False
            if "create_market_buy_order_requires_price" in exchange_config:
                create_market_buy_order_requires_price = exchange_config["create_market_buy_order_requires_price"]

            exchange_class = getattr(ccxt, exchange_id)
            cls._exchange = exchange_class({
                'apiKey': API_KEY,
                'secret': API_SECRET
            })

            cls._exchange.options["createMarketBuyOrderRequiresPrice"] = create_market_buy_order_requires_price    
            return cls._exchange
    
    def __init__(self, exchange_config):
        self.exchange_client = self._get_exchange(exchange_config)

        self.market_order_type_buy = "market"
        if "market_order_type_buy" in exchange_config:
            self.market_order_type_buy = exchange_config["market_order_type_buy"]

        self.market_order_type_sell = "market"
        if "market_order_type_sell" in exchange_config:
            self.market_order_type_sell = exchange_config["market_order_type_sell"]

        self.limit_order_time_limit = 10
        if "limit_order_time_limit" in exchange_config:
            self.limit_order_time_limit = exchange_config["limit_order_time_limit"]


    def execute_op(self, ticker_pair: str, op: str, shares: float = None, price: float = None, order_type:str = None, order_id: str = None):
        try:
            if not self.exchange_client.has[op]:
                logger.warn(f"{ticker_pair}: exchange does not support op:{op}")
                return None
                        
            if op == "fetchTicker":
                return self.exchange_client.fetch_ticker(ticker_pair)
            elif op == "fetchOHLCV":
                return self.exchange_client.fetch_ohlcv(ticker_pair)
            elif op == "fetchOrder":
                order = self.exchange_client.fetch_order(order_id)
                return order
            elif op == "createOrder":
                if (self.market_order_type_buy == "limit" or self.market_order_type_sell == "limit") and price is None:
                    logger.error(f"{ticker_pair}: unable to execute a limit order with an empty price, aborting")
                    return None
                
                market_order_type = self.market_order_type_buy if order_type == "buy" else self.market_order_type_sell
                return self.create_order(ticker_pair, shares, market_order_type, order_type, price)
            elif op == "cancelOrder":
                 self.exchange_client.cancel_order(order_id, ticker_pair)
                 return None
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

        order_results = self.exchange_client.create_order(ticker_pair, type, side, shares, price)
        order_id = order_results['info']['order_id']

        order = None
        status = order_results['status']
        idx = 0
        while (status != 'closed'):
            
            if idx == self.limit_order_time_limit:
                logger.warn(f"{ticker_pair}: limit order not fulfilled within time limit, cancelling order")
                self.execute_op(ticker_pair=ticker_pair, op="cancelOrder", order_id=order_id)
                logger.warn(f"{ticker_pair}: cancelled_order")
                return None

            logger.info(f"{ticker_pair}: waiting for limit_order to be fulfilled, time: {idx}")

            time.sleep(1)
            order = self.execute_op(ticker_pair=ticker_pair, op="fetchOrder", order_id=order_id)
            if (order == None):
                return None
            
            idx += 1
            status = order['status']

        return order

            