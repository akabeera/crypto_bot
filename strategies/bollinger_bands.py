from decimal import *

from .base_strategy import BaseStrategy
from utils.logger import logger
from utils.trading import TradeAction

class BollingerBands(BaseStrategy):
    def __init__(self, config):
        self.priority = config["priority"]
        self.prevent_loss = True
        if "prevent_loss" in config:
            self.prevent_loss = config["prevent_loss"]

        parameters = config["parameters"]
        self.window = parameters["window"]
        self.std_dev = parameters["std_dev"]
        
        super().__init__(config)


    def eval(self, avg_position, candles_df, ticker_info):
        middle_band_key = "middle_band"
        upper_band_key = "upper_band"
        lower_band_key = "lower_band"
        close_key = "close"

        candles_df[middle_band_key] = candles_df[close_key].rolling(self.window).mean()
        candles_df[upper_band_key] = candles_df[middle_band_key] + self.std_dev * candles_df[close_key].rolling(self.window).std()
        candles_df[lower_band_key] = candles_df[middle_band_key] - self.std_dev * candles_df[close_key].rolling(self.window).std()

        last_row = candles_df.iloc[-1]
        close = last_row[close_key]
        upper_band = last_row[upper_band_key]
        lower_band = last_row[lower_band_key]

        action = TradeAction.NOOP
        if close > upper_band:
            logger.debug(f'{ticker_info["symbol"]}: {self.name} triggered SELL signal')
            action =  TradeAction.SELL
        elif close < lower_band:
            logger.debug(f'{ticker_info["symbol"]}: {self.name} triggered BUY signal')
            action = TradeAction.BUY

        if self.prevent_loss and action == TradeAction.SELL:
            action = self.prevent_loss_eval(avg_position, ticker_info, action)

        
        return action

