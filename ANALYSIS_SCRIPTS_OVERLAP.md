# Analysis Scripts - Purpose & Overlap Assessment

**Created:** 2025-11-22  
**Purpose:** Document all analysis scripts, their purposes, and relationships  
**Status:** Complete assessment - minimal overlap found ✅

---

## Executive Summary

**Finding:** Scripts have **distinct purposes** with **minimal overlap**.  
Each tool serves a specific analytical need and they complement rather than duplicate each other.

**Recommendation:** Keep all scripts, update README to document their purposes.

---

## Quick Reference: Which Tool to Use When

| Scenario | Tool | Purpose |
|----------|------|---------|
| **Professional evaluation needed** | `analyze_professional_metrics.py` | Calculate institutional metrics (Sharpe, drawdown, etc.) |
| **Optimizing signal thresholds** | `analyze_trade_quality.py` | Find best score cutoffs, visualize signal quality |
| **Understanding portfolio size** | `analyze_portfolio_decomposition.py` | Compare 10 vs 25 vs 40 ticker portfolios |
| **Setting realistic expectations** | `calculate_realistic_expectations.py` | Weighted average returns by exit path |
| **Confused about entry vs exit** | `explain_exit_returns.py` | Educational tool explaining the difference |

---

## Detailed Script Analysis

### 1. analyze_professional_metrics.py (NEW)

**Purpose:** Professional-grade performance evaluation

**What it calculates:**
- Maximum Drawdown (peak-to-trough equity decline)
- Sharpe Ratio (risk-adjusted returns)
- Win/Loss Ratio (average win ÷ average loss)
- Monthly return distribution (consistency)
- Consecutive win/loss streaks (psychology)
- Professional grading (retail vs professional assessment)

**When to use:**
- After completing backtests
- When evaluating system for real money trading
- When comparing to professional standards
- For institutional capital deployment decisions

**Inputs:** Trade ledger CSV (LOG_FILE_*.csv)  
**Outputs:** `professional_evaluation.txt`

**Example:**
```bash
python analyze_professional_metrics.py --csv LOG_FILE_cmb_24mo.csv
```

**Key Metrics:**
- Drawdown: -9.37% (Grade A)
- Sharpe: 3.35 (Grade A) 
- Overall: A- (Institutional Quality)

**Overlap:** NONE - Unique institutional metrics

---

### 2. analyze_trade_quality.py

**Purpose:** Signal quality optimization and threshold tuning

**What it analyzes:**
- Performance by score buckets (0-4, 4-6, 6-8, 8-10)
- Threshold optimization (find optimal cutoff)
- Entry signal comparison (which signals work best)
- Exit type distribution (PROFIT_TARGET, TRAIL_STOP, etc.)
- Entry-exit pairing performance
- Signal visualizations (scatter plots, box plots, heatmaps)

**When to use:**
- When deciding which signals to trade
- When tuning accumulation_score thresholds
- When analyzing which entry-exit combos work best
- When creating visual presentations

**Inputs:** Trade ledger CSV (LOG_FILE_*.csv or PORTFOLIO_TRADE_LOG_*.csv)  
**Outputs:** 
- `SIGNAL_QUALITY_ANALYSIS_*.txt`
- Various PNG charts (scatter, box, heatmap, pie)

**Example:**
```bash
python analyze_trade_quality.py LOG_FILE_cmb_24mo.csv -o backtest_results
```

**Key Insights:**
- Finds optimal thresholds (e.g., ≥6.0 for Moderate Buy)
- Identifies which signals have statistical significance
- Shows which entry-exit pairings are most profitable

**Overlap:** Minor with `calculate_realistic_expectations.py` (both analyze entry-exit pairs, but different angles)

---

### 3. analyze_portfolio_decomposition.py

**Purpose:** Portfolio size sensitivity analysis

