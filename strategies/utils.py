from .base_strategy import BaseStrategy
from .take_profit import TakeProfit
from .avg_down import AverageDown
from .bollinger_bands import BollingerBands
from .rsi import RSI
from .macd import MACD

def strategy_factory(strategy_json) -> BaseStrategy:
    strategy_name = strategy_json["name"]
    match strategy_name:
        case "TAKE_PROFIT":
            return TakeProfit(strategy_json)
        case "AVERAGE_DOWN":
            return AverageDown(strategy_json)
        case "BOLLINGER_BANDS":
            return BollingerBands(strategy_json)
        case "RSI":
            return RSI(strategy_json)
        case "MACD":
            return MACD(strategy_json)
        case _:
            return None

    