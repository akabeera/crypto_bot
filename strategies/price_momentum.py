import talib
from decimal import Decimal

from .base_strategy import BaseStrategy
from utils.logger import logger
from utils.trading import TradeAction

class PriceMomentum(BaseStrategy):
    """
    Opportunistic buying strategy that catches sharp price drops
    that technical indicators might miss. Complements RSI/MACD strategies.
    
    This catches "panic sells" and sharp dips that occur faster than
    indicators can respond to.
    """
    
    def __init__(self, config):
        parameters = config["parameters"]
        
        # Minimum price drop % to trigger (e.g., -7% = 7)
        self.min_drop_percent = parameters.get("min_drop_percent", 7)
        
        # Number of recent candles to evaluate for drop
        self.lookback_candles = parameters.get("lookback_candles", 3)
        
        # RSI threshold - only buy if RSI is below this (prevents buying overbought dips)
        self.rsi_max_threshold = parameters.get("rsi_max_threshold", 45)
        
        # Minimum volume increase (as multiplier of average) to confirm real move
        self.volume_confirmation_multiplier = parameters.get("volume_confirmation_multiplier", 1.2)
        
        super().__init__(config)

    def eval(self, avg_position, candles_df, ticker_info):
        if not self.enabled:
            return TradeAction.NOOP
        
        ticker = ticker_info["symbol"]
        
        # Need enough candles for analysis
        if len(candles_df) < 20:
            return TradeAction.NOOP
        
        # Calculate RSI to avoid buying overbought conditions
        rsi_key = "RSI_momentum"
        candles_df[rsi_key] = talib.RSI(candles_df['close'] * self.normalization_factor, timeperiod=14)
        
        # Get recent candles for drop analysis
        recent_candles = candles_df.tail(self.lookback_candles + 1)
        
        # Calculate price change from N candles ago to now
        price_start = recent_candles.iloc[0]['close']
        price_current = recent_candles.iloc[-1]['close']
        price_high_in_period = recent_candles['high'].max()
        
        # Calculate drop from recent high to current
        drop_percent = ((price_current - price_high_in_period) / price_high_in_period) * 100
        
        # Check volume confirmation (current volume vs average)
        avg_volume = candles_df['volume'].tail(20).mean()
        current_volume = recent_candles.iloc[-1]['volume']
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
        
        current_rsi = recent_candles.iloc[-1][rsi_key]
        
        # BUY CONDITIONS:
        # 1. Sharp drop detected
        # 2. RSI not overbought (confirms oversold condition)
        # 3. Volume confirmation (real move, not just low liquidity)
        if (drop_percent <= -self.min_drop_percent and 
            current_rsi < self.rsi_max_threshold and
            volume_ratio >= self.volume_confirmation_multiplier):
            
            logger.info(f'{ticker}: {self.name} triggered BUY signal - '
                       f'drop: {drop_percent:.2f}%, RSI: {current_rsi:.1f}, '
                       f'volume: {volume_ratio:.2f}x avg')
            return TradeAction.BUY
        
        # Log near-misses for tuning (only if close to triggering)
        if drop_percent <= -self.min_drop_percent * 0.8:
            logger.debug(f'{ticker}: {self.name} near trigger - '
                        f'drop: {drop_percent:.2f}%, RSI: {current_rsi:.1f}, '
                        f'volume: {volume_ratio:.2f}x (need {self.min_drop_percent}% drop, '
                        f'RSI<{self.rsi_max_threshold}, vol>{self.volume_confirmation_multiplier}x)')
        
        return TradeAction.NOOP

