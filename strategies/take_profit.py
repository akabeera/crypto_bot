from decimal import *

from .base_strategy import BaseStrategy
from trading.trade_action import TradeAction
from strategies.utils import calculate_profit_percent
from utils.logger import logger

class TakeProfit(BaseStrategy):
    def __init__(self, config):
        self.priority = config["priority"]
        self.threshold_percent = Decimal(config["parameters"]["threshold_percent"]/100)

        super().__init__(config)

    def eval(self, avg_position, candles_df, ticker_info):
        if avg_position == None:
            return TradeAction.NOOP
        
        profit = calculate_profit_percent(avg_position, ticker_info)

        if profit >= self.threshold_percent:
            logger.info(f'{avg_position["symbol"]}: {self.name} triggered SELL signal')
            return TradeAction.SELL
        
        return TradeAction.HOLD
        