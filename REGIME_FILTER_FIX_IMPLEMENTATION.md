# Regime Filter Lookahead Bias Fix - Implementation Specification

**Status:** CRITICAL BUG - Affects all backtest validity  
**Priority:** HIGH  
**Date:** 2025-11-17  
**Author:** Volume Analysis System

---

## 🐛 PROBLEM STATEMENT

### Current Bug
The regime filter checks market conditions **as of TODAY** and applies that status to **ALL historical data** in backtests. This creates severe lookahead bias.

**Example of the Problem:**
```
Backtest Period: Nov 2023 - Nov 2025 (24 months)
Today's Date: Nov 17, 2025
Today's Regime: SPY below 200-day MA (FAIL)

CURRENT BEHAVIOR (BROKEN):
- System checks regime on Nov 17, 2025
- Finds regime = FAIL
- Blocks ALL signals for entire 24-month backtest
- Even though regime was PASS on most historical dates

CORRECT BEHAVIOR:
- Nov 15, 2023: Check regime as of Nov 15, 2023
- Dec 20, 2023: Check regime as of Dec 20, 2023
- Jan 10, 2024: Check regime as of Jan 10, 2024
- etc. (bar-by-bar regime checking)
```

### Impact
- **Backtest validity:** All historical backtests are contaminated with future information
- **Signal counts:** Entire backtests can be blocked/allowed based on TODAY's regime
- **Trading decisions:** System may show zero signals when many existed historically
- **Performance metrics:** Win rates, expectancy calculations all invalid

### User's Observed Symptom
- Command: `python vol_analysis.py VRT --period 24mo --backtest`
- Yesterday: Worked fine, generated trades
- Today: Only 2 tickers (MRK, LLY) generate trades
- Root cause: Market regime changed overnight, blocking all other tickers' historical signals

---

## ✅ SOLUTION ARCHITECTURE

### High-Level Design
Replace single "current regime check" with **historical regime series** that tracks regime status for each bar in the backtest.

```
BEFORE:
DataFrame (24 months of data)
    ↓
Check regime TODAY
    ↓
If FAIL: Block all signals
If PASS: Allow all signals

AFTER:
DataFrame (24 months of data)
    ↓
Fetch SPY data (24 months)
Fetch Sector data (24 months)
    ↓
Calculate regime for EACH date:
  df['Market_Regime_OK'] = [True, True, False, True, ...]
  df['Sector_Regime_OK'] = [True, False, True, True, ...]
    ↓
Filter signals bar-by-bar:
  df['Strong_Buy'] = df['Strong_Buy_raw'] & df['Market_Regime_OK'] & df['Sector_Regime_OK']
```

### Key Principles
1. **Single Point of Change:** Fix in `analysis_service.py` only
2. **No Code Duplication:** All consumers automatically fixed
3. **Performance:** Fetch benchmark data once, vectorize operations
4. **Correctness:** No lookahead bias - each bar uses only past data

### Data Flow
```
analysis_service.prepare_analysis_dataframe()
    ↓
1. Fetch ticker data (existing)
2. Calculate indicators (existing)
3. Generate raw signals (existing)
    ↓
4. NEW: regime_filter.calculate_historical_regime_series()
   - Fetches SPY historical data
   - Fetches sector ETF historical data
   - Calculates 200-day MA for SPY
   - Calculates 50-day MA for sector
   - Returns regime status for each date
    ↓
5. Apply bar-by-bar regime filter
   - df['Market_Regime_OK'] = market_series
   - df['Sector_Regime_OK'] = sector_series
   - Filter signals using vectorized operations
    ↓
6. Continue with rest of pipeline (existing)
```

---

## 📝 CODE CHANGES SPECIFICATION

### File 1: `regime_filter.py`

#### New Function: `calculate_historical_regime_series()`

**Purpose:** Calculate regime status for each date in backtest period

