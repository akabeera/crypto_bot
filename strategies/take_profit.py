from .sell_strategy import SellStrategy

class TakeProfit(SellStrategy):
    def __init__(self, config):
        self.priority = config["priority"]
        self.threshold = config["parameters"]["threshold_percent"]

    def eval(self, positions, ohlcv, ticker_info):
        pass
    