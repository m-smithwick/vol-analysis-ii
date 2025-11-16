# Cache Corruption Bug Report - test_variable_stops.py

**Date:** November 16, 2025  
**Severity:** HIGH - Data Integrity Issue  
**Status:** IDENTIFIED - Ready for Fix  
**Affected Files:** VRT_data.csv, ORCL_data.csv, AMZN_data.csv (yfinance cache)

## Summary

The `test_variable_stops.py` script contains two bugs that corrupted yfinance cache files during extended testing, reducing multi-month datasets to 5-6 days of data.

## Root Cause Analysis

### Bug #1: Hardcoded Period (Line 240)

**Location:** `calculate_all_indicators()` function

```python
result_df = vol_analysis.analyze_ticker(
    ticker=ticker, 
    period='1y',  # <-- BUG: Hardcoded to 1 year
    # ...
)
```

**Impact:** When test runs with `--period 2y`, the indicator calculation requests only 1y data, causing mismatch.

### Bug #2: Forced yfinance Data Source (Line 246)

**Location:** `calculate_all_indicators()` function

```python
result_df = vol_analysis.analyze_ticker(
    ticker=ticker,
    # ...
    data_source='yfinance'  # <-- BUG: Ignores MASSIVE cache completely
)
```

**Impact:** 
- Bypasses MASSIVE cache entirely (which has complete data through Nov 14)
- Forces fresh yfinance downloads
- yfinance failures/partial downloads overwrite good caches

### Bug #3: Unnecessary Re-Download (Design Flaw)

**Location:** `calculate_all_indicators()` function entire design

**Problem:** Function receives df as parameter but ignores it and re-downloads data:

```python
def calculate_all_indicators(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    # Ignores df parameter!
    # Re-downloads data via analyze_ticker()
    # Should just calculate indicators on existing df
```

**Impact:** Wastes bandwidth, time, and corrupts caches unnecessarily.

## How Corruption Occurred

### Extended Test Execution Flow:

```bash
python test_variable_stops.py --tickers AMD AMZN PLTR TSLA DDOG NET ORCL GE LLY DELL --period 2y
```

**For each ticker:**

1. ✅ `get_smart_data(ticker, period='2y')` - Works correctly
   - Could use MASSIVE cache
   - Returns good 2y data

2. ❌ `calculate_all_indicators(df, ticker)` - Corrupts cache
   - **Ignores** the df with 2y data
   - Calls `analyze_ticker(ticker, period='1y', data_source='yfinance')`
   - Forces yfinance download (wrong period, wrong source)
   - Overwrites cache with partial/failed data

3. 💥 **Result:** Cache corruption
   - AMZN: Download failed/timed out → 5-6 days cached
   - ORCL: Download failed/timed out → 5-6 days cached
   - VRT: Not in test but was affected (possibly earlier run)

## Affected Caches

| Ticker | Before | After | Status |
|--------|--------|-------|--------|
| VRT | ~500 days | 6 days | ❌ Corrupted |
| ORCL | ~500 days | 5-6 days | ❌ Corrupted |
| AMZN | ~500 days | 5-6 days | ❌ Corrupted |

**Detected by:** Analysis showing only 6 days for VRT when 12-month charts exist in results_volume/

## Why Production Code is Safe

✅ **No production code was modified**
✅ **All corruption from test_variable_stops.py only**
✅ **MASSIVE cache untouched** (read-only, has data through Nov 14)
✅ **data_manager.py works correctly** (respects cache priorities)

## The Fix

### Solution 1: Remove analyze_ticker() Call (RECOMMENDED)

Replace `calculate_all_indicators()` to calculate indicators directly:

```python
def calculate_all_indicators(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """
    Calculate indicators directly on provided DataFrame.
    Does NOT re-download data.
    """
    # Import necessary modules
    import volume_features
    import swing_structure
    import signal_generator
    
    # Calculate indicators directly (like vol_analysis.py does)
    df['CMF_20'] = volume_features.calculate_cmf(df, period=20)
    df['ATR_Z'] = indicators.calculate_zscore(df['ATR20'], window=20) if 'ATR20' in df.columns else 0
    # ... etc for all required indicators
    
    return df
```

### Solution 2: Pass Correct Parameters (Less Safe)

```python
def calculate_all_indicators(df: pd.DataFrame, ticker: str, period: str = '1y', 
                             data_source: str = 'yfinance') -> pd.DataFrame:
    result_df = vol_analysis.analyze_ticker(
        ticker=ticker, 
        period=period,  # Use passed parameter
        data_source=data_source,  # Use passed parameter
        # ...
    )
    return result_df
```

**Problem:** Still re-downloads data unnecessarily, just with correct parameters.

## Cache Restoration Procedure

### Using MASSIVE Cache (Recommended)

MASSIVE cache has complete data through 2025-11-14. Restore corrupted tickers:

```bash
# 1. Clear corrupted caches
rm data_cache/VRT_data.csv
rm data_cache/ORCL_data.csv  
rm data_cache/AMZN_data.csv

# 2. Let system rebuild from MASSIVE on next access
python vol_analysis.py VRT --data-source massive -p 24mo
python vol_analysis.py ORCL --data-source massive -p 24mo
python vol_analysis.py AMZN --data-source massive -p 24mo
```

This will:
- Use MASSIVE cache as source
- Build proper yfinance cache
- Preserve all data through Nov 14

### Manual Restoration (Alternative)

Use `migrate_cache.py` if it supports MASSIVE→yfinance migration.

## Prevention

### Immediate Actions:

1. **Fix test_variable_stops.py** with Solution 1 (remove analyze_ticker call)
2. **Add warning comment** at top of test script about cache risks
3. **Restore corrupted caches** from MASSIVE

### Long-term Prevention:

1. **Add cache protection:** Read-only mode for test scripts
2. **Separate test caches:** Use `data_cache_test/` for testing
3. **Cache validation:** Add checksums or row counts to detect corruption
4. **Better error handling:** Catch partial downloads before cache write

## Testing Required

After fix:

1. Test with MASSIVE data source:
```bash
python test_variable_stops.py --tickers AAPL MSFT --period 2y --data-source massive
```

2. Verify no cache modifications occur

3. Compare results to original 371-trade test

## Risk Assessment

**Immediate Risk:** LOW
- Only 3 caches affected
- MASSIVE cache intact (source of truth)
- Easy to restore

**Future Risk:** HIGH if not fixed
- Could corrupt more caches
- Test script will be used again
- Other users might encounter same issue

## Recommendation

**Priority: HIGH**

1. Implement Solution 1 (remove analyze_ticker call) immediately
2. Restore 3 corrupted caches from MASSIVE
3. Add safeguards to prevent future test-related cache corruption
4. Document "testing best practices" to avoid similar issues

---

**Next Actions:**
- Fix test_variable_stops.py
- Restore VRT, ORCL, AMZN caches
- Test with fixed code
- Continue with variable stop implementation
