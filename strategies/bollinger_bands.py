from decimal import *

from .base_strategy import BaseStrategy
from trading.action import Action

class BollingerBands(BaseStrategy):
    def __init__(self, config):
        self.priority = config["priority"]

        parameters = config["parameters"]
        self.window = parameters["window"]
        self.std_dev = parameters["std_dev"]

        self.prevent_loss = parameters["prevent_loss"]
        if self.prevent_loss is None:
            self.prevent_loss = True


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

        action = Action.NOOP
        if close > upper_band:
            action =  Action.SELL
        elif close < lower_band:
            action = Action.BUY

        if self.prevent_loss and action == Action.SELL:
            action = self.prevent_loss(avg_position, ticker_info, action)

        
        return action
