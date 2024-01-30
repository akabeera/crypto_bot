import copy

from decimal import *
from enum import Enum

from utils.constants import QUANTIZING_DECIMAL

class TradeAction(Enum):
    BUY = 0,
    SELL = 1,
    HOLD = 2,
    NOOP = 3


class TakeProfitEvaluationType(Enum):
    AVERAGE = 0,
    INDIVIDUAL_LOTS = 1,
    OPTIMIZED = 2

FEE_MULTIPLIER = Decimal(2)

def round_down(num: float) -> float:
    return float(Decimal(num).quantize(QUANTIZING_DECIMAL, rounding=ROUND_DOWN))


def calculate_profit_percent(position, bid_price: float) -> Decimal:
    if position is None:
        return None
    
    bid = Decimal(bid_price)
    price = Decimal(position["price"])
    shares = Decimal(position["amount"])
    fee = Decimal(position["fee"]["cost"])
    cost = Decimal(position["cost"])

    profit = (bid - price) * shares 
    profit_after_fees = profit - (fee * FEE_MULTIPLIER)
    profit_after_fees_pct = profit_after_fees/cost

    return profit_after_fees_pct

def calculate_avg_position(trades):
    if len(trades) == 0:
        return None
    
    average_trade = copy.deepcopy(trades[0])

    for idx, trade in enumerate(trades):
        if idx == 0:
            continue

        shares = trade["filled"]
        fee = trade["fee"]["cost"]

        average_trade["filled"] += shares
        average_trade["amount"] += shares
        average_trade["fee"]["cost"] += fee
        average_trade["cost"] += trade["cost"]
        
    average_trade["price"] = average_trade["cost"]/average_trade["amount"]
    average_trade["average"] = average_trade["cost"]/average_trade["amount"]

    return average_trade