from decimal import *

FEE_MULTIPLIER = Decimal(2)

def calculate_profit_percent(avg_position, ticker_info) -> Decimal:
    if avg_position is None:
        return None
    
    ask = Decimal(ticker_info['ask'])
    price = Decimal(avg_position["price"])
    shares = Decimal(avg_position["amount"])
    fee = Decimal(avg_position["fee"]["cost"])
    cost = Decimal(avg_position["cost"])


    profit = (ask - price) * shares 
    profit_after_fees = profit - (fee * FEE_MULTIPLIER)
    profit_after_fees_pct = profit_after_fees/cost

    return profit_after_fees_pct