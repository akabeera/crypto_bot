import os
import ccxt
from decimal import *
from dotenv import load_dotenv

from crypto_bot import CryptoBot
from utils.logger import logger

load_dotenv()

if __name__ == "__main__":

    MONGO_CONNECTION_STRING = os.getenv("MONGO_CONNECTION_STRING")
    if MONGO_CONNECTION_STRING is None:
        logger.error("MongoDB connection string is not defined.  Aborting!")
        exit()
    
    crypto_bot =  CryptoBot(MONGO_CONNECTION_STRING)
    crypto_bot.run()