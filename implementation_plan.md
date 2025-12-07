# Implementation Plan: MA Crossdown Exit Signal

## [Overview]

Add a configurable moving average crossdown exit signal to the conservative trading profile, enabling trend-following discipline when price breaks below a specified moving average (default 48-day to avoid crowd behavior at 50-day).

This implementation adds a new exit signal type that complements the existing volume/momentum-based exits (Momentum Exhaustion, Profit Taking, Distribution Warning) by introducing trend structure confirmation. The signal will be fully configurable through the YAML config system, allowing empirical testing of different MA periods, confirmation requirements, and buffer zones without code modifications.

The implementation follows the established patterns in the codebase: signal generation in `signal_generator.py`, configuration validation in `config_loader.py`, and integration through the existing signal threshold system. The configurable approach enables testing both conservative (2-day confirmation) and aggressive (1-day) exit strategies while maintaining backward compatibility with existing configurations.

## [Types]

No new type definitions required.

The implementation uses existing Python types and data structures:
- `pd.Series` for signal boolean flags (existing pattern)
- `pd.DataFrame` for price/indicator data (existing pattern)
- `dict` for exit_params configuration (existing pattern in risk_manager.py)
- Standard Python types: `int`, `float`, `bool` for parameters

Configuration structure (YAML):
```yaml
exit_signal_params:
  ma_crossdown:
    enabled: bool          # Whether signal is active
    ma_period: int         # MA period (e.g., 48, 50, 60)
    confirmation_days: int # Days below MA required (1=immediate, 2=conservative)
    buffer_pct: float      # Optional buffer to reduce whipsaws (0.0 = no buffer)
```

## [Files]

Modifications required to integrate MA crossdown exit signal into configuration and signal generation system.

**Files to Modify:**

1. **`signal_generator.py`** 
   - Add `generate_ma_crossdown_signals()` function (new)
   - Modify `generate_all_exit_signals()` to accept `exit_params` parameter
   - Add MA crossdown signal to exit signal list

2. **`configs/conservative_config.yaml`**
   - Add `exit_signal_params` section with MA crossdown configuration
   - Add `ma_crossdown` to `signal_thresholds.exit` dictionary  
   - Add `ma_crossdown` to `enabled_exit_signals` list

3. **`config_loader.py`**
   - Add validation for optional `exit_signal_params` section
   - Add `get_exit_signal_params()` method to extract parameters

4. **`vol_analysis.py`**
   - Extract exit_params from config
   - Pass exit_params to `generate_all_exit_signals()` call

5. **`backtest.py`**
   - Add `ma_crossdown` to exit_signal_keys list in relevant functions
   - Ensure signal is included in backtest analysis

6. **`CODE_MAP.txt`**
   - Update signal_generator.py description to mention MA crossdown
   - Update conservative_config.yaml description

7. **`configs/README.md`**
   - Document new exit_signal_params section
   - Provide usage examples

**No New Files Created**

**No Files Deleted**

## [Functions]

Modifications to signal generation and configuration loading to support parameterized exit signals.

**New Functions:**

1. **`generate_ma_crossdown_signals()` in `signal_generator.py`**
   ```python
   def generate_ma_crossdown_signals(
       df: pd.DataFrame,
       ma_period: int = 50,
       confirmation_days: int = 1,
       buffer_pct: float = 0.0
   ) -> pd.Series
   ```
   - Purpose: Detect when price crosses below moving average
   - Parameters: MA period, confirmation requirement, buffer zone
   - Returns: Boolean Series indicating crossdown signals
   - Logic: Calculate MA, detect crossdown with optional confirmation
   - Location: Add after `generate_stop_loss_signals()` in signal_generator.py

**Modified Functions:**

