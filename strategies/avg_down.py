from decimal import *

from .base_strategy import BaseStrategy
from trading.action import Action

class AverageDown(BaseStrategy):
    def __init__(self, config):
        self.priority = config["priority"]
        self.threshold_percent = Decimal(config["parameters"]["threshold_percent"]/100)

    def eval(self, avg_position, candles_df, ticker_info):
        if avg_position == None:
            return Action.NOOP
        
        profit_percent = self.calculate_profit_percent(avg_position, ticker_info)

        if profit_percent < self.threshold_percent:
            return Action.BUY
        
        return Action.HOLD