**Signature:**
```python
def calculate_historical_regime_series(
    ticker: str,
    df: pd.DataFrame
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate historical regime status for each bar in DataFrame.
    
    Args:
        ticker: Stock symbol (determines sector ETF)
        df: DataFrame with DatetimeIndex
        
    Returns:
        Tuple of (market_regime_ok, sector_regime_ok, overall_regime_ok)
        Each is a boolean Series aligned with df.index
    """
```

**Implementation Steps:**

1. **Fetch Benchmark Data**
   ```python
   # Get date range from DataFrame
   start_date = df.index.min() - pd.DateOffset(months=12)  # Extra buffer for MA
   end_date = df.index.max()
   
   # Fetch SPY data
   spy_data = load_benchmark_data('SPY', period=None, 
                                   start_date=start_date, 
                                   end_date=end_date)
   
   # Fetch sector ETF data
   sector_etf = get_sector_etf(ticker)
   sector_data = load_benchmark_data(sector_etf, period=None,
                                      start_date=start_date,
                                      end_date=end_date)
   ```

2. **Calculate Moving Averages**
   ```python
   # SPY 200-day MA
   spy_data['MA200'] = spy_data['Close'].rolling(200, min_periods=200).mean()
   spy_data['Market_Regime_OK'] = spy_data['Close'] > spy_data['MA200']
   
   # Sector 50-day MA
   sector_data['MA50'] = sector_data['Close'].rolling(50, min_periods=50).mean()
   sector_data['Sector_Regime_OK'] = sector_data['Close'] > sector_data['MA50']
   ```

3. **Align with DataFrame Dates**
   ```python
   # Reindex to match ticker's DataFrame (handles missing dates)
   market_regime = spy_data['Market_Regime_OK'].reindex(
       df.index, 
       method='ffill'  # Forward-fill for weekends/holidays
   ).fillna(False)  # Conservative: missing data = regime FAIL
   
   sector_regime = sector_data['Sector_Regime_OK'].reindex(
       df.index,
       method='ffill'
   ).fillna(False)
   
   overall_regime = market_regime & sector_regime
   ```

4. **Return Series**
   ```python
   return market_regime, sector_regime, overall_regime
   ```

**Error Handling:**
- If SPY data fetch fails: Return all False (conservative)
- If sector data fetch fails: Return all False
- If insufficient data for MA: Mark those dates as False
- Log warnings for any data issues

#### Modified Function: `load_benchmark_data()`

**Changes Needed:**
```python
# BEFORE:
def load_benchmark_data(ticker: str, period: str = '12mo', 
                       end_date: Optional[pd.Timestamp] = None) -> Optional[pd.DataFrame]:

# AFTER:
def load_benchmark_data(ticker: str, 
                       period: Optional[str] = '12mo',
                       start_date: Optional[pd.Timestamp] = None,
                       end_date: Optional[pd.Timestamp] = None) -> Optional[pd.DataFrame]:
    """
    Load benchmark data with flexible date range specification.
    
    Args:
        ticker: Benchmark symbol
        period: Data period (e.g., '12mo') - ignored if start_date provided
        start_date: Explicit start date (overrides period)
        end_date: Optional end date
    """
    if start_date is not None:
        # Use explicit date range
        df = yticker.history(start=start_date, end=end_date)
    elif end_date is not None:
        # Use period ending at end_date
        start_date = end_date - pd.DateOffset(months=12)
        df = yticker.history(start=start_date, end=end_date)
    else:
        # Use period from today
        df = yticker.history(period=period)
```

#### Deprecated Function: `apply_regime_filter()`

**Status:** Keep for backward compatibility but mark deprecated

**Changes:**
```python
def apply_regime_filter(df: pd.DataFrame, ticker: str, verbose: bool = False) -> pd.DataFrame:
    """
    Apply regime filter to signal DataFrame.
    
    ⚠️ DEPRECATED: This function uses current regime for all historical data.
    Use calculate_historical_regime_series() instead for backtesting.
    
    This function is kept for live trading where current regime is appropriate,
    but should NOT be used for historical backtesting.
    """
    import warnings
    warnings.warn(
        "apply_regime_filter() uses current regime for all dates. "
        "For backtesting, use calculate_historical_regime_series() instead.",
        DeprecationWarning
    )
    # ... existing implementation ...
```

