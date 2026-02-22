import pandas as pd
import talib
import utils.constants as CONSTANTS

from utils.trading import TradeAction
from strategies.base_strategy import BaseStrategy
from strategies.strategy_factory import strategy_factory

from utils.logger import logger

def init_strategies(config, mongodb_service=None) -> dict[int, BaseStrategy]:
    """
    Initialize strategies from config, organized by priority.
    Returns dict where key=priority, value=list of strategies at that priority.
    """
    strategies: dict[int, BaseStrategy] = dict()
    if CONSTANTS.CONFIG_STRATEGIES not in config:
        logger.warning("missing strategies config, returning empty strategies")
        return strategies

    strategies_config = config[CONSTANTS.CONFIG_STRATEGIES]
    
    for strategy_config in strategies_config:
        strategy_priority = strategy_config[CONSTANTS.CONFIG_STRATEGY_PRIORITY]
        strategy_enabled = True
        if CONSTANTS.CONFIG_ENABLED in strategy_config:
            strategy_enabled = strategy_config[CONSTANTS.CONFIG_ENABLED]

        if not strategy_enabled:
            continue

        strategy_object = strategy_factory(strategy_config, mongodb_service)

        if strategy_object is None:
            logger.warn(f"Encountered unsupported strategy config: {strategy_config}")
            continue

        if strategy_priority in strategies:
            strategies[strategy_priority].append(strategy_object)
        else:
            strategies[strategy_priority] = [strategy_object]

    strategies = dict(sorted(strategies.items()))
    return strategies


def init_strategies_overrides(config, mongodb_service=None) -> dict[str, dict[str, BaseStrategy]]:
    """
    Initialize per-ticker strategy overrides from config.
    Returns dict where key=ticker, value=dict of strategy overrides.
    """
    strategies_overrides: dict[str, dict[str, BaseStrategy]] = dict()
    if CONSTANTS.CONFIG_OVERRIDES not in config:
        return strategies_overrides
    
    overrides_config = config[CONSTANTS.CONFIG_OVERRIDES]

    for so in overrides_config:
        tickers = so[CONSTANTS.CONFIG_TICKERS]

        for ticker in tickers:
            if ticker not in strategies_overrides:
                    strategies_overrides[ticker] = dict()
            
            if CONSTANTS.CONFIG_STRATEGIES in so:
                for s in so[CONSTANTS.CONFIG_STRATEGIES]:
                    strat_name = s[CONSTANTS.CONFIG_STRATEGY_NAME]
                    strat_object =  strategy_factory(s, mongodb_service)

                    logger.info(f"{ticker}: setting strategy override: {strat_name}")
                    strategies_overrides[ticker][strat_name] = strat_object

    return strategies_overrides


