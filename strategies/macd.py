import talib
from decimal import *

from .base_strategy import BaseStrategy
from trading.action import Action

class MACD(BaseStrategy):
    def __init__(self, config):
        self.priority = config["priority"]
        self.prevent_loss = config["prevent_loss"]
        if self.prevent_loss is None:
            self.prevent_loss = True


    def eval(self, avg_position, candles_df, ticker_info):
        macd_key = "MACD"
        macd_signal_key = "MACD_signal"

        candles_df[macd_key], candles_df[macd_signal_key], _ = talib.MACD(candles_df['close'])
        
        last_row = candles_df.iloc[-1]
        macd = last_row[macd_key]
        macd_signal = last_row[macd_signal_key]

        action = Action.NOOP
        if macd_signal < macd:
            action = Action.SELL
        elif macd_signal > macd:
            action = Action.BUY

        if self.prevent_loss and action == Action.SELL:
            action = self.prevent_loss(avg_position, ticker_info, action)
        
        return action


