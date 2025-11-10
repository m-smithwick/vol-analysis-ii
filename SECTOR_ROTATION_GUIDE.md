# 🔄 Sector Rotation Dashboard - Quick Reference Guide

**Built**: November 2025  
**Purpose**: Systematic sector analysis for optimal portfolio allocation

---

## 📁 Files Overview

| File | Purpose | Speed |
|------|---------|-------|
| `sector_etfs.txt` | List of 11 sector ETFs | N/A |
| `sector_rotation.py` | Core scoring algorithms (600+ lines) | N/A |
| `sector_dashboard.py` | Fast dashboard (momentum + RS only) | ~10 sec |
| `sector_dashboard_with_backtest.py` | Complete (with volume analysis) | 5-10 min first run, ~10 sec cached |

---

## 🎯 Scoring System (0-14 Points)

### Momentum (6 pts)
- Above 50-day MA: +2
- Above 200-day MA: +2
- 20-day return >5%: +2

### Volume Analysis (6 pts) *requires backtest*
- Win rate >60%: +2
- Positive expectancy: +2
- Recent signals (<14 days): +2

### Relative Strength (2 pts)
- Outperforming SPY: +1
- Top-3 sector: +1

---

## 🚀 Quick Start

### Fast Analysis (10 seconds)
```bash
python sector_dashboard.py
```

### Complete Analysis (first run ~5 min, then cached)
```bash
python sector_dashboard_with_backtest.py
```

### Weekly Check (Monday morning)
```bash
python sector_dashboard.py --compare --top 5
```

---

## 📊 Score Interpretation

| Score | Category | Allocation | Action |
|-------|----------|------------|--------|
| **8-10** | LEADING | 35-50% | Overweight heavily |
| **6-7** | STRONG | 15-25% | Market weight |
| **4-5** | NEUTRAL | 5-10% | Light/opportunistic |
| **0-3** | WEAK | 0% | Avoid completely |

---

## 🎯 Position Sizing Quick Reference

**Adjust your position sizes based on top sector score:**

| Top Sector Score | Position Size | Cash % | Entry Approach |
|-----------------|---------------|--------|----------------|
| **≥10/14** | 100-125% | 10-15% | Aggressive - enter all Moderate Buy |
| **8-9/14** | 90-100% | 15-20% | Normal - enter most Moderate Buy |
| **6-7/14** | 75-90% | 20-30% | Selective - best setups only |
| **4-5/14** | 50-75% | 30-40% | Very selective - exceptional only |
| **≤3/14** | 0-25% | 60-80% | Defensive - minimal entries |

**Your Current Market (Top = 5/14)**: Use 50-75% size, hold 30-40% cash, be very selective

---

## 🚦 Entry Checklist by Market Environment

### When Top Sector ≥8/14 (Strong Market)
- ✅ Moderate Buy signal
- ✅ Stock in top sector
- → **ENTER** with 100% size

### When Top Sector 6-7/14 (Normal Market)
- ✅ Moderate Buy signal
- ✅ Near support (within 1 ATR)
- ✅ CMF >1.0σ
- ✅ Above VWAP
- → **ENTER** with 75% size if ALL met

### When Top Sector 4-5/14 (Weak Market) ← YOU ARE HERE
- ✅ Moderate Buy signal
- ✅ Near support (within 0.5 ATR)
- ✅ CMF >1.5σ (very strong)
- ✅ Above VWAP
- ✅ Additional confirmation (pivot, volume spike)
- → **ENTER** with 50% size if ALL met

### When Top Sector ≤3/14 (Very Weak)
- ❌ **NO ENTRIES** - move to cash

---

## ⚠️ Rotation Triggers

### Rotate INTO Sector When:
- ✅ Score increases by 3+ points
- ✅ Score crosses above 6
- ✅ Momentum reaches 6/6

### Rotate OUT OF Sector When:
- ❌ Score drops by 3+ points
- ❌ Score falls below 6
- ❌ Momentum drops to 0-2

---

## 🔄 Recommended Workflow

### Weekly (Every Monday)
1. Run quick dashboard with comparison
2. Check for rotation alerts (>3 point changes)
3. Note any sectors crossing above/below score of 6