---

### File 2: `analysis_service.py`

#### Modified Section: Regime Filter Application

**Location:** Around line 160

**BEFORE:**
```python
df["Stop_Loss"] = signal_generator.generate_stop_loss_signals(df)

df = regime_filter.apply_regime_filter(df, ticker, verbose=verbose)

df = indicators.create_next_day_reference_levels(df)
```

**AFTER:**
```python
df["Stop_Loss"] = signal_generator.generate_stop_loss_signals(df)

# Apply historical regime filter (bar-by-bar for backtest accuracy)
try:
    market_regime, sector_regime, overall_regime = (
        regime_filter.calculate_historical_regime_series(ticker, df)
    )
    
    # Add regime status columns
    df['Market_Regime_OK'] = market_regime
    df['Sector_Regime_OK'] = sector_regime
    df['Overall_Regime_OK'] = overall_regime
    
    # Preserve raw signals before filtering
    entry_signals = [
        'Strong_Buy', 'Moderate_Buy', 'Stealth_Accumulation',
        'Confluence_Signal', 'Volume_Breakout'
    ]
    
    for signal_col in entry_signals:
        # Preserve raw signal
        df[f'{signal_col}_raw'] = df[signal_col].copy()
        
        # Apply regime filter bar-by-bar
        df[signal_col] = df[signal_col] & df['Overall_Regime_OK']
    
    if verbose:
        filtered_count = sum(
            (df[f'{sig}_raw'].sum() - df[sig].sum()) 
            for sig in entry_signals
        )
        print(f"  🌍 Regime filter: {filtered_count} signals filtered")
        
except Exception as e:
    logger = get_logger()
    logger.warning(f"Failed to apply historical regime filter: {e}")
    logger.warning("Continuing without regime filtering")
    # Add default regime columns
    df['Market_Regime_OK'] = True
    df['Sector_Regime_OK'] = True
    df['Overall_Regime_OK'] = True

df = indicators.create_next_day_reference_levels(df)
```

**Key Points:**
- Replaces single regime check with historical series
- Preserves raw signals for analysis
- Applies filter using vectorized operations (fast)
- Graceful fallback if regime data unavailable
- Logging for debugging

---

### Files NOT Modified

#### `vol_analysis.py`
**Why:** Uses `analysis_service.prepare_analysis_dataframe()`  
**Impact:** Automatically gets fixed behavior

#### `backtest.py`
**Why:** Uses `analysis_service.prepare_analysis_dataframe()`  
**Impact:** Automatically gets fixed behavior

#### `batch_processor.py`
**Why:** Uses `analysis_service.prepare_analysis_dataframe()`  
**Impact:** Automatically gets fixed behavior

#### `batch_backtest.py`
**Why:** Calls `backtest.py` which uses `analysis_service`  
**Impact:** Automatically gets fixed behavior

**This is the power of centralized architecture - single fix propagates everywhere!**

---

## 🧪 TESTING PLAN

### Test 1: Before/After Comparison

**Test Case:**
```bash
# Run VRT backtest with current (broken) code
python vol_analysis.py VRT --period 24mo --backtest > results_before.txt

# Apply fix

# Run VRT backtest with fixed code
python vol_analysis.py VRT --period 24mo --backtest > results_after.txt

# Compare
diff results_before.txt results_after.txt
```

**Expected Changes:**
- Signal counts should be higher (more signals allowed historically)
- Trades should appear throughout backtest period (not just during good regime periods)
- Performance metrics should be more realistic

### Test 2: Regime Status Validation

