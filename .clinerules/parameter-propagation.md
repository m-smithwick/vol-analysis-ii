# Parameter Propagation Rule

## The Problem

When adding configurable features or parameters to a multi-entry-point system, **ALL entry points must propagate the parameters**. Failure to do so results in silent failures where code executes successfully but uses default/fallback behavior.

---

## Real-World Incident: MA_Crossdown Exit Signal (Dec 2025)

### What Happened

Added configurable MA_Crossdown exit signal with parameters in `configs/conservative_config.yaml`:
```yaml
exit_signal_params:
  ma_crossdown:
    enabled: true
    ma_period: 48
    confirmation_days: 1
    buffer_pct: 0.0
```

**Single-Ticker Path (✅ Worked)**:
- `vol_analysis.py` → loads config → passes to `analyze_ticker()` → `analysis_service.py` → `signal_generator.py`
- MA_Crossdown signals generated correctly (20 signals for AAPL 6mo)

**Batch Path (❌ Silent Failure)**:
- `vol_analysis.py --file` → `batch_processor.py` → `analyze_ticker()` WITHOUT config
- No config passed → `exit_signal_params` missing → MA_Crossdown column created with all False
- **Batch backtests produced identical results to pre-feature runs**
- No errors, no warnings - completely silent failure

### Why It Was Hard to Detect

1. **No Exceptions**: Code ran successfully in both paths
2. **Column Existed**: MA_Crossdown column was created (just always False)
3. **Test Coverage Gap**: Single-ticker tests passed, batch mode never tested
4. **Assumed Consistency**: Expected batch mode to behave like single-ticker mode
5. **No Cross-Path Validation**: Never compared single vs batch results

---

## The Rule: Parameter Propagation Checklist

When adding ANY configurable parameter or feature, you MUST verify:

### ✅ Phase 1: Identify All Entry Points

Document every way users can invoke your functionality:

**For This System**:
- [ ] `vol_analysis.py TICKER` (single ticker CLI)
- [ ] `vol_analysis.py --file` (batch processing CLI)
- [ ] `batch_backtest.py` (if exists - scripted batch runs)
- [ ] Direct function calls (if library usage supported)
- [ ] Programmatic imports (other scripts using modules)

**Action**: List all entry points at the START of feature work, not after.

### ✅ Phase 2: Thread Parameters Through

For EACH entry point, verify the complete chain:

1. **CLI/Entry Point**:
   - [ ] Added argument/parameter to entry point
   - [ ] Parameter properly parsed/extracted

2. **Intermediate Functions**:
   - [ ] Parameter added to function signature
   - [ ] Parameter passed to next function in chain
   - [ ] Default value specified (if applicable)

3. **Final Consumer**:
   - [ ] Parameter received by code that uses it
   - [ ] Behavior changes when parameter varies

**Critical**: If ANY link in chain is missing, feature silently fails.

### ✅ Phase 3: Test All Paths

For EACH entry point:

1. **Baseline Test** (feature disabled/default):
   ```bash
   # Run with default config
   python vol_analysis.py TICKER --period 6mo
   python vol_analysis.py --file short.txt --period 6mo
   ```

2. **Feature Test** (feature enabled/configured):
   ```bash
   # Run with feature config
   python vol_analysis.py TICKER --config configs/feature_config.yaml
   python vol_analysis.py --file short.txt --config configs/feature_config.yaml
   ```

3. **Results Verification**:
   - [ ] Feature behavior differs from baseline in BOTH paths
   - [ ] Results are consistent across paths (same ticker should behave same way)
   - [ ] Feature-specific output appears in logs/results

### ✅ Phase 4: Cross-Path Validation

**CRITICAL TEST**: Run same ticker through different entry points:

```bash
# Single ticker
python vol_analysis.py AAPL --period 6mo --config configs/conservative_config.yaml > single.txt

# Batch mode (with same ticker in file)
echo "AAPL" > test_single.txt
python vol_analysis.py --file test_single.txt --period 6mo --config configs/conservative_config.yaml

# Compare results - should be IDENTICAL
# If results differ, parameter propagation failed somewhere
```

**What to Compare**:
- Signal counts (entry/exit signals)
- Signal dates/locations
- Computed scores
- Position sizing
- Any feature-specific metrics

### ✅ Phase 5: Documentation

Update these files when adding configurable features:

1. **CODE_MAP.txt**:
   - Document new parameter flow
   - Note which entry points use it

2. **configs/README.md**:
   - Document new configuration section
   - Show example usage
   - Explain parameter effects

3. **Main README.md**:
   - Update CLI examples if needed
   - Show feature usage in different modes

---

## Anti-Patterns to Avoid

### ❌ Assuming All Paths Are Updated

**Don't**:
```python
# Updated single-ticker path with new param
def analyze_ticker(..., new_feature_param=None):
    ...

# FORGOT to update batch path!
def process_batch(...):
    df = analyze_ticker(...)  # Missing new_feature_param
```

