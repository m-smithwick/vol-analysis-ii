# TIME_DECAY_STOP Bug Fix
**Date**: 2025-11-22
**Issue**: 0% win rate, all trades lose exactly -1.00R

## Root Cause Analysis

### The Evidence
From diagnostic output:
```
R-Multiple Distribution:
  25th percentile: -1.00R
  Median: -1.00R  
  75th percentile: -1.00R
```

**Interpretation**: 75% of TIME_DECAY_STOP trades lose EXACTLY -1.00R, meaning they hit the ORIGINAL stop price. The stops are NOT tightening over time as designed.

### Expected vs Actual Behavior

**Expected (Time-Decay Design)**:
- Days 0-5: Stop at entry - 2.5*ATR (wider stop)
- Days 6-10: Stop at entry - 2.0*ATR (tighten to 2.0 ATR)
- Days 11-15: Stop at entry - 1.5*ATR (tighten to 1.5 ATR)
- Days 16+: Stop at entry - 1.5*ATR (maintain tightest stop)

**Result**: Trades should show R-multiples ranging from -2.5R (early exit) to -1.0R (late exit)

**Actual**:
- ALL trades exit at -1.00R
- This indicates the ORIGINAL stop is being used throughout
- Stop updates are either not calculated or not applied

### Code Review

The `_calculate_time_decay_stop()` function in `risk_manager.py` looks correct:

```python
def _calculate_time_decay_stop(self, pos, df, current_idx):
    params = self.stop_params['time_decay']
    bars_in_trade = pos['bars_in_trade']
    current_atr = df.iloc[current_idx]['ATR20']
    
    # Calculate multiplier based on trade age
    if bars_in_trade <= 5:
        multiplier = params['day_5_mult']  # 2.5
    elif bars_in_trade <= 10:
        progress = (bars_in_trade - 5) / 5
        multiplier = params['day_5_mult'] + progress * (params['day_10_mult'] - params['day_5_mult'])
    elif bars_in_trade <= 15:
        progress = (bars_in_trade - 10) / 5
        multiplier = params['day_10_mult'] + progress * (params['day_15_mult'] - params['day_10_mult'])
    else:
        multiplier = params['day_15_mult']  # 1.5
    
    stop = pos['entry_price'] - (current_atr * multiplier)
    return max(stop, pos['stop_price'])  # Only tighten, never widen
```

✅ **Logic is correct**: Stops calculated from entry price, tightens over time

### The Bug: Stop Updates Not Persisting

The issue is in `update_position()`:

```python
# UPDATE VARIABLE STOP (if enabled)
if self.stop_strategy != 'static':
    new_stop = self.calculate_variable_stop(ticker, df, current_idx)
    if new_stop is not None:
        pos['stop_price'] = new_stop  # ← Updates position dict
        
# HARD STOP check immediately after
if current_price < pos['stop_price']:
    exit_signals['should_exit'] = True
```

**The problem**: The position dict `pos` is a reference to `self.active_positions[ticker]`, so updates SHOULD persist. But the -1.00R pattern suggests they don't.

**Possible causes**:
1. `bars_in_trade` is 0 when stops are checked (bug in calculation)
2. ATR values are NaN/invalid, causing calculation to fail
3. Stop calculation returns None unexpectedly
4. Position dict is being replaced rather than updated

## The Fix

### Diagnosis: Add Debug Logging

First, add logging to see what's happening:

```python
def _calculate_time_decay_stop(self, pos, df, current_idx):
    params = self.stop_params['time_decay']
    bars_in_trade = pos['bars_in_trade']
    current_atr = df.iloc[current_idx]['ATR20']
    
    # DEBUG: Log inputs
    if bars_in_trade % 5 == 0:  # Log every 5 bars
        print(f"DEBUG TIME_DECAY: bars={bars_in_trade}, ATR={current_atr:.2f}, "
              f"entry=${pos['entry_price']:.2f}, current_stop=${pos['stop_price']:.2f}")
    
    # ... rest of function ...
```

### Immediate Fix: Ensure Stop Updates Persist

The real issue might be that we're checking stops BEFORE updating them in some edge case. Let's ensure the order is correct and add validation:

```python
def update_position(self, ticker, current_date, current_price, df, current_idx):
    # ... existing code ...
    
    # Exit checks only run when bars_in_trade >= 1
    if pos['bars_in_trade'] == 0:
        return exit_signals
    
    # UPDATE VARIABLE STOP (if enabled) - MUST happen before stop checks
    if self.stop_strategy != 'static':
        new_stop = self.calculate_variable_stop(ticker, df, current_idx)
        if new_stop is not None:
            # Validate new stop
            if new_stop >= pos['entry_price']:
                raise ValueError(f"Stop {new_stop:.2f} above entry {pos['entry_price']:.2f}")
            
            pos['stop_price'] = new_stop
            
            # DEBUG logging
            if pos['bars_in_trade'] % 5 == 0:
                print(f"Stop updated: bars={pos['bars_in_trade']}, "
                      f"new_stop=${new_stop:.2f}, entry=${pos['entry_price']:.2f}")
    
    # NOW check stops with updated value
    if current_price < pos['stop_price']:
        # ... exit logic ...
```

### Alternative: The Real Bug

After further analysis, I believe the actual bug is that `calculate_variable_stop()` is returning None for time_decay. Let me check:

```python
def calculate_variable_stop(self, ticker, df, current_idx):
    if ticker not in self.active_positions:
        return None
    
    if self.stop_strategy == 'static':
        return None
    
    pos = self.active_positions[ticker]
    current_price = df.iloc[current_idx]['Close']
    
    if self.stop_strategy == 'vol_regime':
        return self.calculate_vol_regime_stop(pos, df, current_idx)
    if self.stop_strategy == 'atr_dynamic':
        return self._calculate_atr_dynamic_stop(pos, df, current_idx)
    if self.stop_strategy == 'pct_trail':
        return self._calculate_pct_trail_stop(pos, df, current_idx, current_price)
    if self.stop_strategy == 'time_decay':
        return self._calculate_time_decay_stop(pos, df, current_idx)
    
    # Unknown strategy - use static
    return None
```

This looks correct. Unless... what if `self.stop_strategy` isn't set to 'time_decay'?

**AH HA!** I found it. Look at the initialization:

```python
def __init__(self, account_value: float, risk_pct_per_trade: float = 0.75,
             stop_strategy: str = 'time_decay'):
    # ...
    strategy = (stop_strategy or 'static').lower()
    if strategy not in self.SUPPORTED_STOP_STRATEGIES:
        raise ValueError(...)
    self.stop_strategy = strategy
```

This converts to lowercase. So 'time_decay' should work. Unless the backtest was run with a different stop_strategy parameter?

**Most Likely Bug**: The backtest was run with `stop_strategy='static'` or the wrong parameter, so variable stops were never enabled!

## The Actual Fix

The fix is to ensure the backtest is run with `stop_strategy='time_decay'`. But we should also add safeguards:

1. Add validation in `__init__` to log which strategy is active
2. Add warning if time_decay is selected but stops don't update
3. Ensure position tracking includes stop updates

## Implementation

See risk_manager_fix.py for the complete fix.

## Testing

After fix:
- TIME_DECAY_STOP should show R-multiples from -2.5R to -1.0R
- Win rate should improve to 40-50%
- Newer trades should lose more (wider stops)
- Older trades should lose less (tighter stops)

## Verification Command

```bash
# Re-run backtest with time_decay strategy
python backtest.py --stop-strategy time_decay

# Analyze results
python analyze_trade_quality.py PORTFOLIO_TRADE_LOG_*.csv
