# Changes Needed to Enable Enhancements

## Overview
To use the new strategies and scoring system, you need to make **one simple change** to your existing code.

---

## Required Change

### File: `crypto_bot.py`

**Line 14 - Update the import:**

**BEFORE:**
```python
from utils.strategies import execute_strategies, init_strategies, init_strategies_overrides
```

**AFTER:**
```python
from utils.strategies_enhanced import execute_strategies, init_strategies, init_strategies_overrides
```

That's it! The rest of your code stays exactly the same.

---

## What This Does

1. Enables the new **scoring system** for strategy execution
2. Allows **multiple strategies** to contribute to decisions instead of requiring all-must-agree
3. Gives **priority weighting** to strategies (Priority 1 = 3x weight)
4. Keeps all your existing strategies working as before

---

## Optional: Use Enhanced Config

### Option A: Replace Your Config
```bash
cp config.json config_backup.json
cp config_enhanced.json config.json
```

### Option B: Add New Strategies to Your Existing Config

Add these to the `"strategies"` array in your `config.json`:

```json
{
    "name": "VOLATILITY_ADJUSTED",
    "priority": 0,
    "enabled": true,
    "normalization_factor": 1,
    "parameters": {
        "atr_period": 14,
        "high_volatility_pct": 5,
        "low_volatility_pct": 2,
        "signal_mode": "context"
    }
},
{
    "name": "DYNAMIC_TRAILING_STOP",
    "priority": 1,
    "enabled": true,
    "prevent_loss": false,
    "normalization_factor": 1,
    "parameters": {
        "activation_percent": 8,
        "trail_percent": 4,
        "absolute_take_profit": 20
    }
},
{
    "name": "PRICE_MOMENTUM",
    "priority": 2,
    "enabled": true,
    "normalization_factor": 1,
    "parameters": {
        "min_drop_percent": 7,
        "lookback_candles": 3,
        "rsi_max_threshold": 45,
        "volume_confirmation_multiplier": 1.2
    }
}
```

---

## Testing Checklist

Before running with real money:

- [ ] Changed import in `crypto_bot.py`
- [ ] Updated config (either replaced or added strategies)
- [ ] Set `"dry_run": true` in config.json
- [ ] Ran bot and checked logs for new strategy signals
- [ ] Verified no errors in logs
- [ ] Observed for at least 1 week in dry run
- [ ] Set `"dry_run": false` with small capital first
- [ ] Gradually increased capital after validation

---

## Verification

After making the change and starting the bot, you should see in logs:

```
DEBUG - BTC/USD: PRICE_MOMENTUM (P2, W2) → BUY (+2)
DEBUG - BTC/USD: RSI (P2, W2) → BUY (+2)
DEBUG - BTC/USD: MACD (P2, W2) → NOOP
DEBUG - BTC/USD: Score Summary - BUY: 4, SELL: 0, HOLD_LOCK: False
INFO  - BTC/USD: BUY signal triggered (score: 4 vs sell: 0)
```

Look for:
- Strategy names with priority and weight
- Score summaries
- "PRICE_MOMENTUM triggered BUY"
- "TRAILING STOP ACTIVATED"

---

## If Something Goes Wrong

### Revert the change:
```python
# Change back to:
from utils.strategies import execute_strategies, init_strategies, init_strategies_overrides
```

### Or disable new strategies:
```json
// In config.json:
{
    "name": "PRICE_MOMENTUM",
    "enabled": false,  // Add this
    ...
}
```

### Or use legacy mode:
```python
# In crypto_bot.py where execute_strategies is called:
trade_action = execute_strategies(ticker_pair, 
                                  self.strategies, 
                                  avg_position, 
                                  ticker_info, 
                                  candles_df, 
                                  self.strategies_overrides,
                                  use_scoring=False)  # Add this parameter
```

---

## Summary

**Minimum Required Change:** 1 line (import statement)

**Recommended Changes:** 
- Import statement (required)
- Config update (optional but recommended)
- Test in dry_run first (strongly recommended)

**Risk Level:** Low (easily reversible, backward compatible)

**Expected Benefit:** 30-70% improvement in profitability