**Add Debug Output:**
```python
# In analysis_service.py after regime calculation
if verbose:
    regime_summary = pd.DataFrame({
        'Market': df['Market_Regime_OK'],
        'Sector': df['Sector_Regime_OK'],
        'Overall': df['Overall_Regime_OK']
    })
    print("\nRegime Status Over Time:")
    print(regime_summary.tail(20))
    print(f"\nMarket Regime PASS: {df['Market_Regime_OK'].sum()}/{len(df)} days")
    print(f"Sector Regime PASS: {df['Sector_Regime_OK'].sum()}/{len(df)} days")
    print(f"Overall Regime PASS: {df['Overall_Regime_OK'].sum()}/{len(df)} days")
```

**Expected Results:**
- Regime status should vary over time (not all True or all False)
- Should see transitions: PASS → FAIL → PASS
- Overall PASS days should be reasonable (not 0% or 100%)

### Test 3: No Lookahead Check

**Verify Historical Accuracy:**
```python
# For a specific date in the past
test_date = pd.Timestamp('2024-06-15')

# Check regime status on that date
regime_on_date = df.loc[test_date, 'Market_Regime_OK']

# Manually verify SPY was above/below 200-day MA on that date
spy_data = yf.Ticker('SPY').history(start='2023-06-15', end='2024-06-16')
spy_data['MA200'] = spy_data['Close'].rolling(200).mean()
manual_check = spy_data.loc[test_date, 'Close'] > spy_data.loc[test_date, 'MA200']

assert regime_on_date == manual_check, "Regime calculation mismatch!"
```

### Test 4: Performance Benchmarking

**Measure Speed:**
```python
import time

start = time.time()
df = prepare_analysis_dataframe('VRT', '24mo')
elapsed = time.time() - start

print(f"Analysis time: {elapsed:.2f} seconds")
```

**Acceptable:** Should add <2 seconds for 24-month backtest (due to extra data fetches)

### Test 5: Multiple Tickers

**Test Batch:**
```bash
# Test with tickers in different sectors
python batch_backtest.py --file test_tickers.txt --period 24mo

# test_tickers.txt:
VRT
MRK
LLY
AAPL
JPM
```

**Expected:** Each ticker should have sector-specific regime checks

---

## 📋 IMPLEMENTATION STEPS

### Step 1: Backup Current Code
```bash
cp regime_filter.py regime_filter.py.backup
cp analysis_service.py analysis_service.py.backup
```

### Step 2: Modify `regime_filter.py`

1. Update `load_benchmark_data()` signature
2. Add `calculate_historical_regime_series()` function
3. Add deprecation warning to `apply_regime_filter()`
4. Test data fetching independently:
   ```python
   # Quick test
   python -c "
   import regime_filter as rf
   import pandas as pd
   test_dates = pd.date_range('2024-01-01', '2024-12-31', freq='D')
   test_df = pd.DataFrame(index=test_dates)
   market, sector, overall = rf.calculate_historical_regime_series('AAPL', test_df)
   print(f'Market PASS: {market.sum()}/{len(market)} days')
   print(f'Sector PASS: {sector.sum()}/{len(sector)} days')
   "
   ```

### Step 3: Modify `analysis_service.py`

1. Replace `apply_regime_filter()` call with new logic
2. Add error handling
3. Add verbose logging

### Step 4: Test Single Ticker
```bash
python vol_analysis.py VRT --period 24mo --backtest --debug
```

**Checkpoints:**
- No errors
- Regime status varies over time
- Signals generated throughout backtest
- Performance reasonable

### Step 5: Test Batch Processing
```bash
python batch_backtest.py --file stocks.txt --period 12mo
```

**Checkpoints:**
- All tickers process successfully
- Different sectors show different regime patterns
- No crashes or warnings

### Step 6: Validation
- Run Test 1-5 from testing plan
- Compare results with expected behavior
- Document any unexpected findings

### Step 7: Commit
```bash
git add regime_filter.py analysis_service.py
git commit -m "Fix regime filter lookahead bias - use historical bar-by-bar checking"
```

---

## 🔄 ROLLBACK PLAN

