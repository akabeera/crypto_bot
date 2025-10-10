from strategies.base_strategy import BaseStrategy
from strategies.take_profit import TakeProfit
from strategies.avg_down import AverageDown
from strategies.bollinger_bands import BollingerBands
from strategies.rsi import RSI
from strategies.adaptive_rsi import AdaptiveRSI
from strategies.macd import MACD
from strategies.price_momentum import PriceMomentum
from strategies.dynamic_trailing_stop import DynamicTrailingStop
from strategies.volatility_adjusted import VolatilityAdjusted


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
        case "ADAPTIVE_RSI":
            return AdaptiveRSI(strategy_json)
        case "MACD":
            return MACD(strategy_json)
        case "PRICE_MOMENTUM":
            return PriceMomentum(strategy_json)
        case "DYNAMIC_TRAILING_STOP":
            return DynamicTrailingStop(strategy_json)
        case "VOLATILITY_ADJUSTED":
            return VolatilityAdjusted(strategy_json)
        case _:
            return None
        


    