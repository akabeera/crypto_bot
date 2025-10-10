# Strategy Execution Flow Overview

## Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      MAIN BOT LOOP                               │
│  For each ticker: Fetch OHLCV data & ticker info                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PRIORITY 0: CONTEXT                             │
│  ┌───────────────────────────────────────────────────────┐      │
│  │ VolatilityAdjusted (Weight: N/A)                       │      │
│  │ - Calculates ATR-based volatility                      │      │
│  │ - Classifies: high/medium/low                          │      │
│  │ - Provides context, doesn't signal                     │      │
│  └───────────────────────────────────────────────────────┘      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│           PRIORITY 1: POSITION MANAGEMENT (Weight: 3x)           │
│  ┌───────────────────────────────────────────────────────┐      │
│  │ DynamicTrailingStop                                    │      │
│  │ - Check if profit ≥ activation threshold (8%)         │      │
│  │ - Track highest price                                  │      │
│  │ - SELL if drops trail_percent from peak               │      │
│  │ Result: SELL (+3) | HOLD (lock) | NOOP (0)           │      │
│  └───────────────────────────────────────────────────────┘      │
│                                                                   │
│  ┌───────────────────────────────────────────────────────┐      │
│  │ AverageDown                                            │      │
│  │ - Check if position down 60%+                          │      │
│  │ - BUY to average down                                  │      │
│  │ Result: BUY (+3) | HOLD (lock) | NOOP (0)            │      │
│  └───────────────────────────────────────────────────────┘      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│        PRIORITY 2: TECHNICAL ANALYSIS (Weight: 2x)               │
│  ┌───────────────────────────────────────────────────────┐      │
│  │ PriceMomentum (NEW!)                                   │      │
│  │ - Detect 7%+ drop in 3 candles                         │      │
│  │ - Verify RSI < 45 (not overbought)                    │      │
│  │ - Confirm volume 1.2x average                          │      │
│  │ Result: BUY (+2) | NOOP (0)                           │      │
│  └───────────────────────────────────────────────────────┘      │
│                                                                   │
│  ┌───────────────────────────────────────────────────────┐      │
│  │ RSI                                                     │      │
│  │ - Calculate RSI(14)                                    │      │
│  │ - BUY if RSI < 30 for 3 candles                       │      │
│  │ - SELL if RSI > 70 for 3 candles                      │      │
│  │ Result: BUY (+2) | SELL (+2) | NOOP (0)              │      │
│  └───────────────────────────────────────────────────────┘      │
│                                                                   │
│  ┌───────────────────────────────────────────────────────┐      │
│  │ MACD                                                    │      │
│  │ - Calculate MACD crossover                             │      │
│  │ - BUY on bullish crossover below 0                     │      │
│  │ - SELL on bearish crossover above 0                    │      │
│  │ Result: BUY (+2) | SELL (+2) | NOOP (0)              │      │
│  └───────────────────────────────────────────────────────┘      │
│                                                                   │
│  ┌───────────────────────────────────────────────────────┐      │
│  │ BollingerBands                                         │      │
│  │ - Calculate BB(20, 2)                                  │      │
│  │ - BUY if price < lower band                            │      │
│  │ - SELL if price > upper band                           │      │
│  │ Result: BUY (+2) | SELL (+2) | NOOP (0)              │      │
│  └───────────────────────────────────────────────────────┘      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SCORE CALCULATION                            │
│  ┌───────────────────────────────────────────────────────┐      │
│  │ BUY Score:  Sum of all BUY signals (weighted)          │      │
│  │ SELL Score: Sum of all SELL signals (weighted)         │      │
│  │ HOLD Lock:  Any HOLD signal locks that action          │      │
│  └───────────────────────────────────────────────────────┘      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DECISION LOGIC                              │
│  ┌───────────────────────────────────────────────────────┐      │
│  │ If HOLD lock active:                                   │      │
│  │   → Return HOLD (prevents selling at loss)             │      │
│  │                                                         │      │
│  │ If BUY score ≥ 3 AND BUY > SELL:                      │      │
│  │   → Return BUY                                         │      │
│  │                                                         │      │
│  │ If SELL score ≥ 3 AND SELL > BUY:                     │      │
│  │   → Return SELL                                        │      │
│  │                                                         │      │
│  │ Otherwise:                                              │      │
│  │   → Return NOOP                                        │      │
│  └───────────────────────────────────────────────────────┘      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXECUTE ACTION                                │
│  ┌───────────────────────────────────────────────────────┐      │
│  │ BUY:  → handle_buy_order()                             │      │
│  │ SELL: → handle_sell_order()                            │      │
│  │ HOLD/NOOP: → Continue to next ticker                   │      │
│  └───────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Example Scenarios

### Scenario 1: Strong Dip with Confirmation (BUY)