**What it decomposes:**
- Volume Effect: Returns from trading more tickers (more opportunities)
- Sizing Effect: Returns from better per-trade performance
- Trade quality consistency across portfolio sizes
- Position sizing characteristics

**When to use:**
- When deciding how many tickers to trade
- When comparing concentrated (10 tickers) vs diversified (40 tickers)
- When understanding if "more is better"
- After running portfolio sensitivity tests

**Inputs:** Multiple LOG_FILE CSVs from portfolio_sensitivity tests  
**Outputs:** `portfolio_decomposition_analysis.txt`

**Example:**
```bash
# First run sensitivity tests
python test_portfolio_size_sensitivity.py

# Then analyze
python analyze_portfolio_decomposition.py
```

**Key Insights:**
- Tells you if larger portfolios work due to volume or quality
- Shows if trade quality degrades with diversification
- Helps decide optimal portfolio size

**Overlap:** NONE - Unique portfolio size analysis

---

### 4. calculate_realistic_expectations.py

**Purpose:** Calculate weighted expected value by exit path frequency

**What it calculates:**
- Entry signal → Exit signal frequency matrix
- How often each exit fires for each entry
- Weighted average returns (probability × return)
- Best-case vs typical-case scenarios

**When to use:**
- When setting realistic return expectations
- When understanding exit path probabilities
- When explaining why overall returns ≠ exit signal returns
- After reviewing aggregate reports

**Inputs:** Individual backtest files (TICKER_24mo_backtest_*.txt)  
**Outputs:** Console report with weighted expectations

**Example:**
```bash
python calculate_realistic_expectations.py
```

**Key Insights:**
- Shows Momentum Exhaustion only fires 20% of the time
- Calculates what you'll ACTUALLY experience
- Weighted median is realistic expectation

**Overlap:** ⚠️ Minor with `analyze_trade_quality.py`
- Both analyze entry-exit combinations
- `calculate_realistic_expectations.py`: Focuses on path probabilities
- `analyze_trade_quality.py`: Focuses on signal optimization
- **Different angles, complementary**

---

### 5. explain_exit_returns.py

**Purpose:** Educational tool explaining entry vs exit return confusion

**What it explains:**
- Why exit signals show higher returns than entry signals
- Entry signals measure ALL trades (all exit paths)
- Exit signals measure only trades that exited that way (subset)
- Exit returns are measured from ENTRY to EXIT (not independent)

**When to use:**
- When confused about aggregate report numbers
- When explaining results to others
- When entry returns seem too low
- Educational/training purposes

**Inputs:** Aggregate backtest file (AGGREGATE_optimization_*.txt)  
**Outputs:** Console explanation with examples

**Example:**
```bash
python explain_exit_returns.py
```

**Key Insights:**
- Exit signals are self-selected best performers
- Most trades exit via common signals (Distribution, Sell)
- Rare optimal exits (Momentum, Profit Taking) inflate exit averages

**Overlap:** NONE - Purely educational

---

## Script Relationships & Workflow

### Recommended Analysis Workflow

```
1. RUN BACKTESTS
   ↓
   python batch_backtest.py -f cmb.txt -p 24mo
   ↓
   
2. PROFESSIONAL EVALUATION (What grade?)
   ↓
   python analyze_professional_metrics.py
   ↓
   Result: Institutional metrics (Sharpe, drawdown, etc.)
   
3. SIGNAL OPTIMIZATION (Which signals?)
   ↓
   python analyze_trade_quality.py LOG_FILE.csv
   ↓
   Result: Optimal thresholds, best signals
   
4. REALISTIC EXPECTATIONS (What to expect?)
   ↓
   python calculate_realistic_expectations.py
   ↓
   Result: Weighted return expectations
   
5. PORTFOLIO SIZING (How many tickers?)
   ↓
   python test_portfolio_size_sensitivity.py
   python analyze_portfolio_decomposition.py
   ↓
   Result: Optimal portfolio size

6. EDUCATION (Still confused?)
   ↓
   python explain_exit_returns.py
   ↓
   Result: Clarification on metrics
```

