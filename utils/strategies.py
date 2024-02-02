import pandas as pd

from utils.trading import TradeAction, TakeProfitEvaluationType, calculate_profit_percent, calculate_avg_position, round_down
from strategies.base_strategy import BaseStrategy
from strategies.strategy_factory import strategy_factory

from utils.logger import logger

def init_strategies(config):

    strategies: dict[int, BaseStrategy] = dict()
    if "strategies" not in config:
        logger.warning("missing strategies config, returning empty strategies")
        return strategies

    strategies_config = config["strategies"]
    
    for strategy_config in strategies_config:
        strategy_priority = strategy_config["priority"]
        strategy_enabled = True
        if "enabled" in strategy_config:
            strategy_enabled = strategy_config["enabled"]

        if not strategy_enabled:
            continue

        strategy_object = strategy_factory(strategy_config)

        if strategy_object is None:
            logger.warn(f"Encountered unsupported strategy config: {strategy_config}")
            continue

        if strategy_priority in strategies:
            strategies[strategy_priority].append(strategy_object)
        else:
            strategies[strategy_priority] = [strategy_object]

    strategies = dict(sorted(strategies.items()))
    return strategies


def init_strategies_overrides(config):

    strategies_overrides: dict[str, dict[str, BaseStrategy]] = dict()
    if "strategies_overrides" not in config:
        return strategies_overrides
    
    strategies_overrides_config = config["strategies_overrides"]

    for so in strategies_overrides_config:
        tickers = so["tickers"]

        for ticker in tickers:
            if ticker not in strategies_overrides:
                    strategies_overrides[ticker] = dict()
            
            for s in so["strategies"]:
                strat_name = s["name"]
                strat_object =  strategy_factory(s)

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