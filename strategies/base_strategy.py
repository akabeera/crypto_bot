from decimal import *
from utils.trading import calculate_profit_percent
from utils.logger import logger
from utils.trading import TradeAction

class BaseStrategy:
    def __init__(self, config):
        self.name = config["name"]
        self.priority = config["priority"]

        self.prevent_loss = True
        if "prevent_loss" in config:
            self.prevent_loss = config["prevent_loss"]

        self.enabled = True
        if "enabled" in config:
            self.enabled = config["enabled"]

        self.normalization_factor = 1
        if "normalization_factor" in config:
                self.normalization_factor = config["normalization_factor"]
        
    def eval(self, avg_position, candles_df, ticker_info) -> TradeAction:
        pass

    def prevent_loss_eval(self, avg_position, ticker_info, curr_action):
        if avg_position is None:
            return TradeAction.NOOP
        
        profit_pct = calculate_profit_percent(avg_position, ticker_info["bid"])
        if profit_pct < Decimal(0):
            logger.debug(f'{ticker_info["symbol"]}: {self.name} prevent_loss forced HOLD signal, profit: {profit_pct}')
            curr_action = TradeAction.HOLD
            
        return curr_action