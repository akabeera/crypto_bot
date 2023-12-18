import copy
from decimal import *
from utils.constants import ZERO, ONE, ONE_HUNDRED

class ReconciliationActions:

    def __init__(self):
        self.sell_order_deletions = []
        self.sell_order_insertions = []
        self.buy_order_deletions = []
        self.buy_order_updates = [] 

        self.sell_order_collection = ""
        self.buy_order_collection = ""   

def split_order(order, remaining):
    amount = Decimal(order["amount"])
    diff = amount - remaining

    sell_order = copy.deepcopy(order)
    updated_buy_order = copy.deepcopy(order)

    sell_pct = remaining/amount
    buy_pct = ONE - sell_pct
    fee = Decimal(order["fee"]["cost"])
    price = Decimal(order["average"])

    sell_order["amount"] = float(remaining)
    sell_order["filled"] = float(remaining)
    sell_order["cost"] = float(remaining * price)
    sell_order["fee"]["cost"] = float(fee * sell_pct)
    sell_order["fees"][0]["cost"] = float(fee * sell_pct)

    updated_buy_order["amount"] = float(diff)
    updated_buy_order["filled"] = float(diff)
    updated_buy_order["cost"] = float(diff * price)
    updated_buy_order["fee"]["cost"] = float(fee * buy_pct)
    updated_buy_order["fees"][0]["cost"] = float(fee * buy_pct)

    return (sell_order, updated_buy_order)

def handle_partial_order(sell_order, buy_orders) -> ReconciliationActions:
    sell_order_info = sell_order["info"]
    completion_pct = Decimal(sell_order_info["completion_percentage"])

    if completion_pct == ZERO or completion_pct == ONE_HUNDRED:
        return None
    
    actions = ReconciliationActions()

    actions.sell_order_insertions.append(
        {
            'sell_order': sell_order,
            'closed_positions': []
        }
    )
    filled = Decimal(sell_order["filled"])
    remaining = filled

    for idx, buy_order in enumerate(buy_orders):
        buy_amount = Decimal(buy_order["amount"])     
        if remaining < buy_amount:
            (split_sell_order, split_buy_order) = split_order(buy_order, remaining)
            actions.sell_order_insertions[0]["closed_positions"].append(split_sell_order)
            actions.buy_order_updates.append(split_buy_order)
            break

        remaining -= buy_amount
        actions.sell_order_insertions[0]["closed_positions"].append(buy_order)
        actions.buy_order_deletions.append(buy_order)
        
    return actions

