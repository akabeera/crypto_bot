import time
from ccxt import BadSymbol, RequestTimeout, AuthenticationError, NetworkError, ExchangeError

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

def fetch_ticker(exchange, ticker: str):
    try:
        if (exchange.has['fetchTicker']):
            ticker_pair = "{}/USD".format(ticker.upper())
            tickerInfo = exchange.fetch_ticker(ticker_pair)
            return tickerInfo
        else:
            logger.warn('unable to fetch ticker: {ticker}')
            return None
    except BadSymbol as e:
        logger.error("unablet to fetch ticker {}, error: {}".format(ticker, e))
        return None
    except RequestTimeout as e:
        logger.warn("fetch_ticker request timed out for {}, error: {}".format(ticker, e))
        return None
    except AuthenticationError as e:
        logger.warn("WARNING: fetch_ticker authentication error {}, error: {}".format(ticker, e))
        return None
    except NetworkError as e:
        logger.warn("WARNING: fetch_ticker network error {}, error: {}".format(ticker, e)) 
        return None
    except IndexError as e:
        logger.warn("WARNING: fetch_ticker returned IndexError: {}".format(e))
        return None
    except ExchangeError as e:
        logger.warn('WARNING: fetch_ticker exchange error: {}'.format(e))
        return None
        

def fetch_ohlcv(exchange, ticker:str):
    try:
        if (not exchange.has['fetchOHLCV']):
            logger.warn('exchange does not support fetchOHLCV')
            return None
        
        ohlc = exchange.fetch_ohlcv(ticker)
        return ohlc
        
    except BadSymbol as e:
        logger.error("unable to fetch ticker {}, error: {}".format(ticker, e))
        return None
    except RequestTimeout as e:
        logger.warn("fetchOHLCV request timed out for {}, error: {}".format(ticker, e))
        return None
    except AuthenticationError as e:
        logger.warn("fetchOHLCV request timed out for {}, error: {}".format(ticker, e))
        return None
    except NetworkError as e:
        logger.warn("fetchOHLCV network error {}, error: {}".format(ticker, e)) 
        return None
    except ExchangeError as e:
        logger.warn('WARNING: fetch_ticker exchange error: {}'.format(e))
        return None


def create_buy_order(exchange, ticker, amount):
    try:
        order_results = exchange.create_market_buy_order(ticker, amount)
        order_id = order_results['info']['order_id']

        order = None
        status = order_results['status']
        while (status != 'closed'):
            time.sleep(1)
            order = fetch_order(exchange, order_id)
            if (order == None):
                return None
        
            status = order['status']

        return order
    except BadSymbol as e:
        logger.error("unable to submit create_buy_order for ticker {}, error: {}".format(ticker, e))
        return None
    except RequestTimeout as e:
        logger.warn("create_buy_order request timed out for {}, error: {}".format(ticker, e))
        return None
    except AuthenticationError as e:
        logger.warn("create_buy_order request timed out for {}, error: {}".format(ticker, e))
        return None
    except NetworkError as e:
        logger.warn("create_buy_order network error {}, error: {}".format(ticker, e)) 
        return None
    except ExchangeError as e:
        logger.warn("create_buy_order exchange error {}, error: {}".format(ticker, e)) 
        return None


def create_sell_order(exchange, ticker, amount: float, price: float):
    try:
        type = "market"
        side = "sell"
        order_results = exchange.create_order(ticker, type, side, amount, price)
        order_id = order_results['info']['order_id']

        order = None
        status = order_results['status']
        while (status != 'closed'):
            time.sleep(1)
            order = fetch_order(exchange, order_id)
            if (order == None):
                return None
        
            status = order['status']

        return order

    except BadSymbol as e:
        logger.error("unable to submit create_sell_order for ticker {}, error: {}".format(ticker, e))
        return None
    except RequestTimeout as e:
        logger.warn("create_sell_order request timed out for {}, error: {}".format(ticker, e))
        return None
    except AuthenticationError as e:
        logger.warn("create_sell_order request timed out for {}, error: {}".format(ticker, e))
        return None
    except NetworkError as e:
        logger.warn("create_sell_order network error {}, error: {}".format(ticker, e)) 
        return None
    except ExchangeError as e:
        logger.warn("create_sell_order exchange error {}, error: {}".format(ticker, e)) 
        return None

def fetch_order(exchange, orderId):
    try:
        if (not exchange.has['fetchOrder']):
            print("WARNING: exhange does not support fetchOrder")
            return None

        order = exchange.fetch_order(orderId)
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
    







