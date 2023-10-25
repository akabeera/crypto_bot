from trading.action import Action
from strategies.base_strategy import BaseStrategy

class SellStrategy(BaseStrategy):
    def __init__(self):
        pass

    def eval(self, positions, ohlcv, ticker_info) -> Action:
        pass