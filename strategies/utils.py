from decimal import *

FEE_MULTIPLIER = Decimal(2)

def calculate_profit_percent(avg_position, ticker_info) -> Decimal:
    if avg_position is None:
        return None
    
    bid = Decimal(ticker_info['bid'])
    price = Decimal(avg_position["price"])
    shares = Decimal(avg_position["amount"])
    fee = Decimal(avg_position["fee"]["cost"])
    cost = Decimal(avg_position["cost"])


    profit = (bid - price) * shares 
    profit_after_fees = profit - (fee * FEE_MULTIPLIER)
    profit_after_fees_pct = profit_after_fees/cost

    return profit_after_fees_pct

def calculate_avg_position(trades):
    if len(trades) == 0:
        return None
    
    average_trade = trades[0]

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