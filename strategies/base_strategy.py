from decimal import *
from trading.action import Action

class BaseStrategy:
    def __init__(self):
        pass

    def eval(self, avg_position, candles_df, ticker_info) -> Action:
        pass

    def calculate_profit_percent(self, avg_position, ticker_info) -> Decimal:
        ask = Decimal(ticker_info['ask'])

        market_value = Decimal(ask * avg_position.shares)
        price_paid = Decimal(avg_position.price * avg_position.shares)
        fees = Decimal(avg_position.fee*2)

        profit_dollar = market_value - price_paid - fees
        profit_pct = profit_dollar/price_paid

        return profit_pct

    def prevent_loss(self, avg_position, ticker_info, curr_action):
        if avg_position is None:
            return Action.NOOP
        
        profit_pct = self.calculate_profit_percent(avg_position, ticker_info)
        if profit_pct < Decimal(0):
            curr_action = Action.HOLD
            
        return curr_action