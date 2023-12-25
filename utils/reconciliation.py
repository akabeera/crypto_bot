import copy
from decimal import *
from pymongo.errors import PyMongoError
from utils.constants import ZERO, ONE, ONE_HUNDRED
from utils.mongodb_service import MongoDBService

class ReconciliationActions:

    def __init__(self):
        self.sell_order_deletions = []
        self.sell_order_insertions = []
        self.buy_order_insertions = []
        self.buy_order_updates = [] 
        self.buy_order_deletions = []


        self.sell_order_collection = ""
        self.buy_order_collection = ""  

    def __repr__(self) -> str:

        sell_order_ids_to_insert = []
        for order in self.sell_order_insertions:
            sell_order_ids_to_insert.append(order["sell_order"]["id"])

        buy_order_ids_to_insert = []
        for order in self.buy_order_insertions:
            buy_order_ids_to_insert.append(order["id"])       

        buy_order_ids_to_update = []
        for order in self.buy_order_updates:
            buy_order_ids_to_update.append(order["id"])

        buy_order_ids_to_delete = []
        for order in self.buy_order_deletions:
            buy_order_ids_to_delete.append(order["id"])
        
        return f""" 
sell_order_insertions: {sell_order_ids_to_insert},
buy_order_insertions: {buy_order_ids_to_insert},
buy_order_updates: {buy_order_ids_to_update},
buy_order_deletions: {buy_order_ids_to_delete},
"""


def split_order(order, remaining):
    amount = Decimal(order["filled"])
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

def handle_partial_order(sell_order, buy_orders, buy_orders_blacklist = set()) -> ReconciliationActions:
    sell_order_info = sell_order["info"]
    completion_pct = Decimal(sell_order_info["completion_percentage"])

    # if completion_pct == ZERO or completion_pct == ONE_HUNDRED:
    #     return None

    if completion_pct == ZERO:
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
    error_tolerance = Decimal(1)

    for buy_order in buy_orders:
        id = buy_order["id"]
        if id in buy_orders_blacklist:
            #print(f"WARNING: buy order {id} blacklisted, skipping")
            continue

        buy_amount = Decimal(buy_order["filled"])
        if  remaining < buy_amount:
            (split_sell_order, split_buy_order) = split_order(buy_order, remaining)
            actions.sell_order_insertions[0]["closed_positions"].append(split_sell_order)
            print(f"splitting buy order {id} of {buy_amount} shares into sell: {split_sell_order['filled']}, buy: {split_buy_order['filled']}")
            actions.buy_order_updates.append(split_buy_order)
            actions.buy_order_deletions.append(buy_order)

            # if idx+1 < len(buy_orders):
            #     actions.buy_order_insertions.extend(buy_orders[idx+1:])
            break

        remaining -= buy_amount
        actions.sell_order_insertions[0]["closed_positions"].append(buy_order)
        actions.buy_order_deletions.append(buy_order)

    return actions

def reconcile(reconcilation_actions: ReconciliationActions, mongodb_service: MongoDBService):
    try:
        if reconcilation_actions is None:
            return

        sell_order_insertions = reconcilation_actions.sell_order_insertions
        for sell_order in sell_order_insertions:
            id = sell_order["sell_order"]["id"]
            query_filter = {
                "sell_order.id": id
            }

            curr_sell_order = mongodb_service.query(reconcilation_actions.sell_order_collection, query_filter)
            if len(curr_sell_order) > 0:
                print(f"WARNING: sell order already exists {id}, skipping")
                continue

            sell_insert_result = mongodb_service.insert_one(reconcilation_actions.sell_order_collection, sell_order)
            print(f"sell insertion result: {sell_insert_result}")

        buy_order_deletions = reconcilation_actions.buy_order_deletions
        if len(buy_order_deletions) > 0:
            to_delete_list = []
            for buy_order in buy_order_deletions:
                to_delete_list.append(buy_order["id"])

            delete_filter = {
                'id': {"$in": to_delete_list}
            }
            delete_many_result = mongodb_service.delete_many(reconcilation_actions.buy_order_collection, delete_filter)
            print(f"buy deletion result: {delete_many_result}")

        buy_order_updates = reconcilation_actions.buy_order_updates
        for buy_order in buy_order_updates:
            update_filter = {
                'id': buy_order['id']
            }
            update_result = mongodb_service.replace_one(reconcilation_actions.buy_order_collection, buy_order, update_filter, True)  
            print(f"buy update result: {update_result}")

        buy_order_insertions = reconcilation_actions.buy_order_insertions
        for buy_order in buy_order_insertions:
            id = buy_order["id"]
            query_filter = {
                "id": id
            }
            curr_buy_order = mongodb_service.query(reconcilation_actions.buy_order_collection, query_filter)
            if len(curr_buy_order) > 0:
                print(f"WARNING: buy order already exists {id}, skipping insert")
                continue
            buy_insert_result = mongodb_service.insert_one(reconcilation_actions.buy_order_collection, buy_order)
            print(f"buy insertion result: {buy_insert_result}")

    except PyMongoError as e:
        print(f"An error occurred in deleteMany: {e}")