**Do**:
```python
# Create checklist of all calling sites
# Update ALL of them in same commit
def process_batch(..., new_feature_param=None):
    df = analyze_ticker(..., new_feature_param=new_feature_param)
```

### ❌ Testing Only One Path

**Don't**:
```bash
# Only test single ticker
python vol_analysis.py AAPL --config new_config.yaml
# ✅ Works! Ship it!
```

**Do**:
```bash
# Test ALL paths
python vol_analysis.py AAPL --config new_config.yaml
python vol_analysis.py --file stocks.txt --config new_config.yaml
python batch_backtest.py --config new_config.yaml
# Verify feature works in ALL modes
```

### ❌ Silent Defaults

**Don't**:
```python
def generate_signals(df, feature_params=None):
    if feature_params is None:
        # Silently disable feature
        return df
```

**Do**:
```python
def generate_signals(df, feature_params=None):
    if feature_params is None:
        logger.warning("feature_params not provided, using defaults")
        feature_params = get_default_feature_params()
    # Or raise exception if config is required
```

### ❌ No Cross-Validation

**Don't**:
- Test single path, assume others work
- Only verify no exceptions thrown
- Skip result comparison across paths

**Do**:
- Test same input through different entry points
- Compare outputs for consistency
- Verify feature-specific behavior in all paths

---

## Detection: How to Catch Missing Propagation

### During Development

1. **Grep for Function Calls**:
   ```bash
   # Find all places function is called
   grep -n "analyze_ticker(" *.py
   # Verify each call includes new parameter
   ```

2. **Run Diagnostic Script**:
   ```python
   # test_feature_propagation.py
   def test_all_paths():
       # Test single ticker
       df1 = single_ticker_path("AAPL", config)
       
       # Test batch (one ticker)
       df2 = batch_path(["AAPL"], config)
       
       # Compare specific feature columns
       assert df1['Feature_Column'].equals(df2['Feature_Column'])
   ```

3. **Check Configuration Loading**:
   ```python
   # Add debug print when config loaded
   if config:
       logger.info(f"Config loaded: {config.keys()}")
       logger.info(f"Feature enabled: {config.get('feature_params')}")
   else:
       logger.warning("No config provided!")
   ```

### During Testing

1. **Before/After Comparison**:
   ```bash
   # Run batch BEFORE adding feature
   python vol_analysis.py --file test.txt > before.txt
   
   # Add feature, run batch AFTER
   python vol_analysis.py --file test.txt --config new.yaml > after.txt
   
   # Results should DIFFER if feature working
   diff before.txt after.txt
   ```

2. **Feature Flag Test**:
   ```yaml
   # Test with feature disabled
   feature:
     enabled: false
   
   # Test with feature enabled
   feature:
     enabled: true
   
   # Results should differ
   ```

---

## System-Specific Entry Points

### Current System Entry Points

1. **vol_analysis.py** (Main CLI):
   - Single ticker: `vol_analysis.py TICKER`
   - Batch mode: `vol_analysis.py --file`
   - Parameters flow: CLI → analyze_ticker() → prepare_analysis_dataframe()

2. **batch_processor.py** (Batch Processing):
   - Called by: vol_analysis.py --file
   - Calls: analyze_ticker() in loop
   - **CRITICAL**: Must receive and pass config parameter

3. **analysis_service.py** (Core Logic):
   - Called by: analyze_ticker()
   - Calls: signal_generator functions
   - **CRITICAL**: Extracts config sections and passes to generators

4. **Direct Module Usage**:
   - Scripts may import and call functions directly
   - Must document parameter requirements
   - Consider: validation/warnings for missing params

### Future Entry Points

When adding new entry points (REST API, scheduled jobs, etc.):
- [ ] Add to this list immediately
- [ ] Verify parameter propagation
- [ ] Add to testing checklist
- [ ] Document in CODE_MAP.txt

---

## Quick Reference Card

**Before committing new configurable feature**:

```
☐ Listed all entry points
☐ Updated all entry points to accept parameter
☐ Updated all intermediate functions
☐ Verified parameter reaches end consumer
☐ Tested with feature disabled
☐ Tested with feature enabled  
☐ Tested ALL entry points
☐ Compared results across paths (same input = same output)
☐ Updated documentation (CODE_MAP, configs/README, main README)
☐ Added diagnostic logging
☐ Created tests for each path
```

**If you check all boxes**: ✅ Safe to commit

**If you skip any box**: ❌ Risk of silent failure

---

## Summary

**The Golden Rule**: In a multi-entry-point system, adding a parameter to one path means adding it to ALL paths.

**Test Strategy**: Same input through different paths must produce same output.

**Detection**: If batch results are identical before/after feature addition, parameter propagation likely failed.

This is not optional. It's mandatory for maintaining system consistency.
