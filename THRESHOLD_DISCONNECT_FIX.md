# Threshold Disconnect Fix Documentation

## Problem Summary

There was a **critical disconnect** between two parts of the trading system:

1. **Batch Summary Reports** (`batch_processor.py`) - Shows empirically optimized thresholds
   - Moderate Buy: ≥6.5 for 64.3% win rate  
   - Profit Taking: ≥7.0 for 96.1% win rate
   - Stealth Accumulation: ≥4.5 for 58.7% win rate

2. **Risk-Managed Backtest** (`backtest.py` + `batch_backtest.py`) - Uses fixed boolean signals
   - Moderate Buy: Uses ALL signals with score ≥5.0 (FIXED in code)
   - Does NOT respect empirical thresholds
   - Results in trading **59% MORE signals** than validated

**Impact**: You cannot trade the signals shown in batch summary reports because the risk-managed backtest uses different (lower) thresholds, meaning actual performance will differ significantly from expected performance.

## Root Cause

### Signal Generation Logic (`signal_generator.py`)

The signal generation functions use **hard-coded thresholds**:

```python
def generate_moderate_buy_signals(df: pd.DataFrame) -> pd.Series:
    return (
        (df['Accumulation_Score'] >= 5) &  # ❌ Fixed at 5, not 6.5!
        (df['Accumulation_Score'] < 7) &
        (df['CMF_Z'] > 0) &
        df['Above_VWAP']
    )
```

### Batch Summary Logic (`batch_processor.py`)

Batch summary uses **empirical thresholds** from `threshold_config.py`:

```python
moderate_threshold = OPTIMAL_THRESHOLDS['moderate_buy']['threshold']  # 6.5
# Displays signals meeting this threshold, but backtest doesn't use it!
```

### The Disconnect

- **Batch Summary** filters signals by empirical thresholds and shows expected performance (64.3% win rate)
- **Risk-Managed Backtest** uses raw boolean signals with lower fixed thresholds
- User sees one set of signals but trades a different set
- **Result**: False confidence in system performance

## Solution

### Three New Modules Created

#### 1. `signal_threshold_validator.py`
Core validation and filtering module:

**Key Functions:**
- `apply_empirical_thresholds(df)` - Applies validated thresholds to create `*_filtered` signals
- `compare_signal_counts(df)` - Shows raw vs filtered signal differences
- `generate_threshold_comparison_report()` - Detailed comparison report
- `validate_backtest_signals()` - Checks if backtest is using filtered signals

**Usage:**
```python
from signal_threshold_validator import apply_empirical_thresholds

# Apply empirical thresholds before backtest
df = apply_empirical_thresholds(df)

# Use filtered signals in backtest
entry_signals = ['Moderate_Buy_filtered', 'Stealth_Accumulation_filtered']
exit_signals = ['Profit_Taking_filtered', ...]
```

#### 2. `verify_threshold_disconnect.py`
Diagnostic script to demonstrate the problem:

**Features:**
- Analyzes a specific ticker
- Compares raw vs filtered signal counts
- Shows current signal status
- Generates validation report
- Provides actionable next steps

**Run it:**
```bash
python verify_threshold_disconnect.py KGC 24mo
```

#### 3. `THRESHOLD_DISCONNECT_FIX.md` (this file)
Complete documentation of problem and solution.

## How to Verify the Problem

Run the verification script on a ticker from your batch summary:

```bash
python verify_threshold_disconnect.py KGC 24mo
```

**Expected Output:**
```
🟡 MODERATE BUY DISCONNECT:
   Batch Summary Says: Use signals with score ≥6.5
   Expected Win Rate: 64.3%
   Expected Expectancy: +2.15%
   
   Risk-Managed Backtest Actually Trades: ALL signals with score ≥5.0
   Raw Signals: 68
   Filtered Signals (≥6.5): 28
   Signals You'd Trade by Mistake: 40
   
   ⚠️  You would be trading 59% MORE signals than validated!
```

This shows you're potentially trading signals that haven't been empirically validated, with unknown win rates.

## How to Fix

### Step 1: Update Batch Backtesting

Modify `batch_backtest.py` to apply empirical thresholds:

