import pandas as pd
import json


from utils.trading import TradeAction, TakeProfitEvaluationType, calculate_profit_percent, calculate_avg_position, round_down
from strategies.base_strategy import BaseStrategy
from strategies.strategy_factory import strategy_factory

from utils.logger import logger


def init_strategies(strategies_json_config):

    strategies: dict[str, BaseStrategy] = dict()
    
    for strategy_json_config in strategies_json_config:
        strategy_priority = strategy_json_config["priority"]
        strategy_enabled = True
        if "enabled" in strategy_json_config:
            strategy_enabled = strategy_json_config["enabled"]

        if not strategy_enabled:
            continue

        strategy_object = strategy_factory(strategy_json_config)

        if strategy_object is None:
            logger.warn(f"Encountered unsupported strategy config: {strategy_json_config}")
            continue

        if strategy_priority in strategies:
            strategies[strategy_priority].append(strategy_object)
        else:
            strategies[strategy_priority] = [strategy_object]

    strategies = dict(sorted(strategies.items()))
    return strategies


def init_strategies_overrides(strategies_overrides_json_config):
    strategies_overrides: dict[str, dict[str, BaseStrategy]] = dict()

    for so in strategies_overrides_json_config:
        tickers = so["tickers"]

        for ticker in tickers:
            if ticker not in strategies_overrides:
                    strategies_overrides[ticker] = {}
            
            for s in so["strategies"]:
                strat_name = s["name"]
                strat_object =  strategy_factory(s)
                # if strat_name not in strategies_overrides[ticker]:
                #     strategies_overrides[ticker][strat_name] = {}
                logger.info(f"{ticker}: setting strategy override for strategy: {strat_name}")
                strategies_overrides[ticker][strat_name] = strat_object

    return strategies_overrides


def execute_strategies(ticker_pair: str, 
                        strategies: dict[int, BaseStrategy], 
                        avg_position, 
                        ticker_info, 
                        candles_df: pd.DataFrame, 
                        strategies_overrides: dict[str, dict[str, BaseStrategy]] = None) -> TradeAction:

    for priority, strategies in strategies.items():
        trade_action = TradeAction.NOOP
        for s_idx, strategy in enumerate(strategies):
            curr_strat_name = strategy.name
            curr_action = TradeAction.NOOP
            strategy_to_run = strategy
            if strategies_overrides is not None:
                if ticker_pair in strategies_overrides and curr_strat_name in strategies_overrides[ticker_pair]:
                    strategy_to_run = strategies_overrides[ticker_pair][curr_strat_name]
            
            curr_action = strategy_to_run.eval(avg_position, candles_df, ticker_info)    

            if s_idx == 0:
                trade_action = curr_action
            else:
                if trade_action != curr_action:
                    break
                    
        if trade_action == TradeAction.BUY or trade_action == TradeAction.SELL:
            return trade_action
        
    return TradeAction.NOOP