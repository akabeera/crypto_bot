from trading.action import Action

class BaseStrategy:
    def __init__(self):
        pass

    def eval(self, positions, ohlcv, ticker_info) -> Action:
        pass