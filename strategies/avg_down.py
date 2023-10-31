from decimal import *

from .base_strategy import BaseStrategy
from trading.trade_action import TradeAction

class AverageDown(BaseStrategy):
    def __init__(self, config):
        self.priority = config["priority"]
        self.threshold_percent = Decimal(config["parameters"]["threshold_percent"]/100)

    def eval(self, avg_position, candles_df, ticker_info):
        if avg_position == None:
            return TradeAction.NOOP
        
        profit_percent = self.calculate_profit_percent(avg_position, ticker_info)

        if profit_percent < self.threshold_percent:
            return TradeAction.BUY
        
        return TradeAction.HOLD