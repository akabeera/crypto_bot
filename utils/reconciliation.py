import copy
import pprint
from decimal import *
from pymongo.errors import PyMongoError
from utils.constants import DEFAULT_MONGO_SNAPSHOTS_COLLECTION, ZERO, ONE, ONE_HUNDRED
from utils.mongodb_service import MongoDBService

getcontext().prec = 50

class ReconciliationActions:

    def __init__(self):
        self.sell_order_deletions = []
        self.sell_order_insertions = []
        self.buy_order_insertions = []
        self.buy_order_updates = [] 
        self.buy_order_deletions = []

        self.sell_order_collection = ""
        self.buy_order_collection = ""  
        self.replay_orders_shares_tally = Decimal(0)
        self.recon_actions_shares_tally = Decimal(0)

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
        
        return f""" sell_order_insertions: {sell_order_ids_to_insert},
buy_order_insertions: {buy_order_ids_to_insert},
buy_order_updates: {buy_order_ids_to_update},
buy_order_deletions: {buy_order_ids_to_delete},
"""
    def can_automatically_reconcile(self) -> bool:
        precision = Decimal(1.0000000000000000)
        return self.replay_orders_shares_tally.quantize(precision, rounding=ROUND_HALF_UP) == self.recon_actions_shares_tally.quantize(precision, rounding=ROUND_HALF_UP)

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

def reconcile_order(sell_order, buy_orders, buy_orders_blacklist = set()) -> ReconciliationActions:
    sell_order_info = sell_order["info"]
    completion_pct = Decimal(sell_order_info["completion_percentage"])

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
            break

        remaining -= buy_amount
        actions.sell_order_insertions[0]["closed_positions"].append(buy_order)
        actions.buy_order_deletions.append(buy_order)

    return actions

def apply_reconciliation_to_db(reconcilation_actions: ReconciliationActions, mongodb_service: MongoDBService):
    try:
        if reconcilation_actions is None:
            return
        
        buy_order_collection = reconcilation_actions.buy_order_collection
        sell_order_collection = reconcilation_actions.sell_order_collection
        
        sell_order_insertions = reconcilation_actions.sell_order_insertions
        for sell_order in sell_order_insertions:
            id = sell_order["sell_order"]["id"]
            query_filter = {
                "sell_order.id": id
            }
            print(f"inserting sell order {id}")

            curr_sell_order = mongodb_service.query(sell_order_collection, query_filter)
            if len(curr_sell_order) > 0:
                print(f"WARNING: sell order already exists {id}, replacing")
                sell_replace_result = mongodb_service.replace_one(sell_order_collection, sell_order, query_filter, True)
                print(f"sell order replace result: {sell_replace_result.raw_result}")
            else:
                sell_insert_result = mongodb_service.insert_one(sell_order_collection, sell_order)
                print(f"sell insertion result: {sell_insert_result.inserted_id}")

        buy_order_deletions = reconcilation_actions.buy_order_deletions
        if len(buy_order_deletions) > 0:
            to_delete_list = []
            for buy_order in buy_order_deletions:
                to_delete_list.append(buy_order["id"])

            delete_filter = {
                'id': {"$in": to_delete_list}
            }
            print(f"deleting buy order: {to_delete_list}")
            delete_many_result = mongodb_service.delete_many(buy_order_collection, delete_filter)
            print(f"buy deletion result: {delete_many_result.raw_result}")

        buy_order_updates = reconcilation_actions.buy_order_updates
        for buy_order in buy_order_updates:
            update_filter = {
                'id': buy_order['id']
            }
            update_result = mongodb_service.replace_one(buy_order_collection, buy_order, update_filter, True)  
            print(f"buy update result: {update_result.raw_result}")

        buy_order_insertions = reconcilation_actions.buy_order_insertions
        for buy_order in buy_order_insertions:
            id = buy_order["id"]
            query_filter = {
                "id": id
            }
            curr_buy_order = mongodb_service.query(buy_order_collection, query_filter)
            if len(curr_buy_order) > 0:
                print(f"WARNING: buy order already exists {id}, replacing")
                buy_replace_result = mongodb_service.replace_one(buy_order_collection, buy_order, query_filter, True)
                print(f"buy order replace result: {buy_replace_result.raw_result}")

            else:
                buy_insert_result = mongodb_service.insert_one(buy_order_collection, buy_order)
                print(f"buy insertion result: {buy_insert_result.inserted_id}")

    except PyMongoError as e:
        print(f"An error occurred in deleteMany: {e}")

def reconcile_with_exchange(ticker_pair: str, exchange_orders) -> ReconciliationActions:
    order_cache = {}
    for order in exchange_orders:
        order_cache[order["id"]] = order

    reconciliation_actions = ReconciliationActions()
    buy_orders = []
    for idx, order in enumerate(exchange_orders):
        side = order['side']
        id = order["id"]
        filled = Decimal(order["filled"])
        amount = Decimal(order["amount"])

        if side == "buy":
            if filled != amount:
                print(f"WARNING: buy order {id} was partially filled")
            buy_orders.append(order)
            reconciliation_actions.replay_orders_shares_tally += filled
        else:
            order_info = order["info"]
            completion_pct = Decimal(order_info["completion_percentage"])
            reconciliation_actions.replay_orders_shares_tally -= filled
            print(f"{ticker_pair} evaluating sell order:{id}, date: {order['datetime']}, completion percent: {completion_pct}")

            if completion_pct == ZERO:
                continue

            buy_orders_blacklist = set()

            actions = reconcile_order(order, buy_orders, buy_orders_blacklist)
            buy_orders_total = ZERO
            for db in actions.buy_order_deletions:
                buy_orders_total += Decimal(db["filled"])
            buy_order_update = ZERO
            if len(actions.buy_order_updates) > 0:
                buy_order_update = Decimal(actions.buy_order_updates[0]['filled'])
            print(f"{ticker_pair} filled from CB order: {filled}, tally after reconcile order: {buy_orders_total - buy_order_update}")

            reconciliation_actions.sell_order_deletions.extend(actions.sell_order_deletions) 
            reconciliation_actions.sell_order_insertions.extend(actions.sell_order_insertions)
            reconciliation_actions.buy_order_deletions.extend(actions.buy_order_deletions)
            reconciliation_actions.buy_order_updates.extend(actions.buy_order_updates)
            reconciliation_actions.buy_order_insertions.extend(actions.buy_order_insertions)

            ids_to_cleanup = {bod["id"] for bod in actions.buy_order_deletions}
            buy_orders = [bo for bo in buy_orders if bo["id"] not in ids_to_cleanup]
            if len(actions.buy_order_updates) > 0:
                buy_orders.insert(0, actions.buy_order_updates[0])

            reconciliation_actions.buy_order_updates = [bu for bu in reconciliation_actions.buy_order_updates if bu["id"] not in ids_to_cleanup]
            
        if idx == len(exchange_orders) - 1:
            reconciliation_actions.buy_order_insertions.extend(buy_orders)
    
    print(f"{ticker_pair} reconciliation actions")
    print(actions)
    
    #calculate current position based on the recon actions
    for buy_inserts in reconciliation_actions.buy_order_insertions:
        reconciliation_actions.recon_actions_shares_tally += Decimal(buy_inserts["filled"])
    for buy_updates in reconciliation_actions.buy_order_updates:
        reconciliation_actions.recon_actions_shares_tally += Decimal(buy_updates["filled"])

    print(f"{ticker_pair} recon actions tally: {reconciliation_actions.recon_actions_shares_tally} shares, replaying orders tally: {reconciliation_actions.replay_orders_shares_tally} shares")
    return reconciliation_actions