```python
from signal_threshold_validator import apply_empirical_thresholds

def run_batch_risk_managed_backtest(...):
    # After getting DataFrame from analysis
    df = apply_empirical_thresholds(df)
    
    # Use filtered signals
    entry_signals = [
        'Strong_Buy',  # No threshold issue
        'Moderate_Buy_filtered',  # ✅ Uses ≥6.5
        'Stealth_Accumulation_filtered',  # ✅ Uses ≥4.5
        'Confluence_Signal',  # No threshold issue
        'Volume_Breakout'  # No threshold issue
    ]
    
    exit_signals = [
        'Profit_Taking_filtered',  # ✅ Uses ≥7.0
        'Distribution_Warning',
        'Sell_Signal',
        'Momentum_Exhaustion',
        'Stop_Loss'
    ]
```

### Step 2: Update vol_analysis.py

When risk-managed backtest is requested, apply thresholds:

```python
if args.risk_managed:
    from signal_threshold_validator import apply_empirical_thresholds
    df = apply_empirical_thresholds(df)
    # Then run backtest with filtered signals
```

### Step 3: Verify the Fix

Re-run verification script after fixes:

```bash
python verify_threshold_disconnect.py KGC 24mo
```

Should show:
```
✅ Backtest using filtered signals
✅ Signal counts match empirical validation
✅ Expected performance metrics will be reliable
```

## Expected Impact of Fix

### Before Fix:
- Risk-managed backtest: 418 trades (all raw signals)
- Win rate: 62.4% (includes unvalidated signals)
- Average R-Multiple: 2.05R (mixed quality)

### After Fix:
- Risk-managed backtest: ~171 trades (filtered signals only)
- Win rate: Expected 64.3%+ (only validated signals)
- Average R-Multiple: Expected 2.0R+ with higher confidence
- **Trade only signals that have been empirically validated**

## Why This Matters

### Trading Implications:

**Without Fix:**
- You think you're trading signals with 64.3% win rate
- Actually trading mixed signals (some validated, some not)
- Performance may differ significantly from expectations
- Risk management assumptions may be wrong

**With Fix:**
- Trade only empirically validated signals
- Actual performance should match backtested expectations
- Higher confidence in win rates and expectancy
- Proper risk sizing based on validated statistics

### Statistical Validity:

The empirical thresholds come from actual backtest optimization:
- Moderate Buy ≥6.5: Tested on 68 signals, best 28 had 64.3% win rate
- Filters out 59% of signals that performed worse
- Without filtering, you'd trade the 40 signals that brought win rate down

## Testing Checklist

- [ ] Run `verify_threshold_disconnect.py` on multiple tickers
- [ ] Confirm signal count differences match expected ~59% reduction
- [ ] Update `batch_backtest.py` with filtered signals
- [ ] Re-run aggregate optimization with filtered signals
- [ ] Verify new results match expected empirical performance
- [ ] Update documentation to reflect the fix
- [ ] Add warning to README about using filtered signals

## Future Improvements

1. **Make signal_generator.py configurable** - Accept threshold parameters instead of hard-coded values
2. **Auto-validate in backtest** - Add automatic check that warns if using raw signals
3. **Update batch_processor** - Ensure it always uses same thresholds as backtest
4. **Add unit tests** - Test that filtered signals produce expected win rates
5. **Configuration file** - Central location for all thresholds

## Key Takeaways

1. **The disconnect was real and significant** - 59% more signals being traded than validated
2. **Batch summary was correct** - It showed properly filtered signals with validated performance
3. **Risk-managed backtest was wrong** - It used raw signals without respecting empirical thresholds
4. **Fix is straightforward** - Use `apply_empirical_thresholds()` and `*_filtered` signals
5. **Verification is critical** - Always run validation before trading

## Questions?

If you have questions about this fix or need help implementing it:

1. Review the code in `signal_threshold_validator.py`
2. Run `verify_threshold_disconnect.py` to see the issue firsthand
3. Check `threshold_config.py` for the empirical thresholds
4. Look at `signal_generator.py` to see the fixed thresholds

The fix ensures that what you see in batch summary reports matches what you'll actually trade in risk-managed backtests.