def execute_strategies_scoring(ticker_pair: str,
                               strategies: dict[int, BaseStrategy],
                               avg_position,
                               ticker_info,
                               candles_df: pd.DataFrame,
                               strategies_overrides: dict[str, dict[str, BaseStrategy]] = None,
                               trend_config: dict = None) -> TradeAction:
    """
    ENHANCED: Execute strategies using a scoring system instead of all-must-agree.
    
    Each strategy contributes to buy/sell/hold scores based on its signal and priority.
    Higher priority strategies have more weight.
    
    This allows for more nuanced decision-making:
    - Multiple weak signals can combine to trigger an action
    - Strong signal from one strategy can be tempered by others
    - Priority system remains respected
    
    Scoring:
    - BUY signal: +1 point (weighted by priority)
    - SELL signal: +1 point (weighted by priority)
    - HOLD signal: locks in that action type (e.g., prevents selling at a loss)
    - NOOP: 0 points
    
    Priority weighting:
    - Priority 1: 3x weight (most important, like take profit)
    - Priority 2: 2x weight (technical indicators)
    - Priority 3+: 1x weight
    """
    
    buy_score = 0
    sell_score = 0
    hold_lock = False
    
    # First pass: Find VolatilityAdjusted strategy to get multiplier
    volatility_multiplier = 1.0
    for priority, strategy_list in strategies.items():
        for strategy in strategy_list:
            if strategy.name == "VOLATILITY_ADJUSTED":
                # We need to cast to VolatilityAdjusted to access specific methods if not in BaseStrategy
                # But python is dynamic, so we can just try calling it if it exists
                if hasattr(strategy, "get_volatility_multiplier"):
                    # Note: We need the ticker symbol, which is in ticker_pair (e.g. BTC/USD)
                    # get_volatility_multiplier expects just the symbol usually, or we pass the whole pair
                    # Let's check how it was implemented. It takes 'ticker'.
                    # In VolatilityAdjusted.eval, it uses ticker_info["symbol"]
                    # Here we have ticker_pair. Let's assume ticker_pair is what we want or split it.
                    # Actually, VolatilityAdjusted stores state by 'ticker'.
                    # In eval it does: ticker = ticker_info["symbol"]
                    # So we should pass ticker_info["symbol"]
                    if "symbol" in ticker_info:
                        vol_mult = strategy.get_volatility_multiplier(ticker_info["symbol"])
                        volatility_multiplier = float(vol_mult)
                        logger.debug(f"{ticker_pair}: Volatility multiplier: {volatility_multiplier}")
                break
    
    for priority, strategy_list in strategies.items():
        # Calculate priority weight (lower priority number = higher weight)
        if priority == 1:
            weight = 3
        elif priority == 2:
            weight = 2
        else:
            weight = 1
            
        # Apply volatility multiplier
        # We apply it to the weight, so high volatility (mult < 1) reduces impact
        # Low volatility (mult > 1) increases impact
        weight = weight * volatility_multiplier
        
        for strategy in strategy_list:
            curr_strat_name = strategy.name
            strategy_to_run = strategy
            
            # Apply overrides if they exist
            if strategies_overrides is not None:
                if ticker_pair in strategies_overrides and curr_strat_name in strategies_overrides[ticker_pair]:
                    strategy_to_run = strategies_overrides[ticker_pair][curr_strat_name]
            
            # Execute strategy
            curr_action = strategy_to_run.eval(avg_position, candles_df, ticker_info)
            
            # Update scores based on action
            if curr_action == TradeAction.BUY:
                buy_score += weight
                logger.debug(f"{ticker_pair}: {curr_strat_name} (P{priority}, W{weight:.2f}) -> BUY (+{weight:.2f})")
            elif curr_action == TradeAction.SELL:
                sell_score += weight
                logger.debug(f"{ticker_pair}: {curr_strat_name} (P{priority}, W{weight:.2f}) -> SELL (+{weight:.2f})")
            elif curr_action == TradeAction.HOLD:
                hold_lock = True
                logger.debug(f"{ticker_pair}: {curr_strat_name} (P{priority}) -> HOLD (lock activated)")
            else:  # NOOP
                logger.debug(f"{ticker_pair}: {curr_strat_name} (P{priority}) -> NOOP")
    
    # Trend confirmation gate
    in_downtrend = False
    if trend_config and trend_config.get(CONSTANTS.CONFIG_TC_ENABLED, False):
        short_period = trend_config.get(CONSTANTS.CONFIG_TC_SHORT_EMA, CONSTANTS.DEFAULT_TC_SHORT_EMA)
        long_period = trend_config.get(CONSTANTS.CONFIG_TC_LONG_EMA, CONSTANTS.DEFAULT_TC_LONG_EMA)
        close = candles_df['close'].astype(float)
        if len(close) >= long_period:
            ema_short = talib.EMA(close, timeperiod=short_period)
            ema_long = talib.EMA(close, timeperiod=long_period)
            current_price = close.iloc[-1]
            ema_short_val = ema_short.iloc[-1]
            ema_long_val = ema_long.iloc[-1]
            in_downtrend = current_price < ema_short_val and ema_short_val < ema_long_val
            logger.debug(f"{ticker_pair}: trend gate — price: {current_price:.4f}, "
                        f"EMA{short_period}: {ema_short_val:.4f}, EMA{long_period}: {ema_long_val:.4f}, "
                        f"downtrend: {in_downtrend}")

    # Decision logic
    logger.debug(f"{ticker_pair}: Score Summary - BUY: {buy_score}, SELL: {sell_score}, HOLD_LOCK: {hold_lock}")

    # Thresholds for action (can be tuned)
    # Priority 1 strategy alone can trigger (weight=3)
    # Two Priority 2 strategies can trigger (weight=2*2=4)
    buy_threshold = 3
    sell_threshold = 3

    if in_downtrend:
        downtrend_threshold = trend_config.get(CONSTANTS.CONFIG_TC_DOWNTREND_BUY_THRESHOLD, CONSTANTS.DEFAULT_TC_DOWNTREND_BUY_THRESHOLD)
        logger.info(f"{ticker_pair}: downtrend detected, raising buy threshold from {buy_threshold} to {downtrend_threshold}")
        buy_threshold = downtrend_threshold

    # Check BUY signals (HOLD lock doesn't block buys!)
    if buy_score >= buy_threshold and buy_score > sell_score:
        logger.info(f"{ticker_pair}: BUY signal triggered (score: {buy_score} vs sell: {sell_score})")
        return TradeAction.BUY

    # Check SELL signals (HOLD lock DOES block sells to prevent selling at loss)
    if sell_score >= sell_threshold and sell_score > buy_score:
        if hold_lock:
            logger.info(f"{ticker_pair}: HOLD lock prevents SELL (sell_score: {sell_score})")
            return TradeAction.HOLD
        else:
            logger.info(f"{ticker_pair}: SELL signal triggered (score: {sell_score} vs buy: {buy_score})")
            return TradeAction.SELL
    
    return TradeAction.NOOP


def execute_strategies(ticker_pair: str,
                        strategies: dict[int, BaseStrategy],
                        avg_position,
                        ticker_info,
                        candles_df: pd.DataFrame,
                        strategies_overrides: dict[str, dict[str, BaseStrategy]] = None,
                        use_scoring: bool = True,
                        trend_config: dict = None) -> TradeAction:
    """
    Main entry point for strategy execution.

    Args:
        use_scoring: If True, uses enhanced scoring system. If False, uses legacy all-must-agree.
        trend_config: Trend confirmation gate config (EMA periods + downtrend threshold).
    """
    if use_scoring:
        return execute_strategies_scoring(ticker_pair, strategies, avg_position,
                                         ticker_info, candles_df, strategies_overrides,
                                         trend_config)
    else:
        return execute_strategies_legacy(ticker_pair, strategies, avg_position,
                                        ticker_info, candles_df, strategies_overrides)


def execute_strategies_legacy(ticker_pair: str, 
                              strategies: dict[int, BaseStrategy], 
                              avg_position, 
                              ticker_info, 
                              candles_df: pd.DataFrame, 
                              strategies_overrides: dict[str, dict[str, BaseStrategy]] = None) -> TradeAction:
    """
    LEGACY: Original all-must-agree execution logic.
    Kept for backward compatibility.
    """
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
            logger.debug(f"{ticker_pair}: strategy: {curr_strat_name}, priority: {priority}, action: {curr_action}")
            if s_idx == 0:
                trade_action = curr_action
            else:
                if trade_action != curr_action:
                    trade_action = TradeAction.NOOP
                    break
                    
        if trade_action == TradeAction.BUY or trade_action == TradeAction.SELL:
            return trade_action
        
    return TradeAction.NOOP