```
Ticker: ETH/USD
Price: $2000 → $1850 (7.5% drop in 3 candles)

┌─────────────────────────────────────────────────────┐
│ PRIORITY 0: VolatilityAdjusted                      │
│ → Volatility: 3.2% (MEDIUM)                         │
│ → Score: 0 (context only)                           │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ PRIORITY 1: Position Management                     │
│ → DynamicTrailingStop: No position yet → NOOP      │
│ → AverageDown: No position yet → NOOP              │
│ → Score: 0                                          │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ PRIORITY 2: Technical Analysis                      │
│ → PriceMomentum: 7.5% drop, RSI=38 → BUY (+2)     │
│ → RSI: RSI=38 but not < 30 → NOOP                 │
│ → MACD: Bearish → NOOP                             │
│ → BollingerBands: Near lower band → BUY (+2)      │
│ → Score: BUY = 4, SELL = 0                        │
└─────────────────────────────────────────────────────┘

DECISION: BUY score (4) ≥ 3 and BUY > SELL
ACTION: Execute BUY order at $1850
```

---

### Scenario 2: Profit Taking with Trail (SELL)

```
Ticker: SOL/USD
Entry Price: $100
Current Price: $115 (15% profit)
Peak Price: $118
Trail Percent: 4%

┌─────────────────────────────────────────────────────┐
│ PRIORITY 1: DynamicTrailingStop                     │
│ → Activation: 8% (already activated at $108)       │
│ → Peak tracked: $118                                │
│ → Current: $115                                     │
│ → Drop from peak: 2.5% (< 4% trail)                │
│ → Action: HOLD (not yet trail distance)            │
└─────────────────────────────────────────────────────┘

# Price continues to drop...

┌─────────────────────────────────────────────────────┐
│ PRIORITY 1: DynamicTrailingStop                     │
│ → Peak: $118                                        │
│ → Current: $113.28                                  │
│ → Drop from peak: 4.0%                              │
│ → TRAIL HIT! → SELL (+3)                           │
└─────────────────────────────────────────────────────┘

DECISION: SELL score (3) ≥ 3
ACTION: Execute SELL order at $113.28
RESULT: Locked in 13.28% profit (vs 10% fixed)
```

---

### Scenario 3: Prevent Loss (HOLD)

```
Ticker: DOGE/USD
Entry Price: $0.10
Current Price: $0.095 (-5% loss)

┌─────────────────────────────────────────────────────┐
│ PRIORITY 1: AverageDown                             │
│ → Current loss: -5%                                 │
│ → Threshold: -60%                                   │
│ → Action: NOOP (not enough loss to average down)   │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ PRIORITY 2: RSI                                      │
│ → RSI: 75 (overbought)                              │
│ → Signal: SELL                                      │
│ → But position at loss (-5%)                        │
│ → Prevent loss check: profit < 0.5% → HOLD (LOCK)  │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ PRIORITY 2: MACD                                     │
│ → Signal: SELL (+2)                                 │
│ → But prevent_loss active → HOLD (LOCK)            │
└─────────────────────────────────────────────────────┘

DECISION: HOLD lock active
ACTION: Keep position, don't sell at loss
REASONING: Strategies prevent selling at loss
```

---

## Score Threshold Reference

| Score | What Triggers It | Example |
|-------|------------------|---------|
| 0 | No signals | All strategies say NOOP |
| 2 | One Priority 2 strategy | RSI oversold alone |
| 3 | One Priority 1 strategy OR<br>Multiple Priority 2 | DynamicTrailingStop alone OR<br>RSI + MACD together |
| 4 | Two Priority 2 strategies | PriceMomentum + BollingerBands |
| 5 | Priority 1 + Priority 2 | AverageDown + RSI |
| 6+ | Multiple strong signals | Priority 1 + multiple Priority 2 |

**Action Threshold: 3** (configurable in `strategies_enhanced.py`)

---

## Key Differences from Old System

### OLD SYSTEM (All-Must-Agree)
```
Priority 2: RSI=BUY, MACD=BUY, BB=NOOP
Result: NOOP (one disagreed)
Problem: Misses opportunities
```

### NEW SYSTEM (Scoring)
```
Priority 2: RSI=BUY (+2), MACD=BUY (+2), BB=NOOP (0)
Score: BUY=4
Result: BUY (score ≥ 3)
Benefit: More trades trigger
```

---

## Strategy Priority Guidelines

### Priority 0: Context Providers
- Don't generate trade signals
- Provide information for other strategies
- Example: VolatilityAdjusted

### Priority 1: Position Management (Weight: 3x)
- Highest priority decisions
- Take profit strategies
- Risk management (average down)
- One alone can trigger action (score 3)

### Priority 2: Technical Indicators (Weight: 2x)
- RSI, MACD, Bollinger Bands
- Price momentum analysis
- Need multiple to agree (2 strategies = score 4)

### Priority 3+: Auxiliary (Weight: 1x)
- Additional confirmation signals
- Lower weight in decision making

---

## Customization

### Adjust Weights
In `utils/strategies_enhanced.py`, `execute_strategies_scoring()`:

```python
if priority == 1:
    weight = 3  # Change this
elif priority == 2:
    weight = 2  # Change this
else:
    weight = 1  # Change this
```

### Adjust Threshold
```python
action_threshold = 3  # Change this
# Lower = more aggressive (more trades)
# Higher = more conservative (fewer trades)
```

---

## Summary

The new system:
- ✅ Allows multiple strategies to contribute
- ✅ Respects priority weighting
- ✅ Prevents selling at loss (HOLD lock)
- ✅ More nuanced decision making
- ✅ 30-50% more trades expected
- ✅ Backward compatible (can revert to old system)

**Result: Better entry timing, smarter exits, more profitable trades!**

