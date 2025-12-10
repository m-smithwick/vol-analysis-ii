# Signal Filtering Bug Fix Summary

**Date**: December 9, 2025  
**Issue**: Configuration signal filtering was not working - hard-coded signal lists ignored YAML config  
**Status**: ✅ FIXED

## 🚨 The Problem

### Critical Bug: Configuration Ignored
The system was configured to use only specific signals via `enabled_entry_signals` and `enabled_exit_signals` in YAML config files, but the backtest code was ignoring this and using ALL signals.

### Evidence of the Bug (NBIX Example)
**Conservative Config Says:**
```yaml
enabled_entry_signals:
  - "moderate_buy_pullback"  # ONLY this signal
```

**But Backtest Actually Used:**
- 5/7 trades used `Stealth_Accumulation` (deprecated signal)
- 2/7 trades used `Moderate_Buy` (intended signal)

### Root Cause
Hard-coded signal lists in `backtest.py`:
```python
# WRONG: Hard-coded lists ignored config
entry_signals = ['Strong_Buy', 'Moderate_Buy', 'Stealth_Accumulation', 
                 'Confluence_Signal', 'Volume_Breakout']
```

## 🔧 The Solution

### 1. Created Signal Name Mapping (`signal_config_utils.py`)
```python
CONFIG_TO_DATAFRAME_SIGNAL_MAP = {
    'moderate_buy_pullback': 'Moderate_Buy',
    'stealth_accumulation': 'Stealth_Accumulation',
    # ... etc
}

def get_enabled_signals_from_config(config):
    """Extract enabled signals from config and convert to DataFrame column names"""
    # Returns: {'entry': ['Moderate_Buy'], 'exit': ['Profit_Taking', ...]}
```

### 2. Updated Backtest Functions
**Modified `run_risk_managed_backtest()` in `backtest.py`:**
```python
def run_risk_managed_backtest(..., config: Optional[Dict] = None, ...):
    if config:
        from signal_config_utils import get_enabled_signals_from_config, validate_enabled_signals
        enabled_signals = get_enabled_signals_from_config(config)
        entry_signals = enabled_signals['entry']    # ✅ Config-driven
        exit_signals = enabled_signals['exit']      # ✅ Config-driven
    else:
        # Fallback to all signals (legacy behavior)
```

**Modified `batch_backtest.py`:**
```python
# Added config parameter to backtest call
risk_result = backtest.run_risk_managed_backtest(
    df=df,
    ticker=ticker,
    config=config,  # ✅ ADDED THIS
    # ... other params
)
```

## ✅ Verification Results

### Test Case: NBIX with Conservative Config
**Command:** `python batch_backtest.py -f test_nbix.txt -p 24mo -c configs/conservative_config.yaml`

**Before Fix:**
- 7 trades total
- 5 used `Stealth_Accumulation` (deprecated)
- 2 used `Moderate_Buy` (intended)
- Config completely ignored

**After Fix:**
- 3 trades total  
- **ALL 3 use `Moderate_Buy`** ✅
- **ZERO use `Stealth_Accumulation`** ✅
- Config filtering working: `Entry Signals: ['Moderate_Buy']`

### CSV Evidence
```csv
entry_signals_str,primary_signal
Moderate_Buy,Moderate_Buy      # ✅ Trade 1
Moderate_Buy,Moderate_Buy      # ✅ Trade 2  
Moderate_Buy,Moderate_Buy      # ✅ Trade 3
```

## 🎯 Impact

### Performance Accuracy
- **Before**: Using failed signals (22.7% win rate for Stealth_Accumulation)
- **After**: Using validated signals (59.6% win rate for Moderate_Buy)
- **Result**: Backtest results now reflect actual configuration intent

### Configuration Comparisons
All previous config comparisons (conservative vs base vs aggressive) were **INVALID** because they were using identical signal sets despite different configs.

### Need for Re-Analysis
- ✅ Fix implemented and verified
- 🔄 All config comparisons must be re-run with corrected logic
- 📊 New results will show TRUE differences between configurations

## 🔍 Files Modified

1. **`signal_config_utils.py`** (NEW) - Signal name mapping utilities
2. **`backtest.py`** - Added config parameter to `run_risk_managed_backtest()`
3. **`batch_backtest.py`** - Pass config to backtest functions

## 📋 Next Steps

1. **Re-run all configuration comparisons** with corrected signal filtering
2. **Update documentation** to reflect proper config-driven behavior  
3. **Validate other entry points** (vol_analysis.py, etc.) use config properly
4. **Add tests** to prevent regression of this critical bug

## 🛡️ Prevention

This bug was caused by **parameter propagation failure** - config was defined but not threaded through to execution layer. See `.clinerules/parameter-propagation.md` for prevention guidelines.

**Key Lesson**: In multi-entry-point systems, adding a parameter to one path means adding it to ALL paths.
