from decimal import *

from .base_strategy import BaseStrategy
from utils.trading import calculate_profit_percent
from utils.logger import logger
from utils.trading import TradeAction

class AverageDown(BaseStrategy):

    def __init__(self, config):
        self.threshold_percent = Decimal(-config["parameters"]["threshold_percent"]/100)
        super().__init__(config)

    def eval(self, avg_position, candles_df, ticker_info):
        if not self.enabled:
            return TradeAction.NOOP
        
        if avg_position == None:
            return TradeAction.NOOP
        
        profit_percent = calculate_profit_percent(avg_position, ticker_info["bid"])

        if profit_percent < self.threshold_percent:
            logger.debug(f'{ticker_info["symbol"]}: strategy {self.name} trigger BUY signal')
            return TradeAction.BUY
        
        return TradeAction.HOLD