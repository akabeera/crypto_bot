# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the bot
python main.py

# Run all tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/unit/test_trading_utils.py -v

# Run a single test
python -m pytest tests/unit/test_trading_utils.py::TestUtils::test_calculate_avg_position -v

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt
```

There is no linter or formatter configured.

## Architecture

### Core Flow
`main.py` → `CryptoBot.__init__()` → `CryptoBot.run()` (infinite loop)

The main loop in `run()` iterates synchronously through `supported_crypto_list`. For each coin:
1. Optionally refresh coin list via Dynamic Coin Selection (DCS)
2. Fetch OHLCV data (with optional dynamic timeframe based on ATR volatility)
3. Check graduated exit for demoted coins (DCS feature)
4. Check profitable positions via `find_profitable_trades()` → auto-sell
5. Execute strategy scoring pipeline → BUY/SELL/HOLD/NOOP
6. Execute orders via exchange service

### Strategy System
Strategies extend `BaseStrategy` and implement `eval(avg_position, candles_df, ticker_info) → TradeAction`. They are registered in `strategies/strategy_factory.py` via match/case on the strategy name string.

**Execution** (`utils/strategies_enhanced.py`): Strategies are grouped by priority (lower = higher importance). The scoring system weights signals: P1=3x, P2=2x, P3+=1x. A score of ≥3 triggers action. HOLD signals block sells to prevent loss-making exits. A volatility multiplier from `VOLATILITY_ADJUSTED` strategy adjusts all weights.

**Overrides**: Per-ticker strategy parameter overrides are defined in `config_enhanced.json` under `overrides[]`. These create separate strategy instances for specific tickers.

### Dynamic Coin Selection (DCS)
Instead of a hardcoded coin list, DCS discovers coins from the exchange via `load_markets()` + `fetch_tickers()`, filtering by volume and spread. Coins with open positions are always included but tracked as "demoted" with graduated exit logic (time-decaying trailing stop tightening → eventual force exit).

### Services
- **ExchangeService** (`utils/exchange_service.py`): Singleton wrapping ccxt. All exchange calls go through `execute_op(ticker_pair, op, params)`. Supports dry_run mode.
- **MongoDBService** (`utils/mongodb_service.py`): Singleton wrapping pymongo. Stores current positions (`trades`), closed positions (`sell_orders`), strategy state (`strategy_state`).

### Config
`config_enhanced.json` is the active config. All config key strings are defined as constants in `utils/constants.py`. The config supports per-ticker overrides for `amount_per_transaction`, `reinvestment_percent`, `trade_cooldown_period`, `take_profits`, and strategy parameters.

### Financial Calculations
All monetary calculations use `Decimal` (not float) for precision. Fee-aware profit calculation is in `utils/trading.py:calculate_profit_percent()`. Position averaging across multiple lots is in `calculate_avg_position()`.

## Testing
Tests use pytest with mongomock for MongoDB. Fixtures are in `tests/fixtures/`. One pre-existing test failure exists: `test_calculate_profit_percent_loss` (decimal precision mismatch).

## Environment
Requires `.env` file with `API_KEY`, `API_SECRET`, and `DB_CONNECTION_STRING`. TA-Lib C library must be installed separately before `pip install TA-Lib`.
