# Implementation Plan: Fix MA_Crossdown Parameter Propagation in Batch Backtest

## [Overview]
Fix parameter propagation failure preventing MA_Crossdown exit signals from working in batch backtests.

This is a classic multi-entry-point parameter propagation bug documented in `.clinerules/parameter-propagation.md`. The MA_Crossdown feature works correctly in single-ticker mode (`vol_analysis.py`) because it passes the config dict through the entire chain. However, `batch_backtest.py` loads the config but never passes it to the analysis pipeline, causing MA_Crossdown signals to be disabled (all False values).

The fix threads the config parameter through the batch backtest path to match the working single-ticker pattern. This is a minimal 3-location change that maintains backward compatibility while enabling all config-based features (MA_Crossdown, signal thresholds, etc.) to work in batch mode.

## [Types]
No new types required - using existing dict type for config parameter.

The config dict structure is already defined and validated by `ConfigLoader`:
```python
config: Dict[str, Any] = {
    'config_name': str,
    'risk_management': {...},
    'signal_thresholds': {...},
    'exit_signal_params': {
        'ma_crossdown': {
            'enabled': bool,
            'ma_period': int,
            'confirmation_days': int,
            'buffer_pct': float
        }
    },
    'regime_filters': {...},
    'profit_management': {...},
    'backtest': {...}
}
```

## [Files]
Modify one existing file to add config parameter to the batch backtest pipeline.

**Files to Modify:**
- `batch_backtest.py` (3 changes in 3 locations):
  1. Line 36: Add `config` parameter to `run_batch_backtest()` function signature
  2. Line 161: Add `config=config` to `prepare_analysis_dataframe()` call
  3. Line 1143: Add `config=config_dict` to `run_batch_backtest()` call in `main()`

**No files to create or delete.**

## [Functions]
Modify one function signature and update two function calls.

**Modified Functions:**

1. **`run_batch_backtest()` in `batch_backtest.py` (line 36)**
   - Current signature:
     ```python
     def run_batch_backtest(ticker_file: str, period: str = '12mo',
                           start_date: str = None, end_date: str = None,
                           output_dir: str = 'backtest_results',
                           risk_managed: bool = True,
                           account_value: float = 100000,
                           risk_pct: float = 0.75,
                           stop_strategy: str = DEFAULT_STOP_STRATEGY,
                           time_stop_bars: int = DEFAULT_TIME_STOP_BARS,
                           save_individual_reports: bool = True) -> Dict:
     ```
   - New signature (add config parameter):
     ```python
     def run_batch_backtest(ticker_file: str, period: str = '12mo',
                           start_date: str = None, end_date: str = None,
                           output_dir: str = 'backtest_results',
                           risk_managed: bool = True,
                           account_value: float = 100000,
                           risk_pct: float = 0.75,
                           stop_strategy: str = DEFAULT_STOP_STRATEGY,
                           time_stop_bars: int = DEFAULT_TIME_STOP_BARS,
                           save_individual_reports: bool = True,
                           config: dict = None) -> Dict:
     ```
   - Change: Add `config: dict = None` as final parameter (maintains backward compatibility)
   - Also update docstring to document the new parameter

2. **`prepare_analysis_dataframe()` call in `run_batch_backtest()` (line 161)**
   - Current call:
     ```python
     df = prepare_analysis_dataframe(
         ticker=ticker,
         period=fetch_period,
         data_source='yfinance',
         force_refresh=False,
         verbose=False
     )
     ```
   - New call:
     ```python
     df = prepare_analysis_dataframe(
         ticker=ticker,
         period=fetch_period,
         data_source='yfinance',
         force_refresh=False,
         verbose=False,
         config=config
     )
     ```
   - Change: Add `config=config` parameter to pass config through

3. **`run_batch_backtest()` call in `main()` (line 1143)**
   - Current call (approximately line 1143):
     ```python
     results = run_batch_backtest(
         ticker_file=args.ticker_file,
         period=args.period,
         start_date=args.start_date,
         end_date=args.end_date,
         output_dir=args.output_dir,
         risk_managed=args.risk_managed,
         account_value=args.account_value,
         risk_pct=args.risk_pct,
         stop_strategy=args.stop_strategy,
         time_stop_bars=args.time_stop_bars,
         save_individual_reports=args.save_individual_reports
     )
     ```
   - New call:
     ```python
     results = run_batch_backtest(
         ticker_file=args.ticker_file,
         period=args.period,
         start_date=args.start_date,
         end_date=args.end_date,
         output_dir=args.output_dir,
         risk_managed=args.risk_managed,
         account_value=args.account_value,
         risk_pct=args.risk_pct,
         stop_strategy=args.stop_strategy,
         time_stop_bars=args.time_stop_bars,
         save_individual_reports=args.save_individual_reports,
         config=config_dict
     )
     ```
   - Change: Add `config=config_dict` parameter (config_dict already exists at line 1109)
   - Note: The variable name is `config_dict` in main(), not `config`

