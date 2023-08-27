from trading.action import Action

class BaseStrategy:
    def __init__(self):
        pass

    def eval(self) -> Action:
        pass