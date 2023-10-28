import talib
from decimal import *

from .base_strategy import BaseStrategy
from trading.action import Action

class RSI(BaseStrategy):
    def __init__(self, config):
        self.priority = config["priority"]

        parameters = config["parameters"]
        self.overbought_signal_threshold = parameters["overbought_signal_threshold"]
        self.oversold_signal_threshold = parameters["oversold_signal_threshold"]


    def eval(self, avg_position, candles_df, ticker_info):
        rsi_key = "RSI"
        candles_df[rsi_key] = talib.RSI(candles_df['close'])

        last_row = candles_df.iloc[-1]
        rsi = last_row[rsi_key]

        action = Action.NOOP
        if rsi > 70:
            action = Action.SELL
        elif rsi < 32:
            action = Action.BUY

        if self.prevent_loss and action == Action.SELL:
            action = self.prevent_loss(avg_position, ticker_info, action)
        
        return action


