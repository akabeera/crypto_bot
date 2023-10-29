from decimal import *

from .base_strategy import BaseStrategy
from trading.action import Action

class TakeProfit(BaseStrategy):
    def __init__(self, config):
        self.priority = config["priority"]
        self.threshold_percent = Decimal(config["parameters"]["threshold_percent"]/100)

    def eval(self, avg_position, candles_df, ticker_info):
        if avg_position == None:
            return Action.NOOP
        
        profit = self.calculate_profit_percent(avg_position, ticker_info)

        if profit <= self.threshold_percent:
            return Action.SELL
        
        return Action.HOLD
        