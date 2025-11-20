# Task 1.1 Analysis - Current get_smart_data() Behavior

## File Analyzed: data_manager.py

## yfinance Fallback Conditions Found

The `get_smart_data()` function currently has **5 different conditions** that trigger yfinance API calls:

### 1. Force Refresh Mode (Line ~140)
**Condition:** `force_refresh=True` parameter
**Code:**
```python
if force_refresh:
    logger.info(f"Force refresh enabled - downloading fresh data for {ticker} ({interval})")
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=True)
```
**Risk:** HIGH - Always bypasses cache

### 2. No Cache Exists (Line ~155) 
**Condition:** `cached_df is None` (no cache file found)
**Code:**
```python
if cached_df is None:
    # No cache exists - download full period
    logger.info(f"No cache found for {ticker} ({interval}) - downloading {period} data from Yahoo Finance")
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=True)
```
**Risk:** HIGH - This is what's failing for regime filter

### 3. Outdated Intraday Cache (Line ~175)
**Condition:** Intraday data (`interval != "1d"`) AND cache is >1 day old
**Code:**
```python
if days_behind > 1:
    # For intraday data more than a day old, simply refresh entirely
    logger.info(f"Intraday cache outdated ({days_behind}d old) - downloading fresh data for {ticker} ({interval})")
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=True)
```
**Risk:** MEDIUM - Only affects intraday data

### 4. Recent Data Update - Period Method (Line ~210)
**Condition:** Daily cache needs recent data updates
**Code:**
```python
# Try using period parameter instead of start/end dates
period_param = f"{min(days_to_download, 60)}d"
new_data = yf.download(ticker, period=period_param, interval=interval, auto_adjust=True)
```
**Risk:** HIGH - Attempts yfinance for cache updates

### 5. Recent Data Update - Date Method Fallback (Line ~218)  
**Condition:** When period-based download returns empty
**Code:**
```python
if new_data.empty:
    # Download from day after last cached date to today
    start_date = (cache_end_date + timedelta(days=1)).replace(tzinfo=None).strftime('%Y-%m-%d')
    new_data = yf.download(ticker, start=start_date, interval=interval, auto_adjust=True)
```
**Risk:** HIGH - Secondary fallback still uses yfinance

## Additional yfinance Usage

### Import Statement (Line ~8)
```python
import yfinance as yf
```

### Massive.com Fallback (Line ~80)
When `data_source="massive"` fails, it falls back to yfinance logic:
```python
logger.warning(f"No data from Massive.com for {ticker}, falling back to yfinance")
# ... continues to yfinance logic
```

## Problem Analysis

### Root Issue
The regime filter is failing because:
1. `load_benchmark_data()` in `regime_filter.py` calls `get_smart_data()` 
2. `get_smart_data()` tries to download SPY/sector ETF data when cache is incomplete
3. yfinance API returns errors (JSONDecodeError, YFTzMissingError)
4. This causes regime calculation to fail → empty regime columns

### Critical Path
For batch operations, we need **Condition #2** (No Cache Exists) to be eliminated because:
- It's the primary failure point for regime filter
- When SPY or sector ETF cache is missing/incomplete, it triggers yfinance
- yfinance failures cascade to empty regime data

## Next Steps (Task 2.1)
Replace all yfinance calls with cache-only logic and clear error messages when data is missing.

---
**Task 1.1 Status: ✅ COMPLETE**  
**Date:** 2025-11-19 19:15  
**Next Task:** 1.2 - Document regime_filter.py dependencies
