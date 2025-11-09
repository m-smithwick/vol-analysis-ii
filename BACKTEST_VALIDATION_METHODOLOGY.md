# Backtest Validation Methodology
## Systematic Approach to Validating Trading Strategy Results

**Purpose:** Provides a repeatable framework for validating backtest results and identifying common issues that make results appear better than they actually are.

**Created:** 2025-11-08  
**Use Case:** Run these validations whenever you generate new backtest results or modify your strategy

---

## Overview

Trading backtests often show unrealistically positive results due to:
- Lookahead bias (using future information)
- Outlier inflation (rare extreme trades skewing averages)
- Small sample sizes (not statistically significant)
- Period dependency (only works in specific market conditions)
- Cherry-picked results (showing best-case scenarios)

This methodology systematically tests for each of these issues.

---

## The 4-Step Validation Framework

### Validation #1: Execution Timing Check

**Purpose:** Verify no lookahead bias in entry/exit prices

**Script:** `validate_execution_timing.py`

**What it checks:**
1. Entry price = Open of day AFTER signal fires (not same-day close)
2. Exit price = Open of day AFTER exit signal
3. No unrealistic gaps suggesting incorrect data
4. `Next_Open` column calculated correctly

**How to run:**
```bash
# Test on ticker with suspicious returns
python validate_execution_timing.py SOUN 24mo

# Or test on any ticker
python validate_execution_timing.py NVDA 24mo
```

**Pass criteria:**
- ✅ All signals use next-day opens
- ✅ No gaps >10% (unless earnings/splits confirmed)
- ✅ `Next_Open` matches actual next day open

**If fails:**
- Review `backtest.py` execution logic
- Check for same-day close being used
- Verify no future data leakage

---

### Validation #2: Outlier Impact Analysis

**Purpose:** Identify if extreme trades are inflating averages

**Script:** `validate_outlier_impact.py`

**What it checks:**
1. Identifies trades with >100% returns
2. Calculates impact of removing outliers
3. Compares mean vs median (large gaps = outlier issues)
4. Shows return range (>200% spread = high variance)

**How to run:**
```bash
# Analyze most recent aggregate report
python validate_outlier_impact.py

# Or specify file
python validate_outlier_impact.py backtest_results/AGGREGATE_optimization_24mo_20251108_124336.txt
```

**Warning signs:**
- ⚠️ Mean >> Median (>10% gap)
- ⚠️ Single trade changes average by >10%
- ⚠️ Best trade >100% return
- ⚠️ Return range >200%

**If fails:**
- Use MEDIAN returns for expectations, not means
- Cap returns at ±50% and recalculate
- Identify which tickers have outliers
- Consider if outliers were unusual events (buyouts, etc.)

---

### Validation #3: Signal Detail Analysis

**Purpose:** Deep dive into specific signals showing extreme performance

**Script:** `validate_signal_details.py`

**What it checks:**
1. Actual trade count vs report claims
2. Return distribution (histogram)
3. Mean vs median comparison
4. Outlier identification (>3 std dev)
5. Adjusted performance without outliers

**How to run:**
```bash
# Analyzes Momentum Exhaustion by default
python validate_signal_details.py
```

**Warning signs:**
- ⚠️ Trade count discrepancy (report shows X, files have Y)
- ⚠️ Mean > Median by >10%
- ⚠️ Outliers change performance by >10%
- ⚠️ Sample size <20 trades

**If fails:**
- Check for counting errors in aggregation logic
- Use median instead of mean
- Don't rely on signals with <20 occurrences
- Verify outliers aren't data errors

---

### Validation #4: Walk-Forward Testing

**Purpose:** Test performance consistency across different time periods

**Script:** `validate_walk_forward.py`

**What it checks:**
1. First half vs second half performance
2. Quarterly performance variations
3. Signal generation consistency
4. Period-specific dependencies

**How to run:**
```bash
# Test single ticker
python validate_walk_forward.py NVDA 24mo

# Test multiple tickers
python validate_walk_forward.py  # defaults to NVDA, MSFT, AMD
```

**Warning signs:**
- ⚠️ Period difference >50% (highly dependent)
- ⚠️ Signal generation varies >50% between periods
- ⚠️ All gains concentrated in one quarter
- ⚠️ Recent period significantly better/worse