If issues arise:

```bash
# Restore backups
cp regime_filter.py.backup regime_filter.py
cp analysis_service.py.backup analysis_service.py

# Or git revert
git revert HEAD
```

**Rollback Triggers:**
- Performance degradation >5 seconds
- Errors in data fetching
- Incorrect regime calculations
- Unexpected behavior in backtests

---

## 📊 EXPECTED OUTCOMES

### Signal Count Changes

**BEFORE (Broken):**
- VRT backtest (24mo): 0 trades (if today's regime = FAIL)
- or: Many trades (if today's regime = PASS)

**AFTER (Fixed):**
- VRT backtest (24mo): Realistic number based on historical conditions
- Signals allowed on dates when regime was actually good
- Signals blocked on dates when regime was actually bad

### Performance Metrics

**More Accurate:**
- Win rates reflect true historical performance
- Expectancy based on realistic signal filtering
- Trade frequency matches actual conditions

**Example:**
```
BEFORE: 0 trades (because today SPY < 200-day MA)
AFTER: 15 trades over 24 months (when regime was actually good)
```

### Backtest Validity

✅ **No lookahead bias** - each bar uses only data available at that time  
✅ **Realistic regime filtering** - matches what would have happened in live trading  
✅ **Accurate performance metrics** - based on valid historical simulation

---

## 🎯 SUCCESS CRITERIA

1. ✅ VRT backtest generates non-zero trades regardless of today's regime
2. ✅ Regime status varies over time in DataFrame
3. ✅ Manual spot-check confirms regime calculations match SPY/sector data
4. ✅ Performance acceptable (<2 second overhead)
5. ✅ All existing tests still pass
6. ✅ Batch processing works correctly
7. ✅ No lookahead bias detected in validation

---

## 📚 TECHNICAL NOTES

### Why This Design?

**Centralized Fix:** Single point of change in `analysis_service.py`
- All consumers automatically fixed
- No code duplication
- Easier to maintain

**Vectorized Operations:** Use pandas operations, not loops
- Fast even for large date ranges
- Memory efficient
- Pythonic

**Conservative Fallbacks:** When in doubt, mark regime as FAIL
- Prevents false positives
- Better to miss signals than take bad trades
- Graceful degradation

### Performance Optimization

**Data Fetch:** 
- Fetch SPY/sector data once per backtest
- Cache could be added later if needed
- ~1 second overhead acceptable

**Calculation:**
- Vectorized rolling means (pandas optimized)
- Boolean operations very fast
- Alignment via reindex (efficient)

**Memory:**
- Additional columns: ~8 bytes × num_rows
- For 24mo = ~500 rows = 4KB
- Negligible memory impact

### Future Enhancements

1. **Caching:** Cache SPY/sector regime data to avoid repeated fetches
2. **Configurable Thresholds:** Allow user to modify 200-day/50-day MA periods
3. **Alternative Regimes:** Add options for different regime definitions
4. **Regime Diagnostics:** Built-in visualization of regime changes

---

## 🚨 CRITICAL WARNINGS

1. **All existing backtests are invalid** due to lookahead bias
2. **Re-run all validation** after fix is applied
3. **Update documentation** to explain historical regime filtering
4. **Notify users** of the fix and need to re-run backtests

---

## ✅ CHECKLIST

Before Implementation:
- [ ] Read and understand entire specification
- [ ] Review code changes carefully
- [ ] Prepare test data and validation scripts
- [ ] Backup current code

During Implementation:
- [ ] Modify `regime_filter.py`
- [ ] Test regime calculation independently
- [ ] Modify `analysis_service.py`
- [ ] Test single ticker
- [ ] Test batch processing

After Implementation:
- [ ] Run all tests from testing plan
- [ ] Compare before/after results
- [ ] Validate no lookahead bias
- [ ] Check performance
- [ ] Update documentation
- [ ] Commit changes

---

**This fix is critical for backtest validity. All historical performance metrics must be recalculated after implementation.**
