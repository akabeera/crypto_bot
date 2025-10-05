import talib
from decimal import Decimal

from .base_strategy import BaseStrategy
from utils.logger import logger
from utils.trading import TradeAction

class VolatilityAdjusted(BaseStrategy):
    """
    Enhances other strategy signals with volatility context.
    
    Calculates ATR (Average True Range) to measure volatility and
    provides volatility-adjusted buy/sell signals:
    - High volatility: more conservative (wider thresholds)
    - Low volatility: more aggressive (tighter thresholds)
    
    This acts as a "signal enhancer" for other strategies.
    """
    
    def __init__(self, config):
        parameters = config["parameters"]
        
        # ATR period for volatility calculation
        self.atr_period = parameters.get("atr_period", 14)
        
        # Volatility thresholds (as % of price)
        self.high_volatility_threshold = Decimal(parameters.get("high_volatility_pct", 5)) / 100  # 5%
        self.low_volatility_threshold = Decimal(parameters.get("low_volatility_pct", 2)) / 100   # 2%
        
        # Should this strategy generate signals or just provide context?
        self.signal_mode = parameters.get("signal_mode", "context")  # "context" or "signal"
        
        super().__init__(config)
        
        # Store last calculated volatility for external access
        self.last_volatility_state = {}

    def calculate_volatility(self, candles_df, ticker):
        """
        Calculate ATR-based volatility as percentage of price.
        Returns: (volatility_pct, volatility_state)
        volatility_state: "high", "medium", "low"
        """
        if len(candles_df) < self.atr_period + 1:
            return None, "unknown"
        
        # Calculate ATR
        atr_key = "ATR"
        candles_df[atr_key] = talib.ATR(
            candles_df['high'], 
            candles_df['low'], 
            candles_df['close'], 
            timeperiod=self.atr_period
        )
        
        last_row = candles_df.iloc[-1]
        atr = last_row[atr_key]
        current_price = last_row['close']
        
        if current_price == 0 or atr is None:
            return None, "unknown"
        
        # ATR as percentage of price
        volatility_pct = Decimal(str(atr)) / Decimal(str(current_price))
        
        # Classify volatility
        if volatility_pct >= self.high_volatility_threshold:
            volatility_state = "high"
        elif volatility_pct <= self.low_volatility_threshold:
            volatility_state = "low"
        else:
            volatility_state = "medium"
        
        return volatility_pct, volatility_state

    def eval(self, avg_position, candles_df, ticker_info):
        if not self.enabled:
            return TradeAction.NOOP
        
        ticker = ticker_info["symbol"]
        
        volatility_pct, volatility_state = self.calculate_volatility(candles_df, ticker)
        
        if volatility_pct is None:
            return TradeAction.NOOP
        
        # Store for external access
        self.last_volatility_state[ticker] = {
            "volatility_pct": volatility_pct,
            "volatility_state": volatility_state,
            "current_price": Decimal(str(ticker_info["bid"]))
        }
        
        logger.debug(f'{ticker}: {self.name} volatility: {volatility_pct*100:.2f}% ({volatility_state})')
        
        # Context mode: just log info, don't generate signals
        if self.signal_mode == "context":
            return TradeAction.NOOP
        
        # Signal mode: adjust buy/sell aggressiveness based on volatility
        # This would work in conjunction with other strategies via scoring system
        
        # In high volatility: be more conservative (wait for stronger signals)
        # In low volatility: be more aggressive (act on weaker signals)
        # This is implemented via the scoring system in execute_strategies
        
        return TradeAction.NOOP
    
    def get_volatility_multiplier(self, ticker):
        """
        Returns a multiplier for strategy scoring based on volatility.
        High volatility = lower multiplier (more conservative)
        Low volatility = higher multiplier (more aggressive)
        """
        if ticker not in self.last_volatility_state:
            return Decimal("1.0")  # neutral
        
        state = self.last_volatility_state[ticker]["volatility_state"]
        
        if state == "high":
            return Decimal("0.7")  # reduce signal strength by 30%
        elif state == "low":
            return Decimal("1.3")  # increase signal strength by 30%
        else:
            return Decimal("1.0")  # neutral

