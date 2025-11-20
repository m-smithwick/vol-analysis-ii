# Data Architecture Fix - Task List

## Problem Summary
- Regime filter columns are empty due to yfinance API failures
- Batch backtest only shows 2 months instead of 24 months
- Multiple code paths for data loading causing "whack-a-mole" fixes
- get_smart_data() should be the ONLY data loading function (cache-only)
- Scripts should fail gracefully with clear missing data messages

## Task Order (No Big Bang Approach)

### PHASE 1: Assessment and Documentation
- [ ] **Task 1.1**: Document current get_smart_data() behavior
  - File: `data_manager.py`
  - Action: Review what yfinance fallbacks currently exist
  - Output: List exact conditions that trigger yfinance calls

- [ ] **Task 1.2**: Document regime_filter.py dependencies
  - File: `regime_filter.py` 
  - Action: Map all data loading paths in load_benchmark_data()
  - Output: List where yfinance calls happen

- [ ] **Task 1.3**: Create data loading audit
  - Files: Search results from earlier (88 yfinance references)
  - Action: Categorize each yfinance usage (critical vs removable)
  - Output: Priority list of files to fix

### PHASE 2: Core Architecture Fix
- [ ] **Task 2.1**: Make get_smart_data() cache-only
  - File: `data_manager.py`
  - Action: Remove all yfinance fallbacks from get_smart_data()
  - Test: Verify it only returns cached data or raises clear error
  - Rollback plan: Git commit before changes

- [ ] **Task 2.2**: Add missing data detection to get_smart_data()
  - File: `data_manager.py`
  - Action: Replace yfinance calls with helpful error messages
  - Error format: "Cache missing for {ticker}. Run: python populate_cache.py {ticker} --period {period}"
  - Test: Verify clear error messages appear

### PHASE 3: Fix regime_filter.py (High Priority)
- [ ] **Task 3.1**: Remove load_benchmark_data() custom logic
  - File: `regime_filter.py`
  - Action: Replace load_benchmark_data() internals to use get_smart_data()
  - Keep: Same function signature for compatibility
  - Test: Verify regime calculation works with cached data only

- [ ] **Task 3.2**: Fix regime calculation error handling
  - File: `regime_filter.py`
  - Action: When data missing, return clear error instead of empty values
  - Change: Don't default to None/empty for regime columns
  - Test: Verify regime columns have True/False values or clear error

### PHASE 4: Module-by-Module Cleanup
- [ ] **Task 4.1**: Fix analysis_service.py
  - File: `analysis_service.py`
  - Action: Ensure prepare_analysis_dataframe() only uses get_smart_data()
  - Test: Verify 24mo period parameter works correctly

- [ ] **Task 4.2**: Clean up duplicate convert functions
  - Files: `populate_cache_bulk.py`, `tests/test_massive_bulk_single_day.py`
  - Action: Remove duplicate convert_to_yfinance_format() functions
  - Keep: Only the one in `massive_data_provider.py`
  - Test: Verify populate_cache_bulk.py still works

- [ ] **Task 4.3**: Fix test files
  - Files: `tests/test_*.py` files with direct yf.download() calls
  - Action: Replace direct yfinance calls with get_smart_data() calls
  - Test: Verify tests still pass

### PHASE 5: Error Handling Improvements
- [ ] **Task 5.1**: Add batch operation detection
  - Files: `batch_backtest.py`, `data_manager.py`
  - Action: Add parameter to indicate batch mode (no auto-downloads)
  - Test: Verify batch operations are strictly cache-only

- [ ] **Task 5.2**: Improve error messages in batch_backtest.py
  - File: `batch_backtest.py`
  - Action: Catch missing data errors and show populate commands
  - Format: "Missing data for SPY. Run: python populate_cache.py SPY --period 24mo"
  - Test: Verify helpful error messages appear

### PHASE 6: Validation and Testing
- [ ] **Task 6.1**: Test regime filter with known good data
  - Action: Run debug_regime_filter.py on ticker with 24mo cache
  - Expected: Regime columns should have True/False values
  - Test: Verify no yfinance calls are made

- [ ] **Task 6.2**: Test batch_backtest with cmb.txt
  - Action: Run python batch_backtest.py -f cmb.txt --period 24mo
  - Expected: Either full 24mo of trades OR clear missing data error
  - Test: Verify no silent failures

- [ ] **Task 6.3**: Verify CSV export includes regime data
  - Action: Check PORTFOLIO_TRADE_LOG CSV has regime columns with data
  - Expected: market_regime_ok, sector_regime_ok, overall_regime_ok with True/False
  - Test: No more empty regime columns

### PHASE 7: Documentation and Cleanup
- [ ] **Task 7.1**: Update architecture documentation
  - File: Create/update data loading architecture docs
  - Action: Document the cache-only approach and populate workflow
  - Include: Examples of error messages and how to fix them

- [ ] **Task 7.2**: Remove obsolete code
  - Action: Delete unused yfinance imports and functions
  - Files: Clean up after all modules are converted
  - Test: Verify system still works after cleanup

## Success Criteria
1. ✅ get_smart_data() is cache-only, no yfinance fallbacks
2. ✅ regime filter columns have actual True/False data
3. ✅ batch_backtest shows full 24mo of trades (when data available)
4. ✅ Clear error messages when data is missing
5. ✅ No silent failures or empty columns
6. ✅ All modules use get_smart_data() for data access

## Rollback Plan
- Each task should be a separate git commit
- If any task breaks the system, revert that commit
- Test after each phase before proceeding to next

## Priority Order
**Critical Path**: Tasks 2.1 → 3.1 → 3.2 → 6.1 → 6.2
These tasks directly fix the reported issues.

**Secondary**: Other tasks improve architecture and prevent future issues.

---
*Created: 2025-11-19 19:12*
*Last Updated: 2025-11-19 19:12*