**If fails:**
- Strategy may be overfit to specific market conditions
- Test on additional out-of-sample data
- Consider market regime filters
- Adjust expectations for normal markets

---

## Supporting Analysis Tools

### Exit Signal Return Explanation

**Script:** `explain_exit_returns.py`

**Purpose:** Clarifies why exit signals show higher returns than entry signals

**Key insight:** Exit returns are measured from entry to exit (same trades), not independent returns

**Run:**
```bash
python explain_exit_returns.py
```

**Shows:**
- Entry signal: ALL trades (all exit paths)
- Exit signal: Filtered trades (only those exiting this way)
- Frequency distribution of exit paths
- Weighted expected returns

---

## Validation Checklist

Use this checklist when validating any backtest:

- [ ] Run Validation #1: Execution Timing
  - [ ] Entry prices use next-day opens
  - [ ] Exit prices use next-day opens
  - [ ] No unrealistic gaps
  
- [ ] Run Validation #2: Outlier Impact
  - [ ] Identify trades >100% return
  - [ ] Calculate mean vs median gap
  - [ ] Assess impact of removing outliers
  
- [ ] Run Validation #3: Signal Detail Analysis
  - [ ] Verify trade counts match report
  - [ ] Check return distribution
  - [ ] Compare adjusted vs unadjusted performance
  
- [ ] Run Validation #4: Walk-Forward Testing
  - [ ] Compare first vs second half
  - [ ] Check period dependency
  - [ ] Verify signal consistency

- [ ] Additional Checks
  - [ ] Sample sizes >20 for statistical significance
  - [ ] Performance not dependent on <5 outlier trades
  - [ ] Win rates between 40-70% (realistic range)
  - [ ] Median returns used for expectations
  - [ ] Strategy works across multiple time periods

---

## Interpretation Guidelines

### Execution Timing

**Green Flags:**
- ✅ All prices use next-day opens
- ✅ No gaps >10%
- ✅ Consistent execution logic

**Red Flags:**
- 🚨 Using same-day closes
- 🚨 Gaps >20% (possible data errors)
- 🚨 `Next_Open` missing or incorrect

### Outlier Impact

**Green Flags:**
- ✅ Mean ≈ Median (within 5%)
- ✅ No single trade changes average >5%
- ✅ Return range <100%

**Red Flags:**
- 🚨 Mean >> Median (>15% gap)
- 🚨 Single trade impacts average >10%
- 🚨 Return range >300%
- 🚨 Strategy depends on 1-2 outliers

### Sample Size

**Green Flags:**
- ✅ >100 trades: Statistically robust
- ✅ >50 trades: Reasonably reliable
- ✅ >20 trades: Minimum acceptable

**Red Flags:**
- 🚨 <20 trades: Unreliable
- 🚨 <10 trades: Meaningless
- 🚨 <5 trades: Pure luck

### Walk-Forward Consistency

**Green Flags:**
- ✅ Period difference <20%
- ✅ Signal generation varies <30%
- ✅ Consistent performance across quarters

**Red Flags:**
- 🚨 Period difference >100%
- 🚨 All gains in one period
- 🚨 Signal generation varies >50%

---

## Common Issues and Solutions

### Issue 1: Mean >> Median

**Symptom:** Average returns much higher than median returns

**Cause:** A few extreme winners inflating the average

**Solution:**
- Use median for realistic expectations
- Cap returns at ±50% and recalculate
- Remove top/bottom 5% and retest
- Document that mean is unreliable

### Issue 2: High Win Rates (>85%)

**Symptom:** Signal shows 90%+ win rate

**Causes:**
- Lookahead bias (using future data)
- Survivorship bias (only tested winners)
- Very small sample (<20 trades)
- Cherry-picked best exit path

