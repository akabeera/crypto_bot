import json
import os
import time
import pandas as pd
import utils.constants as CONSTANTS
import talib
from decimal import *
from dotenv import load_dotenv

from strategies.base_strategy import BaseStrategy
from utils.trading import TradeAction, TakeProfitEvaluationType, find_profitable_trades, calculate_avg_position, calculate_profit_percent, round_down
from utils.mongodb_service import MongoDBService
from utils.exchange_service import ExchangeService
# from utils.strategies import execute_strategies, init_strategies, init_strategies_overrides
from utils.strategies_enhanced import execute_strategies, init_strategies, init_strategies_overrides

from utils.logger import logger

load_dotenv()

CONFIG_FILE = 'config_enhanced.json'

class CryptoBot:

    def __init__(self, db_connection_string):
        with open(CONFIG_FILE) as f:
            self.config = json.load(f)
        
        self.ticker_trades_cooldown_periods = {}

        self.max_spend = Decimal(self.config[CONSTANTS.CONFIG_MAX_SPEND])
        self.amount_per_transaction = Decimal(self.config[CONSTANTS.CONFIG_AMOUNT_PER_TRANSACTION])

        if CONSTANTS.CONFIG_DB not in self.config:
            logger.error(f"missing db config, aborting")
            exit(1)

        self.reinvestment_percent = CONSTANTS.CONFIG_DEFAULT_REINVESTMENT_PERCENT
        if CONSTANTS.CONFIG_REINVESTMENT_PERCENT in self.config:
            self.reinvestment_percent = Decimal(self.config[CONSTANTS.CONFIG_REINVESTMENT_PERCENT]/100)

        self.remaining_balance = self.max_spend
        self.trade_cooldown_period = 10
        if CONSTANTS.CONFIG_TRADE_COOLDOWN_PERIOD in self.config:
            self.trade_cooldown_period = self.config[CONSTANTS.CONFIG_TRADE_COOLDOWN_PERIOD]

        self.currency: str = CONSTANTS.CONFIG_DEFAULT_CURRENCY
        if CONSTANTS.CONFIG_CURRENCY in self.config:
            self.currency =self.config[CONSTANTS.CONFIG_CURRENCY]

        self.sleep_interval = CONSTANTS.CONFIG_DEFAULT_SLEEP_INTERVAL
        if CONSTANTS.CONFIG_DEFAULT_SLEEP_INTERVAL in self.config:
            self.sleep_interval = self.config[CONSTANTS.CONFIG_SLEEP_INTERVAL]

        self.crypto_currency_sleep_interval = CONSTANTS.CONFIG_DEFAULT_CRYPTO_CURRENCY_SLEEP_INTERVAL
        if CONSTANTS.CONFIG_CRYPTO_CURRENCY_SLEEP_INTERVAL in self.config:
            self.crypto_currency_sleep_interval = self.config[CONSTANTS.CONFIG_CRYPTO_CURRENCY_SLEEP_INTERVAL]

        self.ohlcv_timeframe = CONSTANTS.CONFIG_DEFAULT_OHLCV_TIMEFRAME
        if CONSTANTS.CONFIG_OHLCV_TIMEFRAME in self.config:
            self.ohlcv_timeframe = self.config[CONSTANTS.CONFIG_OHLCV_TIMEFRAME]

        self.dynamic_timeframe = False
        if CONSTANTS.CONFIG_DYNAMIC_TIMEFRAME in self.config:
            self.dynamic_timeframe = self.config[CONSTANTS.CONFIG_DYNAMIC_TIMEFRAME]

        self.volatility_thresholds = {"high": 2.0, "low": 0.5}
        if CONSTANTS.CONFIG_VOLATILITY_THRESHOLDS in self.config:
            self.volatility_thresholds = self.config[CONSTANTS.CONFIG_VOLATILITY_THRESHOLDS]

        self.crypto_whitelist = self.config[CONSTANTS.CONFIG_SUPPORTED_CRYPTO_CURRENCIES]
        self.crypto_blacklist = []
        if CONSTANTS.CONFIG_BLACKLISTED_CRYPTO_CURRENCIES in self.config:
            self.crypto_blacklist = self.config[CONSTANTS.CONFIG_BLACKLISTED_CRYPTO_CURRENCIES]

        self.supported_crypto_list = list(set(self.crypto_whitelist).difference(self.crypto_blacklist))

        # Dynamic Coin Selection config
        self.dcs_enabled = False
        self.last_coin_refresh_time = 0
        dcs_config = self.config.get(CONSTANTS.CONFIG_DYNAMIC_COIN_SELECTION, {})
        if dcs_config.get(CONSTANTS.CONFIG_DCS_ENABLED, False):
            self.dcs_enabled = True
            self.dcs_top_n = dcs_config.get(CONSTANTS.CONFIG_DCS_TOP_N, CONSTANTS.DEFAULT_DCS_TOP_N)
            self.dcs_min_volume = dcs_config.get(CONSTANTS.CONFIG_DCS_MIN_24H_VOLUME_USD, CONSTANTS.DEFAULT_DCS_MIN_24H_VOLUME_USD)
            self.dcs_max_spread = dcs_config.get(CONSTANTS.CONFIG_DCS_MAX_SPREAD_PERCENT, CONSTANTS.DEFAULT_DCS_MAX_SPREAD_PERCENT)
            self.dcs_refresh_interval = dcs_config.get(CONSTANTS.CONFIG_DCS_REFRESH_INTERVAL_MINUTES, CONSTANTS.DEFAULT_DCS_REFRESH_INTERVAL_MINUTES)
            self.dcs_always_include = dcs_config.get(CONSTANTS.CONFIG_DCS_ALWAYS_INCLUDE, [])
            self.demoted_coins = {}  # coin -> demotion timestamp

            # Graduated exit config
            ge_config = dcs_config.get(CONSTANTS.CONFIG_DCS_GRADUATED_EXIT, {})
            self.ge_max_hold_days = ge_config.get(CONSTANTS.CONFIG_DCS_GE_MAX_HOLD_DAYS, CONSTANTS.DEFAULT_DCS_GE_MAX_HOLD_DAYS)
            self.ge_max_loss_percent = Decimal(str(ge_config.get(CONSTANTS.CONFIG_DCS_GE_MAX_LOSS_PERCENT, CONSTANTS.DEFAULT_DCS_GE_MAX_LOSS_PERCENT))) / 100
            self.ge_loss_active_after_days = ge_config.get(CONSTANTS.CONFIG_DCS_GE_LOSS_ACTIVE_AFTER_DAYS, CONSTANTS.DEFAULT_DCS_GE_LOSS_ACTIVE_AFTER_DAYS)

            # Extract base trailing stop params from strategy config for graduated exit
            self.ge_base_activation = Decimal("0.08")  # 8% default
            self.ge_base_trail = Decimal("0.04")  # 4% default
            for strat_config in self.config.get(CONSTANTS.CONFIG_STRATEGIES, []):
                if strat_config.get(CONSTANTS.CONFIG_STRATEGY_NAME) == "DYNAMIC_TRAILING_STOP":
                    params = strat_config.get(CONSTANTS.CONFIG_PARAMETERS, {})
                    self.ge_base_activation = Decimal(str(params.get("activation_percent", 8))) / 100
                    self.ge_base_trail = Decimal(str(params.get("trail_percent", 4))) / 100
                    break

        self.dry_run = False
        if CONSTANTS.CONFIG_DRY_RUN in self.config:
            self.dry_run = self.config[CONSTANTS.CONFIG_DRY_RUN]

        #TODO: Abstract mongodb service into a data_service
        db_config = self.config[CONSTANTS.CONFIG_DB]
        db_type = db_config[CONSTANTS.CONFIG_DB_TYPE] 
        self.mongodb_db_name = db_config[CONSTANTS.CONFIG_DB_NAME]
        self.current_positions_collection = db_config[CONSTANTS.CONFIG_DB_CURRENT_POSITIONS_COLLECTION]
        self.closed_positions_collection = db_config[CONSTANTS.CONFIG_DB_CLOSED_POSITIONS_COLLECTION]
        self.mongodb_service = MongoDBService(db_connection_string, self.mongodb_db_name)

        exchange_config = self.config[CONSTANTS.CONFIG_EXCHANGE]
        self.exchange_service = ExchangeService(exchange_config, self.dry_run)

        self.init()

    def init(self):
        (self.take_profit_threshold, self.take_profit_evaluation_type) = self.init_take_profits_config(self.config[CONSTANTS.CONFIG_TAKE_PROFITS])

        self.strategies: dict[str, BaseStrategy] = init_strategies(self.config, self.mongodb_service)
        self.init_overrides()

    def init_take_profits_config(self, take_profits_config):

        take_profit_threshold = CONSTANTS.DEFAULT_TAKE_PROFIT_THRESHOLD
        take_profit_evaluation_type = CONSTANTS.DEFAULT_TAKE_PROFIT_EVALUATION_TYPE

        if take_profits_config is not None:
            if CONSTANTS.CONFIG_TAKE_PROFITS_THRESHOLD_PERCENT in take_profits_config:
                take_profit_threshold = take_profits_config[CONSTANTS.CONFIG_TAKE_PROFITS_THRESHOLD_PERCENT]

            if CONSTANTS.CONFIG_TAKE_PROFITS_EVALUATION_TYPE in take_profits_config:
                take_profit_evaluation_type = take_profits_config[CONSTANTS.CONFIG_TAKE_PROFITS_EVALUATION_TYPE]

        take_profit_threshold = Decimal(take_profit_threshold/100)
        take_profit_evaluation_type = TakeProfitEvaluationType[take_profit_evaluation_type]

        return (take_profit_threshold, take_profit_evaluation_type)

    def init_overrides(self):
        if CONSTANTS.CONFIG_OVERRIDES not in self.config:
            return
        
        self.strategies_overrides: dict[str, dict[str, BaseStrategy]] = init_strategies_overrides(self.config, self.mongodb_service)
        self.overrides: dict[str, dict[str, any]] = dict()

        overrides_config = self.config[CONSTANTS.CONFIG_OVERRIDES]
        overrideable_attributes = set(CONSTANTS.CONFIG_OVERRIDEABLE_ATTRIBUTES)

        for oc in overrides_config:
            tickers = oc[CONSTANTS.CONFIG_TICKERS]

            attributes = oc.keys()
            
            for ticker in tickers:
                if ticker not in self.overrides:
                    self.overrides[ticker] = dict()

                for attribute in attributes:
                    if attribute not in overrideable_attributes:
                        continue
                    
                    self.overrides[ticker][attribute] = oc[attribute]
                    logger.info(f"{ticker}: setting override for {attribute}: {oc[attribute]}")
                        
    def _build_dynamic_coin_list(self):
        currency = self.currency.upper()

        # 1. Load markets and filter active spot USD pairs
        markets = self.exchange_service.execute_op(ticker_pair="", op=CONSTANTS.OP_LOAD_MARKETS)
        if not markets:
            logger.error("DCS: failed to load markets, falling back to static list")
            return None

        spot_pairs = []
        for symbol, market in markets.items():
            if (market.get('spot', False)
                    and market.get('active', False)
                    and market.get('quote', '') == currency):
                spot_pairs.append(symbol)

        if not spot_pairs:
            logger.error("DCS: no active spot USD pairs found, falling back to static list")
            return None

        # 2. Fetch tickers for volume and spread data
        tickers = self.exchange_service.execute_op(ticker_pair="", op=CONSTANTS.OP_FETCH_TICKERS)
        if not tickers:
            logger.error("DCS: failed to fetch tickers, falling back to static list")
            return None

        # 3. Filter and rank candidates
        blacklist_set = set(c.upper() for c in self.crypto_blacklist)
        candidates = []

        for symbol in spot_pairs:
            base = symbol.split('/')[0].upper()

            # Remove blacklisted coins
            if base in blacklist_set:
                continue

            ticker_data = tickers.get(symbol)
            if not ticker_data:
                continue

            volume_usd = ticker_data.get('quoteVolume') or 0
            bid = ticker_data.get('bid')
            ask = ticker_data.get('ask')

            # Filter by min volume
            if volume_usd < self.dcs_min_volume:
                continue

            # Filter by max spread
            if bid and ask and bid > 0:
                spread_pct = ((ask - bid) / bid) * 100
                if spread_pct > self.dcs_max_spread:
                    continue

            candidates.append((base, volume_usd))

        # 4. Sort by volume descending, take top N
        candidates.sort(key=lambda x: x[1], reverse=True)
        selected = [c[0] for c in candidates[:self.dcs_top_n]]

        # 5. Merge in always_include coins
        selected_set = set(selected)
        for coin in self.dcs_always_include:
            coin_upper = coin.upper()
            if coin_upper not in selected_set and coin_upper not in blacklist_set:
                selected.append(coin_upper)
                selected_set.add(coin_upper)

        # 6. Merge in coins with open positions from MongoDB, track demoted ones
        demoted = set()
        open_symbols = self.mongodb_service.distinct(self.current_positions_collection, 'symbol')
        for symbol in open_symbols:
            # symbol format is "BTC/USD", extract base
            base = symbol.split('/')[0].upper()
            if base not in selected_set:
                selected.append(base)
                selected_set.add(base)
                demoted.add(base)
                logger.info(f"DCS: including {base} due to open position (demoted)")

        return selected, demoted

    def _maybe_refresh_coin_list(self):
        if not self.dcs_enabled:
            return False

        elapsed_minutes = self.get_elapse_time_mins(self.last_coin_refresh_time)
        if self.last_coin_refresh_time != 0 and elapsed_minutes < self.dcs_refresh_interval:
            return False

        logger.info(f"DCS: refreshing coin list (elapsed: {elapsed_minutes:.1f} min)")
        result = self._build_dynamic_coin_list()

        if result is None:
            logger.warning("DCS: build failed, keeping current list")
            return False

        new_list, demoted_set = result

        old_set = set(self.supported_crypto_list)
        new_set = set(new_list)

        added = new_set - old_set
        removed = old_set - new_set

        if added:
            logger.info(f"DCS: added coins: {sorted(added)}")
        if removed:
            logger.info(f"DCS: removed coins: {sorted(removed)}")

        # Update demoted_coins tracking
        now = time.time()
        # Add newly demoted coins
        for coin in demoted_set:
            if coin not in self.demoted_coins:
                self.demoted_coins[coin] = now
                logger.info(f"DCS: {coin} demoted — graduated exit active")
        # Remove coins that re-qualified (no longer demoted)
        re_qualified = [c for c in self.demoted_coins if c not in demoted_set]
        for coin in re_qualified:
            del self.demoted_coins[coin]
            logger.info(f"DCS: {coin} re-qualified — graduated exit removed")

        self.supported_crypto_list = new_list
        self.last_coin_refresh_time = time.time()
        logger.info(f"DCS: active coin list ({len(new_list)}): {new_list}")
        if self.demoted_coins:
            logger.info(f"DCS: demoted coins: {list(self.demoted_coins.keys())}")
        return True

    def _check_graduated_exit(self, ticker_pair, avg_position, ticker_info, all_positions):
        if not self.dcs_enabled or avg_position is None:
            return TradeAction.NOOP

        ticker = ticker_pair.split('/')[0].upper()
        if ticker not in self.demoted_coins:
            return TradeAction.NOOP

        demotion_time = self.demoted_coins[ticker]
        days_demoted = (time.time() - demotion_time) / 86400

        # Force exit after max hold days
        if days_demoted >= self.ge_max_hold_days:
            logger.info(f"{ticker_pair}: GRADUATED EXIT — force exit after {days_demoted:.1f} days demoted")
            return TradeAction.SELL

        # Tightening factor: starts at 0.5, decays linearly to 0.1 over max_hold_days
        tightening_factor = Decimal(str(max(0.1, 0.5 - (0.4 * days_demoted / self.ge_max_hold_days))))

        effective_activation = self.ge_base_activation * tightening_factor
        effective_trail = self.ge_base_trail * tightening_factor

        profit_pct = calculate_profit_percent(avg_position, ticker_info["bid"])
        if profit_pct is None:
            return TradeAction.NOOP

        # If profit exceeds tightened activation, take it
        if profit_pct >= effective_activation:
            logger.info(f"{ticker_pair}: GRADUATED EXIT — taking profit {profit_pct*100:.2f}% "
                       f"(tightened activation: {effective_activation*100:.2f}%, "
                       f"days demoted: {days_demoted:.1f})")
            return TradeAction.SELL

        # Stop-loss active after configured grace period
        if days_demoted >= self.ge_loss_active_after_days:
            # Time-decay the max loss: starts at ge_max_loss_percent, tightens to half by max_hold_days
            days_past_grace = days_demoted - self.ge_loss_active_after_days
            remaining_days = self.ge_max_hold_days - self.ge_loss_active_after_days
            if remaining_days > 0:
                decay_factor = Decimal(str(max(0.5, 1.0 - (0.5 * days_past_grace / remaining_days))))
            else:
                decay_factor = Decimal("0.5")
            effective_max_loss = self.ge_max_loss_percent * decay_factor

            if profit_pct < CONSTANTS.ZERO and abs(profit_pct) >= effective_max_loss:
                logger.info(f"{ticker_pair}: GRADUATED EXIT — stop-loss at {profit_pct*100:.2f}% "
                           f"(max loss: -{effective_max_loss*100:.2f}%, "
                           f"days demoted: {days_demoted:.1f})")
                return TradeAction.SELL

        logger.debug(f"{ticker_pair}: graduated exit check — profit: {profit_pct*100:.2f}%, "
                    f"activation: {effective_activation*100:.2f}%, "
                    f"days demoted: {days_demoted:.1f}")
        return TradeAction.NOOP

    def run(self):
        idx = 0
        N = len(self.supported_crypto_list)
        logger.info(f"Running for following cryto currencies: ${self.supported_crypto_list}")

        while True:

            # Refresh coin list if DCS is enabled and interval has elapsed
            if self._maybe_refresh_coin_list():
                N = len(self.supported_crypto_list)
                idx = 0

            if idx == N:
                logger.debug(f"heartbeat!")
                time.sleep(self.sleep_interval)
                idx = 0

            ticker:str = self.supported_crypto_list[idx]
            idx += 1 

            ticker_pair:str = "{}/{}".format(ticker.upper(), self.currency.upper())
            
            timeframe = self.ohlcv_timeframe
            if self.dynamic_timeframe:
                timeframe = self.get_optimal_timeframe(ticker_pair)
                logger.info(f"{ticker_pair}: dynamic timeframe selected: {timeframe}")

            ohlcv = self.exchange_service.execute_op(ticker_pair=ticker_pair, op=CONSTANTS.OP_FETCH_OHLCV, params={"timeframe": timeframe})
            if ohlcv == None or len(ohlcv) == 0:
                logger.error(f"{ticker_pair}: unable to fetch ohlcv, skipping")
                continue

            if len(ohlcv) < 4:
                logger.warning(f"{ticker_pair}: not enough candles, candles len: {len(ohlcv)}, skipping")
                continue

            candles_df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])

            take_profit_threshold = self.take_profit_threshold
            take_profit_evaluation_type = self.take_profit_evaluation_type

            if ticker_pair in self.overrides and CONSTANTS.CONFIG_TAKE_PROFITS in self.overrides[ticker_pair]:
                (take_profit_threshold, take_profit_evaluation_type) = self.init_take_profits_config(self.overrides[ticker_pair][CONSTANTS.CONFIG_TAKE_PROFITS])

            ticker_filter = {
                'symbol': ticker_pair
            }
            all_positions = self.mongodb_service.query(self.current_positions_collection, ticker_filter)
            avg_position = calculate_avg_position(all_positions) 

            ticker_info = self.exchange_service.execute_op(ticker_pair=ticker_pair, op=CONSTANTS.OP_FETCH_TICKER)
            if ticker_info is None:
                logger.error(f"{ticker_pair}: error fetching ticker_info, skipping")
                continue
            
            # Graduated exit check for demoted coins (before normal strategies)
            graduated_action = self._check_graduated_exit(ticker_pair, avg_position, ticker_info, all_positions)
            if graduated_action == TradeAction.SELL and all_positions:
                self.handle_sell_order(ticker_pair, ticker_info, all_positions)
                time.sleep(self.crypto_currency_sleep_interval)
                continue

            profitable_positions_to_exit = find_profitable_trades(ticker_pair,
                                                                  avg_position,
                                                                  all_positions,
                                                                  ticker_info,
                                                                  take_profit_threshold,
                                                                  take_profit_evaluation_type)
            if profitable_positions_to_exit is not None:
                logger.info(f"{ticker_pair}: number of profitable positions to exit: {len(profitable_positions_to_exit)}")
                self.handle_sell_order(ticker_pair, ticker_info, profitable_positions_to_exit)
                continue

            self.handle_cooldown(ticker_pair)
            trade_action = execute_strategies(ticker_pair, 
                                              self.strategies, 
                                              avg_position, 
                                              ticker_info, 
                                              candles_df, 
                                              self.strategies_overrides)
            
            if trade_action == TradeAction.BUY:
                logger.info(f"{ticker_pair}: BUY signal triggered")
                self.handle_buy_order(ticker_pair, ticker_info)
            elif trade_action == TradeAction.SELL:
                logger.info(f'{ticker_pair}: SELL signal triggered, number of lots being sold: {len(all_positions)}')
                self.handle_sell_order(ticker_pair, ticker_info, all_positions)
      
            time.sleep(self.crypto_currency_sleep_interval)
        
    def handle_buy_order(self, ticker_pair: str, ticker_info = None):        
        if self.ticker_in_cooldown(ticker_pair):
            logger.warn(f"{ticker_pair} is in cooldown, skipping buy")
            return None
        
        amount = self.amount_per_transaction
        if ticker_pair in self.overrides:
            if CONSTANTS.CONFIG_AMOUNT_PER_TRANSACTION in self.overrides[ticker_pair]:
                amount = Decimal(self.overrides[ticker_pair][CONSTANTS.CONFIG_AMOUNT_PER_TRANSACTION])

        if self.remaining_balance < amount:
            logger.warn(f"{ticker_pair}: insufficient balance to place buy order, skipping")
            return None
        
        params = None
        if ticker_info is None:
            return None
        
        if "ask" in ticker_info:

            ask_price = Decimal(ticker_info["ask"])
            shares = float(amount / ask_price)
            rounded_shares = round_down(shares)
            
            params = {
                CONSTANTS.PARAM_ORDER_TYPE: "buy",
                CONSTANTS.PARAM_MARKET_ORDER_TYPE: 'limit',
                CONSTANTS.PARAM_SHARES: rounded_shares,
                CONSTANTS.PARAM_PRICE: ask_price   
            }

        else:

            params = {
                CONSTANTS.PARAM_TOTAL_COST: amount,
                CONSTANTS.PARAM_ORDER_TYPE: 'buy',
                CONSTANTS.PARAM_MARKET_ORDER_TYPE: 'market'
            }
        
        order = self.exchange_service.execute_op(ticker_pair=ticker_pair, op=CONSTANTS.OP_CREATE_ORDER, params=params)
        if not order:
            logger.error(f"{ticker_pair}: FAILED to execute buy order")
            return None
        
        self.remaining_balance -= amount
        self.mongodb_service.insert_one(self.current_positions_collection, order)
        self.start_cooldown(ticker_pair)
        logger.info(f"{ticker_pair}: BUY executed. price: {order['price']}, shares: {order['filled']}, fees: {order['fee']['cost']}, remaining balance: {self.remaining_balance}")

        return order

    def handle_sell_order(self, ticker_pair: str, ticker_info, positions_to_exit):
        if "bid" not in ticker_info:
            logger.error(f"{ticker_info}: missing bid price in ticker_info, aborting handle_sell_order")
            return None
        
        bid_price = ticker_info["bid"]
                    
        shares: float = 0.0
        positions_to_delete = []
        for position in positions_to_exit:
            shares += position["filled"]
            positions_to_delete.append(position["id"])

        rounded_shares = round_down(shares)

        params = {
            CONSTANTS.PARAM_ORDER_TYPE: "sell",
            CONSTANTS.PARAM_MARKET_ORDER_TYPE: 'limit',
            CONSTANTS.PARAM_SHARES: rounded_shares,
            CONSTANTS.PARAM_PRICE: bid_price    
        }

        order = self.exchange_service.execute_op(ticker_pair=ticker_pair, op=CONSTANTS.OP_CREATE_ORDER, params=params)
        if not order:
            logger.error(f"{ticker_pair}: FAILED to execute sell order")
            return None

        closed_position = {
            'sell_order': order,
            'closed_positions': positions_to_exit
        }
        self.mongodb_service.insert_one(self.closed_positions_collection, closed_position)
        delete_filter = {
            "id": {"$in": positions_to_delete}
        }

        deletion_result = self.mongodb_service.delete_many(self.current_positions_collection, delete_filter)
        deletion_count = deletion_result.deleted_count
        if deletion_count != len(positions_to_exit):
            logger.warn(f"{ticker_pair}: mismatch of deleted positions, deletion count: {deletion_count}, positions exited:{len(positions_to_exit)}")

        to_reinvest_percent = self.reinvestment_percent
        if ticker_pair in self.overrides:
            if CONSTANTS.CONFIG_REINVESTMENT_PERCENT in self.overrides[ticker_pair]:
                to_reinvest_percent = Decimal(self.overrides[ticker_pair][CONSTANTS.CONFIG_REINVESTMENT_PERCENT])

        proceeds = Decimal(order['info']['total_value_after_fees'])
        if to_reinvest_percent > CONSTANTS.ZERO:
            self.remaining_balance += (proceeds * to_reinvest_percent)

        logger.info(f"{ticker_pair}: SELL EXECUTED. price: {order['average']}, shares: {order['filled']}, proceeds: {proceeds}, remaining_balance: {self.remaining_balance}")
        return closed_position

    def start_cooldown(self, ticker_pair):
        self.ticker_trades_cooldown_periods[ticker_pair] = time.time()

    def ticker_in_cooldown(self, ticker_pair):
        if ticker_pair not in self.ticker_trades_cooldown_periods:
            return False
        
        last_trade_timestamp = self.ticker_trades_cooldown_periods[ticker_pair]
        elapse_time_minutes = self.get_elapse_time_mins(last_trade_timestamp)

        trade_cooldown_period = self.trade_cooldown_period
        if ticker_pair in self.overrides and CONSTANTS.CONFIG_TRADE_COOLDOWN_PERIOD in self.overrides[ticker_pair]:
            trade_cooldown_period = self.overrides[ticker_pair][CONSTANTS.CONFIG_TRADE_COOLDOWN_PERIOD]

        if elapse_time_minutes < trade_cooldown_period:
            logger.info(f"{ticker_pair}: currently in cooldown, elapse {elapse_time_minutes} of {trade_cooldown_period} minutes so far")
            return True
        
        return False

    def handle_cooldown(self, ticker_pair):
        if ticker_pair not in self.ticker_trades_cooldown_periods:
            return 
        
        last_trade_timestamp = self.ticker_trades_cooldown_periods[ticker_pair]
        elapse_time_minutes = self.get_elapse_time_mins(last_trade_timestamp)
        
        if elapse_time_minutes >= self.trade_cooldown_period:
            logger.info(f"{ticker_pair}: resetting cooldown")
            del self.ticker_trades_cooldown_periods[ticker_pair]

    def get_elapse_time_mins(self, timestamp):
        current_time = time.time()
        elapsed_time = current_time - timestamp
        elapse_time_minutes = elapsed_time/60

        return elapse_time_minutes

    def get_optimal_timeframe(self, ticker_pair):
        # Fetch 1h candles for volatility check
        ohlcv = self.exchange_service.execute_op(ticker_pair=ticker_pair, op=CONSTANTS.OP_FETCH_OHLCV, params={"timeframe": '1h'})
        if not ohlcv or len(ohlcv) < 15:
            return self.ohlcv_timeframe

        df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # Calculate ATR (14 periods)
        high = df['high']
        low = df['low']
        close = df['close']
        
        try:
            atr = talib.ATR(high, low, close, timeperiod=14)
            last_atr = atr.iloc[-1]
            last_close = close.iloc[-1]
            
            if last_close == 0:
                return self.ohlcv_timeframe

            volatility_pct = (last_atr / last_close) * 100
            
            if volatility_pct > self.volatility_thresholds["high"]:
                return '15m'
            elif volatility_pct < self.volatility_thresholds["low"]:
                return '4h'
            
        except Exception as e:
            logger.error(f"{ticker_pair}: error calculating volatility: {e}")
            
        return '1h'