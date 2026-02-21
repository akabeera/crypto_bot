import talib
from decimal import *

from .base_strategy import BaseStrategy
from utils.logger import logger
from utils.trading import TradeAction

class MACD(BaseStrategy):
    def __init__(self, config):
        self.fastperiod=12
        self.slowperiod=26 
        self.signalperiod=9

        if "parameters" in config:
            parameters = config["parameters"]

            if "fastperiod" in parameters:
                self.fastperiod = parameters["fastperiod"]

            if "slowperiod" in parameters:
                self.slowperiod = parameters["slowperiod"]

            if "signalperiod" in parameters:
                self.signalperiod = parameters["signalperiod"]

        super().__init__(config)


    def eval(self, avg_position, candles_df, ticker_info):
        if not self.enabled:
            return TradeAction.NOOP
        
        macd_key = "MACD"
        macd_signal_key = "MACD_signal"

        candles_df[macd_key], candles_df[macd_signal_key], _ = talib.MACD(candles_df['close'], fastperiod=self.fastperiod, slowperiod=self.slowperiod, signalperiod=self.signalperiod)
        
        last_row = candles_df.iloc[-1]
        macd = last_row[macd_key]
        macd_signal = last_row[macd_signal_key]

        prev_row = candles_df.iloc[-2]
        prev_macd = prev_row[macd_key]
        prev_macd_signal = prev_row[macd_signal_key]

        ticker = ticker_info["symbol"]

        action = TradeAction.NOOP
        if macd_signal < macd and macd_signal > 0:
            logger.debug(f'{ticker}: {self.name} triggered SELL signal')
            action = TradeAction.SELL
        elif macd_signal > macd and macd_signal < 0:
            logger.debug(f'{ticker}: {self.name} triggered BUY signal')
            action = TradeAction.BUY

        if self.prevent_loss and action == TradeAction.SELL:
            action = self.prevent_loss_eval(avg_position, ticker_info, action)
        
        return action


