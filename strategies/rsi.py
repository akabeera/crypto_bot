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

        self.normalization_factor = 100000
        if "normalization_factor" in config:
                self.normalization_factor = config["normalization_factor"]

        parameters = config["parameters"]
        self.overbought_signal_threshold = parameters["overbought_signal_threshold"]
        self.oversold_signal_threshold = parameters["oversold_signal_threshold"]

        self.timeperiod = 14
        if "timeperiod" in parameters:
            self.timeperiod = parameters["timeperiod"]
            
        self.num_candles_required = 1
        if "num_candles_required" in parameters:
            self.num_candles_required = parameters["num_candles_required"]

        super().__init__(config)


    def eval(self, avg_position, candles_df, ticker_info):
        rsi_key = "RSI"
        candles_df[rsi_key] = talib.RSI(candles_df['close'] * self.normalization_factor, timeperiod=self.timeperiod)

        #last_row = candles_df.iloc[-1]

        candles_to_evaluate = candles_df.tail(self.num_candles_required)
        #rsi = last_row[rsi_key]

        ticker = ticker_info["symbol"]
        #logger.info(f"{ticker}: REGULAR RSI: {rsi}")

        action = TradeAction.NOOP
        if (candles_to_evaluate[rsi_key] > self.overbought_signal_threshold).all():
            logger.debug(f'{ticker}: {self.name} triggered SELL signal')
            action = TradeAction.SELL
        elif (candles_to_evaluate[rsi_key] < self.oversold_signal_threshold).all():
            logger.debug(f'{ticker}: {self.name} triggered BUY signal')
            action = TradeAction.BUY

        if self.prevent_loss and action == TradeAction.SELL:
            action = self.prevent_loss_eval(avg_position, ticker_info, action)
        
        return action