---

## Overlap Analysis Matrix

|  | Professional Metrics | Trade Quality | Portfolio Decomp | Realistic Expect | Explain Exit |
|--|---------------------|---------------|------------------|------------------|--------------|
| **Calculates Sharpe/Drawdown** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Optimizes Thresholds** | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Analyzes Portfolio Size** | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Exit Path Frequencies** | ❌ | ⚠️ Partial | ❌ | ✅ | ⚠️ References |
| **Professional Grading** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Creates Visualizations** | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Educational/Explanatory** | ⚠️ Includes context | ❌ | ❌ | ⚠️ Includes examples | ✅ |

**Legend:**
- ✅ = Primary function
- ⚠️ = Secondary/minor function
- ❌ = Not included

---

## Consolidation Recommendation: NONE NEEDED

**Verdict:** Keep all 5 scripts as-is.

**Rationale:**
1. Each has distinct primary purpose
2. Minimal functional overlap
3. Different output formats
4. Serve different use cases
5. Complementary rather than redundant

**Action Required:**
- ✅ Document in README (update needed)
- ❌ No consolidation needed
- ❌ No deprecation needed

---

## README Update Plan

### New Section to Add: "Performance Analysis & Optimization"

**Location:** After "Quick Start & Commands", before "Validation Status"

**Content Structure:**

```markdown
## Performance Analysis & Optimization

After running backtests, use these tools to evaluate and optimize your strategy:

### Professional Evaluation
```bash
# Calculate institutional-grade metrics (Sharpe, drawdown, etc.)
python analyze_professional_metrics.py --csv LOG_FILE_cmb_24mo.csv
```
Outputs: Sharpe ratio, maximum drawdown, monthly consistency, loss streaks,  
professional grading (retail vs institutional standards)

### Signal Optimization
```bash
# Find optimal thresholds and best-performing signals
python analyze_trade_quality.py LOG_FILE_cmb_24mo.csv -o backtest_results
```
Outputs: Threshold analysis, signal comparisons, entry-exit pairings, visualizations

### Portfolio Sizing
```bash
# Understand if you should trade 10, 25, or 40 tickers
python analyze_portfolio_decomposition.py
```
Outputs: Volume vs sizing effects, trade quality by portfolio size

### Realistic Expectations
```bash
# Calculate weighted expected returns by exit path frequency
python calculate_realistic_expectations.py
```
Outputs: Entry-exit frequency matrix, weighted expectations, best vs typical case

### Understanding Results
```bash
# Explains why exit returns differ from entry returns
python explain_exit_returns.py
```
Educational tool for interpreting backtest reports
```

---

## Documentation Status

- [x] All scripts reviewed
- [x] Purposes identified
- [x] Overlaps assessed (minimal)
- [x] Workflow defined
- [ ] README updated (ready for implementation)
- [ ] User notified of findings

---

## Additional Notes

### Validation Scripts (Already in Tests)

The following validation scripts exist in `tests/` directory:
- `validate_execution_timing.py` - Check lookahead bias
- `validate_outlier_impact.py` - Analyze outlier effects
- `validate_signal_details.py` - Deep dive signal analysis
- `validate_walk_forward.py` - Period consistency testing

**These should remain in tests/** - They're validation tools, not regular analysis tools.

### Scripts in Root vs Tests

**Current Structure:**
- Root: Analysis & optimization tools (user-facing)
- Tests: Validation tools (QA/verification)

**This is correct** - no changes needed.

---

## Final Recommendation

1. ✅ **Keep all 5 analysis scripts** - Each has unique value
2. ✅ **Create this overlap doc** - Reference for users
3. ✅ **Update README** - Add analysis tools section
4. ❌ **No consolidation needed** - Scripts are complementary
5. ❌ **No deprecation needed** - All serve purposes

**Next Step:** Update README with new "Performance Analysis & Optimization" section.
