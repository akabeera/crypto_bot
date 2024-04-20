import copy

from decimal import *
from enum import Enum

from utils.constants import QUANTIZING_DECIMAL
from utils.logger import logger

class TradeAction(Enum):
    BUY = 0,
    SELL = 1,
    HOLD = 2,
    NOOP = 3


class TakeProfitEvaluationType(Enum):
    AVERAGE = 0,
    INDIVIDUAL_LOTS = 1,
    AVERAGE_THEN_INDIVIDUAL_LOTS = 2,
    OPTIMIZED = 3

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

    # assume fee for selling is the same as buying
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

def find_profitable_trades(ticker_pair: str, 
                           avg_position, 
                           all_positions, 
                           ticker_info, 
                           take_profit_threshold: Decimal, 
                           take_profit_evaluation_type: TakeProfitEvaluationType = TakeProfitEvaluationType.INDIVIDUAL_LOTS):
    if not avg_position:
        return None
        
    bid_price = ticker_info["bid"]

    profitable_positions = []
    if take_profit_evaluation_type == TakeProfitEvaluationType.AVERAGE:
        profit_pct = calculate_profit_percent(avg_position, bid_price)

        if profit_pct >= take_profit_threshold:
            logger.info(f'{ticker_pair}: avg profits meets profit threshold')
            profitable_positions = all_positions

    elif take_profit_evaluation_type == TakeProfitEvaluationType.INDIVIDUAL_LOTS:
        for position in all_positions:
            profit_pct = calculate_profit_percent(position, bid_price)
            #logger.info(f'{ticker_pair}: lot {position["id"]}, profit pct: {profit_pct * 100}%')

            if profit_pct >= take_profit_threshold:
                logger.info(f'{ticker_pair}: selling individual lot {position["id"]}, profit pct: {profit_pct * 100}%')
                profitable_positions.append(position)
                
    elif take_profit_evaluation_type == TakeProfitEvaluationType.AVERAGE_THEN_INDIVIDUAL_LOTS:
        profit_pct = calculate_profit_percent(avg_position, bid_price)

        if profit_pct >= take_profit_threshold:
            logger.info(f'{ticker_pair}: avg profits meets profit threshold')
            profitable_positions = all_positions
        else:
            for position in all_positions:
                profit_pct = calculate_profit_percent(position, bid_price)
                #logger.info(f'{ticker_pair}: lot {position["id"]}, profit pct: {profit_pct * 100}%')

                if profit_pct >= take_profit_threshold:
                    logger.info(f'{ticker_pair}: selling individual lot {position["id"]}, profit pct: {profit_pct * 100}%')
                    profitable_positions.append(position)

    elif take_profit_evaluation_type == TakeProfitEvaluationType.OPTIMIZED:
        logger.warn(f'{ticker_pair}: take profit evaluation type of OPTIMIZED not supported yet')
    else:
        logger.warn(f'{ticker_pair}: unsuppored evaluation type: {take_profit_evaluation_type}')

        pass        

    if len(profitable_positions) == 0:
        return None
    
    return profitable_positions