### Monthly (First Sunday)
1. Run full 6mo analysis
2. Review allocation recommendations
3. Rebalance portfolio based on rankings
4. Update watchlists for leading sectors

### Quarterly
1. Run 12mo analysis for long-term view
2. Validate sector selections
3. Make strategic portfolio shifts

---

## 💡 Real-World Example

**Your Recent Success:**
- **Tech (XLK) scored 10/14** → You allocated 50%+ to tech
- **Result**: +10.71% expectancy, 66.5% win rate
- **33x better** than diversified approach in weak sectors

**Matt's Challenge:**
- **Financials (XLF) scored 3/14** → His portfolio heavily weighted there
- **Result**: +0.32% expectancy, 42.9% win rate
- **Wrong sector = poor results** even with good stock selection

**Lesson**: **Sector selection matters more than stock selection!**

---

## 🎓 Integration with Stock Selection

```bash
# Step 1: Identify leading sectors (score ≥6)
python sector_dashboard.py

# Step 2: Run backtests on stocks in those sectors
python batch_backtest.py -f tech_stocks.txt -p 12mo

# Step 3: Select stocks with strong signals
# - Moderate Buy win rate >60%
# - Positive expectancy
# - Recent signal activity

# Step 4: Monitor for sector rotation
python sector_dashboard.py --compare  # Weekly check
```

---

## 📦 Cache Management

### Backtest Cache
- **Location**: `sector_cache/backtest_results_{period}.json`
- **Validity**: 7 days
- **Purpose**: Speed up subsequent dashboard runs

### Score History
- **Location**: `sector_cache/scores_{period}_latest.json`
- **Purpose**: Enable `--compare` mode for rotation detection
- **Updated**: Every dashboard run

---

## 🔧 Command Reference

### Basic Commands
```bash
# Quick analysis
python sector_dashboard.py

# With period
python sector_dashboard.py -p 6mo

# Top N only
python sector_dashboard.py --top 5

# Compare to last run
python sector_dashboard.py --compare

# Save report
python sector_dashboard.py -o reports
```

### Advanced Commands
```bash
# Full analysis with backtest
python sector_dashboard_with_backtest.py

# Quick mode (skip backtest)
python sector_dashboard_with_backtest.py --quick

# Compare with backtest
python sector_dashboard_with_backtest.py --compare -o sector_analysis
```

---

## 📈 Key Benefits

✅ **Objective sector ranking** - No guessing which sectors to favor  
✅ **Early rotation detection** - Catch shifts before they're obvious  
✅ **Systematic rebalancing** - Remove emotion from allocation  
✅ **Integrated with your system** - Uses same volume analysis framework  
✅ **Prevents concentration risk** - Automatically diversifies across leading sectors  
✅ **Optimizes performance** - Always weighted toward market leaders  

---

## 🎯 Success Metrics

**Before Sector Dashboard:**
- Manual sector selection based on intuition
- Potentially overweighted in weakening sectors
- Miss early rotation opportunities

**After Sector Dashboard:**
- Data-driven sector rankings updated weekly/monthly
- Automatic rotation signals (>3 point changes)
- Always weighted toward leading sectors (score ≥6)
- Systematic process for catching sector leadership changes

---

## 🚨 Important Notes

1. **200-day MA may show N/A** for 3mo period (need longer data)
   - Use 6mo or 12mo periods for full momentum scoring

2. **Volume scores need backtest** 
   - Use `sector_dashboard_with_backtest.py` for complete 14-point scoring
   - First run takes time, then cached for 7 days

3. **Rotation alerts need history**
   - Run once to establish baseline
   - Second run (a week later) will show rotation alerts

4. **HTTP 404 errors are cosmetic**
   - These are from yfinance trying to fetch fundamentals
   - Don't affect sector analysis
   - Can be safely ignored

---

## 📚 Further Reading

See README.md "Sector Rotation Dashboard" section for:
- Detailed scoring explanations
- Sample dashboard outputs
- Complete workflow examples
- Integration patterns
- Troubleshooting guide

---

**Built as part of Weeks 1-3 implementation plan (Nov 2025)**
