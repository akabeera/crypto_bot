from enum import Enum

class TradeAction(Enum):
    BUY = 0,
    SELL = 1,
    HOLD = 2,
    NOOP = 3