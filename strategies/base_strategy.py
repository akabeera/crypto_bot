from decimal import *
from trading.trade_action import TradeAction
from strategies.utils import calculate_profit_percent
from utils.logger import logger

class BaseStrategy:
    def __init__(self, config):
        self.name = config["name"]
        pass

    def eval(self, avg_position, candles_df, ticker_info) -> TradeAction:
        pass

    def prevent_loss_eval(self, avg_position, ticker_info, curr_action):
        if avg_position is None:
            return TradeAction.NOOP
        
        profit_pct = calculate_profit_percent(avg_position, ticker_info)
        if profit_pct < Decimal(0):
            logger.info(f'{ticker_info["symbol"]}: {self.name} prevent_loss forced HOLD signal, profit: {profit_pct}')
            curr_action = TradeAction.HOLD
            
        return curr_action