**Solution:**
- Verify execution timing (Validation #1)
- Check sample size (need >20 trades)
- Understand it's a filtered subset of all trades
- Check frequency (rare signals aren't dependable)

### Issue 3: Extreme Returns (>50% avg)

**Symptom:** Strategy shows >50% average returns

**Causes:**
- Outliers inflating averages
- Lookahead bias
- Concentrated in one period/ticker
- Trading errors in backtest

**Solution:**
- Run all 4 validations
- Check median (usually 50-80% lower)
- Test on different periods
- Verify on multiple tickers

### Issue 4: Small Sample Sizes

**Symptom:** Signal shows great results but <20 occurrences

**Causes:**
- Signal is too specific/rare
- Period too short
- Strict filtering

**Solution:**
- Don't trade signals with <20 occurrences
- Test on longer periods (36mo, 60mo)
- Loosen filters to generate more signals
- Accept wider entry criteria

---

## Validation Workflow

```
┌─────────────────────────────────────┐
│ 1. Generate Backtest Results        │
│    python batch_backtest.py          │
└────────────┬────────────────────────┘
             │
             ↓
┌─────────────────────────────────────┐
│ 2. Run Validation #1                │
│    Execution Timing Check            │
│    → Passes? Continue                │
│    → Fails? Fix timing logic         │
└────────────┬────────────────────────┘
             │
             ↓
┌─────────────────────────────────────┐
│ 3. Run Validation #2                │
│    Outlier Impact Analysis           │
│    → Check mean vs median            │
│    → Identify extreme trades         │
└────────────┬────────────────────────┘
             │
             ↓
┌─────────────────────────────────────┐
│ 4. Run Validation #3                │
│    Signal Detail Deep Dive           │
│    → Verify trade counts             │
│    → Check distributions             │
└────────────┬────────────────────────┘
             │
             ↓
┌─────────────────────────────────────┐
│ 5. Run Validation #4                │
│    Walk-Forward Testing              │
│    → Test period consistency         │
│    → Check robustness                │
└────────────┬────────────────────────┘
             │
             ↓
┌─────────────────────────────────────┐
│ 6. Document Results                  │
│    - Use median for expectations     │
│    - Note sample sizes               │
│    - Flag period dependencies        │
│    - Identify robust signals         │
└─────────────────────────────────────┘
```

---

## Output Files Generated

After running all validations, you'll have:

1. `validate_execution_timing.py` - Timing verification script
2. `validate_outlier_impact.py` - Outlier analysis script
3. `validate_signal_details.py` - Deep dive analysis script
4. `validate_walk_forward.py` - Consistency testing script
5. `explain_exit_returns.py` - Entry/exit relationship explanation
6. `BACKTEST_VALIDATION_REPORT.md` - Technical validation results
7. `REALISTIC_PERFORMANCE_SUMMARY.md` - Plain English summary

---

## Quick Reference: Validation Commands

```bash
# Complete validation suite (run all 4 tests)
python validate_execution_timing.py SOUN 24mo
python validate_outlier_impact.py
python validate_signal_details.py
python validate_walk_forward.py NVDA 24mo

# Explain results
python explain_exit_returns.py

# Show summary
cat REALISTIC_PERFORMANCE_SUMMARY.md
```

---

## When to Re-Validate

Run full validation suite whenever:
- ✓ You modify signal generation logic
- ✓ You change entry/exit conditions
- ✓ You test on new data periods
- ✓ You add new tickers to your universe
- ✓ Results seem too good to be true
- ✓ Quarterly review (every 3 months)

---

## Expected Outcomes

### Realistic Backtest Results Should Show:

**Entry Signals:**
- Win Rate: 50-65%
- Median Return: +2-8% per trade
- Mean close to median (<10% gap)
- Sample size: >50 trades

**Exit Signals:**
- Win Rate: 60-85% (exits should be higher)
- Preserve gains vs prevent losses
- Frequency matters (rare signals aren't reliable)
- Work across multiple entry types

**Overall System:**
- Annual Returns: 10-30% (not 60%+)
- Max Drawdown: -15% to -30%
- Sharpe Ratio: 0.5 to 2.0
- Profit Factor: 1.3 to 2.5

### If Your Results Exceed These:

- 🚨 Run ALL 4 validations immediately
- 🚨 Check for outliers inflating averages
- 🚨 Verify sample sizes are adequate
- 🚨 Test on different time periods
- 🚨 Use median instead of mean

---

## Case Study: Your 24-Month Results

### Initial Results (Appeared Suspicious)
- Momentum Exhaustion: 90.6% win, +68% avg
- Stealth Accumulation: 56.3% win, +18% avg
- Volume Breakout: 8.3% win, -16% avg

### After Validation (Reality)
- Momentum: 16 trades (not 254), +24% median (not +68%)
- Stealth: 1,083 trades, +3% median (not +18%)
- Volume Breakout: Depends on one +379% outlier

### Lessons Learned
1. Always check actual trade counts
2. Mean can be 3-20x higher than median
3. Exit signals are rare (20-33% of trades)
4. Use weighted expectations, not cherry-picked results

---

## Best Practices

### Before Trading Any Strategy

1. **Run full validation suite** (all 4 tests)
2. **Use median returns** for expectations
3. **Verify sample size** (>50 trades minimum)
4. **Test on multiple periods** (walk-forward)
5. **Paper trade 3 months** before real money
6. **Size positions conservatively** (5-10% max)
7. **Track actual vs expected** performance

### Red Flags to Watch For

- 🚨 Annual returns >40% (too good to be true)
- 🚨 Win rates >75% on entry signals (suspicious)
- 🚨 Profit factors >5.0 (likely inflated)
- 🚨 Mean >2x median (outlier inflation)
- 🚨 Sample size <30 trades (unreliable)
- 🚨 All gains in one period (overfit)
- 🚨 One ticker dominates results (not robust)

### Documentation Standards

Every backtest should document:
- **Period tested:** Dates and market conditions
- **Universe:** Which stocks/sectors
- **Sample sizes:** Trades per signal type
- **Mean AND median:** Show both returns
- **Outliers:** List extreme trades separately
- **Walk-forward:** Results by time period
- **Limitations:** Known issues or dependencies

---

## Validation Script Reference

### Script Purposes and Usage

| Script | Purpose | Key Output | When to Use |
|--------|---------|------------|-------------|
| `validate_execution_timing.py` | Check lookahead bias | Timing issues list | Always first |
| `validate_outlier_impact.py` | Find extreme trades | Outlier impact table | When returns look high |
| `validate_signal_details.py` | Deep dive analysis | Trade distribution | When sample size unclear |
| `validate_walk_forward.py` | Test consistency | Period comparison | Before live trading |
| `explain_exit_returns.py` | Clarify results | Weighted expectations | When confused |

### Typical Validation Session

```bash
# 1. Generate backtest
python batch_backtest.py ibd.txt -p 24mo

# 2. Run all validations
python validate_execution_timing.py SOUN 24mo  # Check worst performer
python validate_outlier_impact.py              # Check for outliers
python validate_signal_details.py              # Deep dive suspicious signals
python validate_walk_forward.py                # Test consistency

# 3. Get clarity
python explain_exit_returns.py                 # Understand the numbers

# 4. Review reports
cat BACKTEST_VALIDATION_REPORT.md
cat REALISTIC_PERFORMANCE_SUMMARY.md
```

---

## Maintenance and Updates

### When to Update This Methodology

- New validation tests are discovered
- Common issues emerge that should be checked
- Better statistical methods become available
- Trading platform requirements change

### Version History

**v1.0 (2025-11-08):**
- Initial 4-step validation framework
- Scripts for execution, outliers, signals, walk-forward
- Explanation tools for entry/exit returns
- Comprehensive documentation

---

## Contact and Support

This methodology was developed through systematic analysis of backtest results that appeared too good to be true. The validation revealed:

- Execution timing was correct (no lookahead)
- Outliers were massively inflating averages
- Sample sizes were smaller than reported
- Period dependency was significant

Always question results that seem exceptional, and validate thoroughly before risking capital.

---

## Quick Start Guide

**If you're validating a new backtest:**

1. Run: `python validate_execution_timing.py TICKER 24mo`
   - Should pass (no timing issues)

2. Run: `python validate_outlier_impact.py`
   - Check for outliers, use median

3. Run: `python validate_signal_details.py`
   - Verify sample sizes, check distributions

4. Run: `python validate_walk_forward.py`
   - Ensure consistency across periods

5. Run: `python explain_exit_returns.py`
   - Understand what the numbers mean

6. Read: `REALISTIC_PERFORMANCE_SUMMARY.md`
   - Get final realistic expectations

**Total time:** 10-15 minutes for complete validation

**Value:** Prevents trading strategies with hidden flaws that could lose real money
