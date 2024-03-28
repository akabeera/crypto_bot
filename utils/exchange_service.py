import ccxt
import os
import time
from dotenv import load_dotenv
from ccxt import BadSymbol, RequestTimeout, AuthenticationError, NetworkError, ExchangeError
from utils.logger import logger
from utils.constants import AUG_FIRST_TIMESTAMP_MS

load_dotenv()
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

        self.limit_order_time_limit = 10
        if "limit_order_time_limit" in exchange_config:
            self.limit_order_time_limit = exchange_config["limit_order_time_limit"]


    def execute_op(self, ticker_pair: str, op: str, params = {}):
        try:
            if not self.exchange_client.has[op]:
                logger.warn(f"{ticker_pair}: exchange does not support op: {op}")
                return None
                        
            if op == "fetchTicker":
                ticker_info = self.exchange_client.fetch_ticker(ticker_pair)
                if ticker_info is None or "bid" not in ticker_info or ticker_info["bid"] is None:
                    logger.warn(f"{ticker_pair}: bid info missing from tickerInfo")
                    return None
                return ticker_info
            
            elif op == "fetchOHLCV":
                timeframe = "1m"
                if "timeframe" in params:
                    timeframe = params["timeframe"]
                if "since" in params:
                    since = params["since"]
                return self.exchange_client.fetch_ohlcv(ticker_pair)
            elif op == "fetchOrder": 
                if "order_id" not in params or params["order_id"] is None:
                    logger.error(f"{ticker_pair}: missing or invalid 'order_id' param is fetchOrder")
                    return None
                order_id = params["order_id"]
                order = self.exchange_client.fetch_order(order_id)
                return order
            elif op == "fetchOrders":
                return self.exchange_client.fetch_orders(ticker_pair, AUG_FIRST_TIMESTAMP_MS, 500)
            elif op == "cancelOrder":
                 if "order_id" not in params or params["order_id"] is None:
                    logger.error(f"{ticker_pair}: missing or invalid 'order_id' param is cancelOrder")
                    return None
                 order_id = params["order_id"]
                 return self.exchange_client.cancel_order(order_id, ticker_pair)
            elif op == "createOrder":

                if "order_type" not in params:
                    logger.error(f"{ticker_pair}: missing 'order_type' param")
                    return None
                
                order_type = params['order_type']

                market_order_type = "market"
                if "market_order_type" in params:
                    market_order_type = params["market_order_type"]

                if market_order_type == "market":
                    if order_type == "buy":
                        if "total_cost" not in params or params["total_cost"] is None:
                            logger.error(f"{ticker_pair}: missing or invalid 'total_cost' param for buy order")
                            return None
                        total_cost = params["total_cost"]
                        return self.create_market_buy_order(ticker_pair, total_cost)
                    if order_type == "sell":
                        if "shares" not in params or params["shares"] is None:
                            logger.error(f"{ticker_pair}: missing or invalid 'shares' param for sell order")
                            return None
                        shares = params["shares"]
                        return self.create_market_sell_order(ticker_pair, shares)
                elif market_order_type == "limit":

                    if "price" not in params or params["price"] is None or "shares" not in params or params["shares"] is None:
                        logger.error(f"{ticker_pair}: invalid params for limit order, params: {params}")
                        return None

                    price = params["price"]
                    shares = params["shares"]

                    return self.create_order(ticker_pair, shares, market_order_type, order_type, price)
                else:
                    logger.error(f"{ticker_pair}: invalid market_order_type:{market_order_type}")
                    return None
            elif op == "fetchMyTrades":
                return self.exchange_client.fetch_my_trades(ticker_pair, AUG_FIRST_TIMESTAMP_MS, 1000)
            elif op == "fetchTransactions":
                return self.exchange_client.fetch_transactions(ticker_pair, AUG_FIRST_TIMESTAMP_MS, 1000)
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
        params = {
            "order_id": order_id
        }

        order = None
        status = order_results['status']
        idx = 0
        filled = 0
        while (status != 'closed'):
            prev_filled = filled
            
            if idx == self.limit_order_time_limit:

                if order is not None:
                    filled = order["filled"]

                if filled > prev_filled:
                    logger.info(f"{ticker_pair}: order is still being filled, extending time")
                    idx = 0
                    continue

                logger.warn(f"{ticker_pair}: limit order not fulfilled within time limit, cancelling order")
                self.execute_op(ticker_pair=ticker_pair, op="cancelOrder", params=params)
                logger.warn(f"{ticker_pair}: cancelled_order, last order status: {order}")

                return None

            logger.info(f"{ticker_pair}: waiting for limit_order to be fulfilled, time: {idx}")

            time.sleep(4)
            order = self.execute_op(ticker_pair=ticker_pair, op="fetchOrder", params=params)
            if (order == None):
                return None
            
            idx += 1
            status = order['status']

        return order
    
    def create_market_buy_order(self, ticker_pair: str, amount: float):

        order_results = self.exchange_client.create_market_buy_order(ticker_pair, amount)
        order_id = order_results['info']['order_id']

        order = None
        status = order_results['status']
        while (status != 'closed'):
            time.sleep(1)
            order = self.execute_op(ticker_pair=ticker_pair, op="fetchOrder", order_id=order_id)
            if (order == None):
                return None

            status = order['status']

        return order

    def create_market_sell_order(self, ticker_pair, shares: float):
        order_results = self.exchange.create_market_sell_order(ticker_pair, shares)
        order_id = order_results['info']['order_id']

        order = None
        status = order_results['status']
        while (status != 'closed'):
            time.sleep(1)
            order = self.execute_op(ticker_pair=ticker_pair, op="fetchOrder", order_id=order_id)
            if (order == None):
                return None

            status = order['status']

        return order