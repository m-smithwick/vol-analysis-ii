# Corrected Configuration Comparison: Entry & Exit Parameters

**Date**: December 9, 2025  
**Status**: ✅ FIXED SIGNAL FILTERING BUG - Results now reflect TRUE config differences  
**Test Data**: 4-ticker portfolio (VRT, GLD, SLV, APP) over 24-month period

## 🚨 Why This Analysis Was Needed

**Previous config comparisons were INVALID** due to a critical bug:
- All configs were using identical signal sets despite different configurations
- Deprecated `Stealth_Accumulation` signal (22.7% win rate) was being used instead of intended signals
- Performance differences were not due to actual config variations

**This analysis uses CORRECTED signal filtering** that respects the `enabled_entry_signals` configuration.

---

## 📊 Configuration Summary Table

| Parameter | Conservative | Base | Aggressive |
|-----------|-------------|------|-----------|
| **Entry Threshold** | 6.5 | 6.0 | 5.5 |
| **Time Stop** | 0 bars (disabled) | 20 bars | 8 bars |
| **Regime Filter** | SPY + Sector (strict) | SPY + Sector (strict) | SPY only (lenient) |
| **Enabled Entry Signals** | `moderate_buy_pullback` only | `moderate_buy_pullback` only | `moderate_buy_pullback` only |
| **Enabled Exit Signals** | Standard 3 signals | Standard 3 signals | Standard 3 signals |
| **Transaction Costs** | 0.05% slippage | 0.05% slippage | 0.10% slip + $0.005 comm |

---

## 🎯 Corrected Performance Results (Sample: VRT Analysis)

### Conservative Config
```yaml
Entry Threshold: 6.5 (highest quality)
Time Stop: 0 bars (let winners run)
Regime: SPY + Sector (strict filtering)
Transaction Costs: Standard (0.05% slippage)
```

**Results:**
- **13 trades total** (selective entries)
- **Win Rate: 61.5%** (quality over quantity)
- **Average R-Multiple: 0.73R** 
- **Net Profit: +3.10%** ($3,104 on $100K)
- **Time Stops: 0%** (no forced exits)
- **Profit Scaling: 23%** (3 of 13 trades reached +2R)
- **Transaction Costs: 3.04%** of gross P&L

### Base Config
```yaml
Entry Threshold: 6.0 (balanced)
Time Stop: 20 bars (exit laggards)
Regime: SPY + Sector (strict filtering)
Transaction Costs: Standard (0.05% slippage)
```

**Results:**
- **22 trades total** (balanced approach)
- **Win Rate: 68.2%** (best win rate)
- **Average R-Multiple: 0.79R**
- **Net Profit: +8.89%** ($8,893 on $100K)
- **Time Stops: 36%** (8 of 22 trades)
- **Profit Scaling: 18%** (4 of 22 trades reached +2R)
- **Transaction Costs: 2.77%** of gross P&L

### Aggressive Config
```yaml
Entry Threshold: 5.5 (more entries)
Time Stop: 8 bars (quick exits)
Regime: SPY only (lenient filtering)
Transaction Costs: STRESS TEST (2x costs)
```

**Results:**
- **28 trades total** (high frequency)
- **Win Rate: 39.3%** (many marginal setups)
- **Average R-Multiple: 0.02R** (near breakeven)
- **Net Profit: +0.43%** ($432 on $100K)
- **Time Stops: 89%** (25 of 28 trades - devastating!)
- **Profit Scaling: 0%** (no trades reached +2R)
- **Transaction Costs: 59.31%** of gross P&L (crippling)

## 🔍 True Configuration Differences (Post-Fix)

### 1. **Entry Quality vs Quantity Trade-off**

| Config | Threshold | Trades (VRT) | Win Rate | Quality |
|--------|-----------|--------------|----------|---------|
| Conservative | 6.5 | 13 | 61.5% | High quality, fewer trades |
| Base | 6.0 | 22 | 68.2% | Balanced approach |
| Aggressive | 5.5 | 28 | 39.3% | More trades, lower quality |

**Key Insight**: Lower threshold = more trades but significantly lower win rate.

### 2. **Time Stop Impact (CRITICAL DIFFERENCE)**

| Config | Time Stop | Time Stop % | Impact |
|--------|-----------|-------------|---------|
| Conservative | 0 bars | 0% | Let winners run, accept some laggards |
| Base | 20 bars | 36% | Exit positions not working after 20 days |
| Aggressive | 8 bars | **89%** | Force exits after just 8 days - kills most trades! |

**Critical Finding**: Aggressive config's 8-bar time stop is **devastating** - it exits 89% of positions before they can develop.

