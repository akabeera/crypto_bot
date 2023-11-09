import talib
from decimal import *

from .base_strategy import BaseStrategy
from utils.logger import logger
from utils.trading import TradeAction

class RSI(BaseStrategy):
    def __init__(self, config):
        self.priority = config["priority"]
        self.prevent_loss = True
        if "prevent_loss" in config:
            self.prevent_loss = config["prevent_loss"]

        parameters = config["parameters"]
        self.overbought_signal_threshold = parameters["overbought_signal_threshold"]
        self.oversold_signal_threshold = parameters["oversold_signal_threshold"]

        super().__init__(config)


    def eval(self, avg_position, candles_df, ticker_info):
        rsi_key = "RSI"
        candles_df[rsi_key] = talib.RSI(candles_df['close'])

        last_row = candles_df.iloc[-1]
        rsi = last_row[rsi_key]

        action = TradeAction.NOOP
        if rsi > 70:
            logger.info(f'{ticker_info["symbol"]}: {self.name} triggered SELL signal')
            action = TradeAction.SELL
        elif rsi < 32:
            logger.info(f'{ticker_info["symbol"]}: {self.name} triggered BUY signal')
            action = TradeAction.BUY

        if self.prevent_loss and action == TradeAction.SELL:
            action = self.prevent_loss_eval(avg_position, ticker_info, action)
        
        return action


