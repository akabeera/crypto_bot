import talib
from decimal import *

from .base_strategy import BaseStrategy
from utils.logger import logger
from utils.trading import TradeAction

class AdaptiveRSI(BaseStrategy):
    def __init__(self, config):
        parameters = config["parameters"]
        self.default_upper_threshold = parameters["default_upper_threshold"]
        self.default_lower_threshold = parameters["default_lower_threshold"]
        self.volatility_factor = parameters["volatility_factor"]
        self.rsi_period = parameters["rsi_period"]
        self.trend_ma_period = parameters["trend_ma_period"]
        self.trend_factor = parameters["trend_factor"]

        super().__init__(config)

    def clip(self, val, lower=None, upper=None):
        if lower:
            val = max(val, lower)
        
        if upper:
            val = min(val, upper)

        return val

    def eval(self, avg_position, candles_df, ticker_info):

        rsi_key = "ADAPTIVE_RSI"
        candles_df['close_normalized'] = candles_df['close'] * self.normalization_factor 

        candles_df['price_change_std'] = candles_df['close_normalized'].pct_change().rolling(window=self.rsi_period).std()
        candles_df["price_ma"] = candles_df['close_normalized'].rolling(window=self.trend_ma_period).mean()
        candles_df[rsi_key] = talib.RSI(candles_df['close_normalized'], timeperiod=self.rsi_period)

        last_row = candles_df.iloc[-1]

        rsi = last_row[rsi_key]
        price_ma = last_row["price_ma"]
        price_change_std = last_row['price_change_std']
        closed_normalized = last_row['close_normalized']

        # Adjust thresholds for volatility
        volatility_upper_threshold = self.default_upper_threshold + (price_change_std * self.volatility_factor)
        volatility_lower_threshold = self.default_lower_threshold - (price_change_std * self.volatility_factor)

        threshold_shift = ((closed_normalized - price_ma) / price_ma) * self.trend_factor
        trend_upper_threshold = volatility_upper_threshold + threshold_shift
        trend_lower_threshold = volatility_lower_threshold + threshold_shift

        upper_threshold = self.clip(trend_upper_threshold, upper=90, lower=55)
        lower_threshold = self.clip(trend_lower_threshold, upper=40, lower=10)

        ticker = ticker_info["symbol"]
        logger.info(f"{ticker}: std dev: {last_row['price_change_std']}, shift: {threshold_shift}")

        logger.info(f"{ticker}: ADAPTIVE RSI: {rsi}, upper: {upper_threshold}, lower: {lower_threshold}")

        action = TradeAction.NOOP
        if rsi > upper_threshold:
            logger.debug(f'{ticker}: {self.name} triggered SELL signal')
            logger.info(f"adaptive RSI triggered SELL")
            action = TradeAction.SELL
        elif rsi < lower_threshold:
            logger.debug(f'{ticker}: {self.name} triggered BUY signal, RSI: {rsi}')
            logger.info(f"adaptive RSI triggered BUY")

            action = TradeAction.BUY

        if self.prevent_loss and action == TradeAction.SELL:
            action = self.prevent_loss_eval(avg_position, ticker_info, action)
        
        return action