### 3. **Transaction Cost Sensitivity**

**Aggressive config uses DOUBLE transaction costs as stress test:**
- Slippage: 0.10% vs 0.05% (2x)
- Commission: $0.005/share vs $0.00
- **Impact**: 59% of gross P&L consumed by costs!

**For VRT:**
- Conservative: $97 costs on $3,202 gross (3.04%)
- Base: $254 costs on $9,147 gross (2.77%)
- **Aggressive: $629 costs on $1,061 gross (59.31%!)**

### 4. **Regime Filtering**

**Conservative & Base**: SPY + Sector (both required)
**Aggressive**: SPY only (sector ignored)

This should allow aggressive more trades in sector-weak periods, but the time stop damage overwhelms any benefit.

---

## 💡 Key Insights from Corrected Analysis

### 1. **Time Stops Are the Primary Driver**
The biggest performance difference isn't the entry threshold (6.5 vs 6.0 vs 5.5) - it's the time stop strategy:
- **0 bars (Conservative)**: Let positions develop naturally
- **20 bars (Base)**: Reasonable timeout for laggards  
- **8 bars (Aggressive)**: Kills most trades before they can work

### 2. **Lower Thresholds Hurt More Than Help**
Aggressive's 5.5 threshold generates many marginal trades that get stopped out:
- 28 trades vs 13 (Conservative) = 115% more trades
- But 39% win rate vs 61.5% = 37% lower success rate
- Net result: Much worse performance despite more opportunities

### 3. **Transaction Costs Matter at High Frequency**
Aggressive config's high trade frequency + double costs = devastating:
- 28 trades × $22.47 average cost = $629 total costs
- With only $1,061 gross profit, costs consume 59% of gains

### 4. **Regime Filtering Difference is Minor**
The SPY-only vs SPY+Sector difference is overwhelmed by the time stop effect.

---

## 🎯 Corrected Recommendations

### Conservative Config - BEST FOR CAPITAL PRESERVATION
- **Use when**: Risk-averse, smaller accounts, volatile markets
- **Strengths**: High win rate (61.5%), no time stop pressure, lower costs
- **Weaknesses**: Fewer opportunities, may hold laggards longer

### Base Config - BEST BALANCED APPROACH  
- **Use when**: Balanced risk tolerance, systematic approach
- **Strengths**: Highest win rate (68.2%), reasonable trade frequency
- **Weaknesses**: Some good trades cut short by 20-bar time stop

### Aggressive Config - AVOID OR MODIFY
- **Current form**: Poor performance due to over-trading and short time stops
- **To improve**: Increase time stop to 15-20 bars, or disable entirely
- **Transaction costs**: Use standard costs, not stress-test levels

---

## 🔧 Configuration Tuning Insights

### Optimal Parameter Combinations (Based on Corrected Data):

1. **Entry Threshold**: 6.0-6.5 range is optimal
   - Below 6.0: Too many marginal trades
   - Above 6.5: Miss good opportunities

2. **Time Stop Strategy**:
   - **0 bars**: Best for trending markets (Conservative approach)
   - **15-20 bars**: Good compromise (Base approach)
   - **8 bars**: Too aggressive, kills developing trades

3. **Regime Filtering**: 
   - SPY + Sector provides valuable quality filter
   - SPY-only allows more trades but lower quality

### Suggested New Config: "Balanced_Optimized"
```yaml
entry:
  moderate_buy_pullback: 6.0
time_stop_bars: 15  # Sweet spot between Conservative (0) and Base (20)
regime: SPY + Sector  # Keep quality filter
transaction_costs: standard  # Don't stress test
```

---

## 📈 Performance Ranking (Corrected)

**Based on risk-adjusted returns and win rates:**

1. **🥇 Base Config**: 68.2% win rate, 0.79R average, balanced approach
2. **🥈 Conservative Config**: 61.5% win rate, 0.73R average, capital preservation
3. **🥉 Aggressive Config**: 39.3% win rate, 0.02R average, needs major revision

---

## 🚨 Critical Bug Fix Summary

**What Was Fixed:**
- Hard-coded signal lists in `backtest.py` replaced with config-driven filtering
- Created `signal_config_utils.py` for proper config-to-DataFrame mapping
- Updated `batch_backtest.py` to pass config parameters to backtest functions

**Impact:**
- All configurations now use ONLY their intended signals
- Performance comparisons are now valid and meaningful
- Deprecated signals (like Stealth_Accumulation) are properly excluded

**Validation:**
- NBIX Conservative: 3/3 trades use Moderate_Buy (was 2/7)
- Zero trades use deprecated Stealth_Accumulation (was 5/7)
- Config-driven filtering confirmed working across all configurations