1. **`generate_all_exit_signals()` in `signal_generator.py`**
   - Current signature: `def generate_all_exit_signals(df: pd.DataFrame) -> pd.DataFrame`
   - New signature: `def generate_all_exit_signals(df: pd.DataFrame, exit_params: dict = None) -> pd.DataFrame`
   - Changes:
     - Add optional `exit_params` parameter
     - Extract MA crossdown parameters from exit_params if provided
     - Call `generate_ma_crossdown_signals()` with extracted parameters
     - Add 'MA_Crossdown' column to returned DataFrame

2. **`get_exit_signal_params()` in `config_loader.py`** (NEW METHOD)
   - Signature: `def get_exit_signal_params(self) -> Dict[str, Any]`
   - Purpose: Extract exit signal parameters from config
   - Returns: Dict with exit signal params, or empty dict if not present
   - Location: Add after `get_regime_config()` method

3. **Signal generation calls in `vol_analysis.py`**
   - Locate calls to `generate_all_exit_signals(df)`
   - Modify to: `generate_all_exit_signals(df, exit_params=exit_params)`
   - Extract exit_params from config loader before calling

**No Functions Removed**

## [Classes]

Modifications to ConfigLoader class to validate and extract exit signal parameters.

**Modified Classes:**

1. **`ConfigLoader` in `config_loader.py`**
   - File: `config_loader.py`
   - Changes:
     - Add optional `exit_signal_params` to config structure (not required for backward compatibility)
     - Add validation method `_validate_exit_signal_params()` (optional validation)
     - Add accessor method `get_exit_signal_params()` to extract params
   - Methods added:
     - `get_exit_signal_params(self) -> Dict[str, Any]`: Returns exit signal params or empty dict
   - Methods modified:
     - `_validate_structure()`: Add exit_signal_params to optional sections (not required)

**No New Classes**

**No Classes Removed**

## [Dependencies]

No new external dependencies required. Implementation uses existing project dependencies.

**Existing Dependencies Used:**
- `pandas` - Already in requirements.txt (DataFrame operations, rolling means)
- `numpy` - Already in requirements.txt (numerical operations)
- `yaml` - Already in requirements.txt (config file loading)

**No New Dependencies Added**

**No Version Changes Required**

## [Testing]

Comprehensive testing strategy to validate MA crossdown exit signal implementation and integration.

**Test Files Required:**

1. **Unit Tests** (create new test file)
   - `tests/test_ma_crossdown_exit.py` (NEW)
   - Test `generate_ma_crossdown_signals()` function:
     - Test simple crossdown detection (1-day)
     - Test 2-day confirmation requirement
     - Test buffer zone functionality
     - Test edge cases (all NaN, all above MA, all below MA)
     - Test different MA periods (20, 48, 50, 60)

2. **Integration Tests** (modify existing test files)
   - `tests/test_conservative_config.py` (NEW or add to existing config tests)
   - Test config loading with exit_signal_params
   - Test backward compatibility (configs without exit_signal_params)
   - Validate parameter extraction

3. **Manual Testing** (documented test cases)
   - Single ticker test: `python vol_analysis.py AAPL --period 12mo`
   - Verify MA crossdown signals appear in results
   - Compare with/without MA crossdown enabled
   - Historical backtest: `python batch_backtest.py -p 12mo -f ticker_lists/short.txt`
   - Verify exit type distribution includes MA crossdowns

**Existing Tests to Modify:**