**No functions to create or remove.**

## [Classes]
No class modifications required.

All necessary classes already exist:
- `ConfigLoader` in `config_loader.py` (already working)
- Risk management classes (already working)
- Signal generation classes (already working)

## [Dependencies]
No dependency changes required.

All required imports already exist in `batch_backtest.py`:
- `from config_loader import load_config, ConfigValidationError` (line 30)
- `from analysis_service import prepare_analysis_dataframe` (line 26)

## [Testing]
Verify fix with both single-ticker and batch paths to ensure parameter propagation works.

**Test Strategy:**

1. **Verify Single-Ticker Path Still Works (Baseline)**
   ```bash
   python vol_analysis.py AAPL --period 6mo --config configs/conservative_config.yaml
   ```
   - Expected: MA_Crossdown column present with some True values
   - Check: Count signals in output

2. **Test Batch Path With Fix**
   ```bash
   # Create small test file
   echo "AAPL" > test_ma_crossdown.txt
   
   # Run batch backtest
   python batch_backtest.py \
     -f test_ma_crossdown.txt \
     -c configs/conservative_config.yaml \
     --start-date 2024-06-07 \
     --end-date 2025-12-05 \
     --no-individual-reports
   ```
   - Expected: MA_Crossdown exit signals appear in LOG_FILE CSV
   - Check: Column MA_Crossdown exists and has some True values
   - Verify: Exit types include signal-based exits

3. **Cross-Path Validation (Critical Test)**
   ```bash
   # Run same ticker through both paths
   python vol_analysis.py AAPL --period 6mo --config configs/conservative_config.yaml > single.txt
   
   echo "AAPL" > single_ticker.txt
   python batch_backtest.py -f single_ticker.txt -c configs/conservative_config.yaml \
     --start-date 2024-06-07 --end-date 2025-12-05 --no-individual-reports
   
   # Compare signal counts - should be identical or very close
   grep "MA_Crossdown" single.txt
   # Check LOG_FILE CSV for MA_Crossdown column
   ```
   - Expected: Both paths generate similar MA_Crossdown signal counts
   - If different: Parameter propagation still has issues

4. **Test Without Config (Backward Compatibility)**
   ```bash
   python batch_backtest.py -f test_ma_crossdown.txt --period 6mo
   ```
   - Expected: Runs without errors (uses defaults)
   - MA_Crossdown column created with all False (no config provided)

5. **Verify Exit Signal Distribution**
   - Open generated LOG_FILE CSV
   - Check `exit_type` column for variety of exit types
   - Before fix: No SIGNAL_EXIT types (all TIME_STOP, HARD_STOP, etc.)
   - After fix: Some SIGNAL_EXIT types should appear when MA_Crossdown triggers

**Test Files:**
- Use existing test infrastructure
- No new test files needed (this is a bug fix, not new feature)
- Can add regression test later to prevent recurrence

## [Implementation Order]
Implement changes in specific order to ensure safe testing at each step.

1. **Modify `run_batch_backtest()` signature** (line 36 in batch_backtest.py)
   - Add `config: dict = None` parameter
   - Update docstring to document config parameter
   - Rationale: Add parameter first so subsequent calls can use it

2. **Update `prepare_analysis_dataframe()` call** (line 161 in batch_backtest.py)
   - Add `config=config` to the call
   - Rationale: Thread parameter through to analysis service

3. **Update `run_batch_backtest()` call in main()** (line 1143 in batch_backtest.py)
   - Add `config=config_dict` to the call
   - Rationale: Complete the parameter chain from main() to analysis

4. **Test with single ticker batch** (validation)
   - Run batch backtest with one ticker
   - Verify MA_Crossdown signals appear
   - Compare to single-ticker mode results

5. **Test with full batch** (final validation)
   - Run with full ticker list (e.g., nasdaq100.txt)
   - Verify results show MA_Crossdown exit signals
   - Check LOG_FILE CSV for signal distribution

6. **Update CODE_MAP.txt documentation** (if successful)
   - Document that this parameter propagation bug was fixed
   - Note the importance of testing BOTH entry points when adding features
   - Reference `.clinerules/parameter-propagation.md`

**Total Implementation Time: ~10 minutes**
- Code changes: 3 lines
- Testing: 5-10 minutes
- Documentation: 2-3 minutes

**Risk Level: Low**
- Backward compatible (config defaults to None)
- Minimal code changes
- Follows established pattern from vol_analysis.py

**Success Criteria:**
- Batch backtests show MA_Crossdown exit signals in LOG_FILE CSV
- Exit type distribution includes SIGNAL_EXIT types
- Single-ticker and batch paths produce consistent results for same ticker
- No regression in tests without config file
