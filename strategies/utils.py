from .base_strategy import BaseStrategy

def strategy_factory(strategyJson) -> BaseStrategy:
    strategy_name = strategyJson["name"]
    match strategy_name:
        case "TAKE_PROFIT":
            print("hello")
        case "AVERAGE_DOWN":
            print("hello")
        case "BOLLINGER_BANDS":
            print("sdjflsd")
        case _:
            print('not supported')

    