- None (new feature, shouldn't break existing tests)
- Run full test suite to ensure no regressions: `pytest tests/`

**Validation Strategy:**

1. **Correctness Validation:**
   - Compare MA calculations with manual calculations
   - Verify crossdown detection matches expected behavior
   - Test confirmation logic with known data sequences

2. **Integration Validation:**
   - Run batch backtest comparing results with/without MA crossdown
   - Verify exit type attribution is correct
   - Check that MA crossdown doesn't interfere with other exit signals

3. **Performance Validation:**
   - Compare execution time with/without MA crossdown (should be negligible)
   - Verify no memory leaks with large datasets

## [Implementation Order]

Sequential implementation steps to minimize integration conflicts and enable incremental testing.

**Step-by-step Implementation:**

1. **Add MA crossdown signal generation function** (`signal_generator.py`)
   - Implement `generate_ma_crossdown_signals()` 
   - Add comprehensive docstring with examples
   - Test function in isolation with sample data

2. **Update signal generation to accept parameters** (`signal_generator.py`)
   - Modify `generate_all_exit_signals()` signature
   - Add exit_params parameter handling
   - Call MA crossdown function with extracted params
   - Maintain backward compatibility (exit_params=None)

3. **Add configuration sections** (`configs/conservative_config.yaml`)
   - Add `exit_signal_params.ma_crossdown` section
   - Add `ma_crossdown` to exit thresholds (value: 5.0)
   - Add `ma_crossdown` to enabled_exit_signals list

4. **Update configuration loader** (`config_loader.py`)
   - Add `get_exit_signal_params()` method
   - Add optional validation for exit_signal_params (if present)
   - Test config loading with new sections

5. **Integrate into vol_analysis.py**
   - Extract exit_params from config using `get_exit_signal_params()`
   - Pass exit_params to `generate_all_exit_signals()`
   - Test with single ticker run

6. **Update backtest integration** (`backtest.py`)
   - Add 'MA_Crossdown' or 'ma_crossdown' to exit_signals list
   - Verify signal appears in backtest reports

7. **Test implementation**
   - Run unit tests (if created)
   - Run single ticker test: `python vol_analysis.py AAPL --period 12mo`
   - Run batch backtest: `python batch_backtest.py -p 12mo -f ticker_lists/short.txt`
   - Compare results with/without MA crossdown enabled

8. **Documentation updates**
   - Update `CODE_MAP.txt` with MA crossdown signal description
   - Update `configs/README.md` with exit_signal_params documentation
   - Add usage examples to config README

9. **Final validation**
   - Run full test suite: `pytest tests/`
   - Run batch backtest on larger ticker list
   - Review and commit changes

**Dependencies Between Steps:**
- Step 2 depends on Step 1 (function must exist before calling it)
- Step 5 depends on Steps 2-4 (all components must be ready)
- Step 6 depends on Step 5 (signal must be generated before backtesting)
- Steps 7-9 depend on Steps 1-6 (implementation must be complete)

**Estimated Time:** 2-3 hours total
- Steps 1-2: 30 minutes (signal generation)
- Steps 3-4: 20 minutes (configuration)
- Step 5: 15 minutes (integration)
- Step 6: 10 minutes (backtest update)
- Steps 7-9: 45-90 minutes (testing and documentation)

---

## Implementation Notes

**Key Design Decisions:**

1. **Configurable by default**: Enables testing different strategies without code changes
2. **Backward compatible**: Configs without exit_signal_params still work (exit_params=None)
3. **Consistent patterns**: Follows existing signal generation patterns in codebase
4. **48-day default**: Avoids crowd behavior at exact 50-day MA
5. **1-day confirmation default**: Faster exits, can be increased to 2 days for conservative approach

**Integration Points:**

- Signal generation: `signal_generator.generate_all_exit_signals()`
- Configuration: `config_loader.ConfigLoader.get_exit_signal_params()`
- Vol analysis: Pass exit_params to signal generation
- Backtest: Include ma_crossdown in exit signal lists
- Risk manager: No changes needed (uses exit signals as-is)

**Testing Priority:**

1. High: Unit test signal generation function
2. High: Integration test with vol_analysis.py
3. Medium: Batch backtest comparison
4. Low: Performance testing (MA calc is fast)

**Future Enhancements:**

- Add to other config profiles (balanced, aggressive)
- Test exponential moving average (EMA) variant
- Add to exit strategy comparison reports
- Consider multiple MA periods (e.g., 20/50 double crossdown)
