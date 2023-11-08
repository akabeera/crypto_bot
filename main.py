import os
import ccxt
from decimal import *
from dotenv import load_dotenv

from crypto_bot import CryptoBot
from utils.logger import logger

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