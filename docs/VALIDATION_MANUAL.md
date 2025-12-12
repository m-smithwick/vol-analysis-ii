# Trading System Validation Manual

**Last Updated:** December 11, 2025  
**Status:** ✅ AUTHORITATIVE - Single source of truth for all validated findings  
**Purpose:** Consolidated validation results across entry signals, stop strategies, parameters, and configurations

---

## 📋 EXECUTIVE SUMMARY

### What's Validated and Production-Ready ✅

**Entry Signals:**
- ✅ **Moderate Buy Pullback (≥6.0)** - Primary signal, 60-70% win rate, regime-agnostic
- ❌ Stealth Accumulation - Failed out-of-sample (53% → 23% win rate)
- ❌ Strong Buy - Regime-dependent failure (84% → 17%)
- ❌ Volume Breakout - Insufficient sample, poor performance

**Stop Strategies:**
- ✅ **Static Stops** - Winner by 3x ($161k vs $53k), 15% stop rate
- ❌ Time Decay - Cuts winners early, 23% stop rate, 3x worse than static
- ❌ Vol Regime - Excessive stops, 32% stop rate, adaptive logic backfires

**Parameters:**
- ✅ **Time Stop: 20 bars** - Optimal (reduced from 12 bars)
- ✅ **Entry Threshold: 6.0-6.5** - Quality vs quantity sweet spot
- ✅ **Risk per Trade: 0.75-1.0%** - Standard position sizing

**Configurations:**
- ✅ **Base Config** - Most balanced, 68% win rate
- ✅ **Conservative Config** - Best for capital preservation, 62% win rate
- ⚠️ **Aggressive Config** - NOT RECOMMENDED (89% time stop rate)

### Critical Lessons Learned

1. **Use Median, NOT Mean** - Outliers inflate averages 3-20x
2. **Static Beats Sophisticated** - Simple static stops outperform variable strategies
3. **Quality Over Quantity** - Lower thresholds = more trades but worse results
4. **Out-of-Sample Critical** - In-sample success doesn't guarantee future performance
5. **Validation Rigor Matters** - Premature conclusions lead to contradictions (see Timeline)

### Realistic Performance Expectations

**Per Trade:**
- Win Rate: 60-70%
- Median Return: +6-7%
- Holding Period: 40-70 days (regime-dependent)

**Annual:**
- Conservative: 10-12%
- Moderate: 12-18%
- Aggressive: 18-25% (with higher risk)
- **NOT 60%+** (those are outlier-inflated historical results)

---

## 1️⃣ ENTRY SIGNAL VALIDATION

**Status:** ✅ VALIDATED (November 9, 2025)  
**Sample Size:** 342 trades (Moderate Buy), 24-month period  
**Source:** STRATEGY_VALIDATION_COMPLETE.md

### Primary Signal: Moderate Buy Pullback (≥6.0)

**Validation Results:**

| Metric | Choppy Markets | Rally Markets | Overall |
|--------|---------------|---------------|---------|
| Win Rate | 55.9% | 70.5% | 60-65% |
| Median Return | +6.23% | +7.28% | +6-7% |
| Closed Trades | 254 | 88 | 342 |
| Avg Hold Period | 71 days | 44 days | ~60 days |
| Verdict | ✅ WORKS | ✅ WORKS BETTER | ✅ REGIME-AGNOSTIC |

**Why This Signal Works:**

**In Choppy Markets:**
- Pullbacks are deeper (more fear)
- Bounces are stronger (relief rallies)
- Longer holding periods needed
- Higher volatility creates larger moves

**In Rally Markets:**
- Pullbacks are shallower (dip buyers ready)
- Quick bounces, smoother recovery
- Shorter holding periods
- Still catches the uptrend

**Critical Strength:** Works in ALL market conditions (regime-agnostic)

### Deprecated Signals (DO NOT USE)

#### Stealth Accumulation (≥4.0) - FAILED

**Out-of-Sample Test Results:**

| Period | Win Rate | Median Return | Status |
|--------|----------|---------------|--------|
| In-Sample (18mo) | 53.2% | +3.30% | Looked promising |
| Out-of-Sample (6mo) | 22.7% | -7.65% | ❌ FAILED |

**Why It Failed:**
- Overfit to training data (worked in choppy markets only)
- Rally markets negated early accumulation advantage
- Signal became noise in trending conditions
- **Lesson:** Always validate out-of-sample

#### Strong Buy - UNRELIABLE

**Regime Performance:**

| Regime | Win Rate | Median Return | Change |
|--------|----------|---------------|--------|
| Choppy | 84.2% | +17.75% | Looked excellent |
| Rally | 17.6% | -9.57% | ❌ Collapsed |
| Difference | -66.6% | -27.32% | Complete reversal |

**Why It's Unreliable:**
- Performance completely reversed between regimes
- Too aggressive for trending markets
- Small sample size (36 trades total)
- **Lesson:** Regime-dependent signals are dangerous

#### Volume Breakout - INSUFFICIENT

- Only 9 trades total (statistically meaningless)
- Poor performance in both regimes (0-40% win rate)
- Highly dependent on outliers
- **Lesson:** Need 100+ trades minimum for confidence

### Entry Signal Recommendations

**✅ USE:**
- Moderate Buy Pullback (≥6.0) ONLY
- Wait for signal confirmation
- Enter at next day open

**❌ DO NOT USE:**
- Stealth Accumulation (failed validation)
- Strong Buy (regime-dependent)
- Volume Breakout (insufficient data)
- Any unvalidated signals

**Position Sizing:**
- Risk 0.75-1.0% per trade
- Position sizes: 5-10% of portfolio
- Adjust for conviction and volatility

---

## 2️⃣ STOP STRATEGY VALIDATION

**Status:** ✅ VALIDATED (November 22, 2025)  
**Sample Size:** 982 trades total (387 static, 428 vol_regime, 167 time_decay)  
**Period:** 36 months  
**Source:** STOP_STRATEGY_VALIDATION.md

### Winner: Static Stops

**Three-Way Comparison Results:**

| Strategy | Total P&L | Trades | Stop Rate | $/Trade | Status |
|----------|-----------|--------|-----------|---------|--------|
| **STATIC** | **$161,278** | 387 | **15.0%** | **$417** | ✅ RECOMMENDED |
| VOL_REGIME | $146,572 | 428 | 32.0% | $342 | ❌ Not Recommended |
| TIME_DECAY | $53,359 | 167 | 23.4% | $319 | ❌ Not Recommended |

**Performance Improvement:**
- Static vs Time_Decay: **+202% P&L** ($161k vs $53k)
- Static vs Vol_Regime: **+10% P&L** ($161k vs $147k)
- Static achieves **lowest stop-out rate** (15% vs 23-32%)

### Why Static Wins (Counterintuitive but Validated)

**1. Variable Stops Kill Winners Early**

Example scenario:
```
Day 1:  Entry at $50, stop at $47.50 (static)
Day 5:  Price at $51, time_decay tightens to $49.00
Day 10: Price at $52, time_decay tightens to $50.00  
Day 12: Pullback to $49.50 → STOPPED OUT by time_decay
Day 15: Recovery to $54 → Would have hit profit target with static

Result: -1% loss (time_decay) vs +8% win (static)
```

**2. Static Allows Exit Signals to Work**

Static stops give trades room to develop and let validated exit signals (Profit Target, Trailing Stop, Signal Exit) work properly.

**Time_Stop Performance Comparison:**

| Strategy | TIME_STOP P&L | Trades | Why Different? |
|----------|---------------|--------|----------------|
| STATIC | +$10,851 | 143 | 143 trades survived to 20-bar limit |
| TIME_DECAY | +$2,844 | 24 | Only 24 survived (rest stopped out early) |
| VOL_REGIME | +$1,937 | 44 | Only 44 survived (excessive stops) |

Variable stops kill trades before time stop can save them.

**3. Profit Exit Performance**

| Strategy | Profit Exits P&L | Count | System Total |
|----------|------------------|-------|--------------|
| STATIC | $154,269 | 125 | $161,278 (BEST) |
| VOL_REGIME | $159,870 | 197 | $146,572 (worse despite more exits) |
| TIME_DECAY | $64,703 | 77 | $53,359 (significantly worse) |

Vol_regime gets MORE profit exits but still underperforms because excessive stops (-$58k) cost more than extra exits gain.

### The Intuition Trap

**Time Decay Logic:** "Tighten stops as trades age to lock in gains"
- **Reality:** Cuts winners before they reach targets
- **Result:** 23% stop rate, $53k P&L

**Vol Regime Logic:** "Adjust stops based on volatility"
- **Reality:** Creates highest stop rate (32%) by being too reactive
- **Result:** $147k P&L but 10% worse than static

**Static Logic:** "Set reasonable stop at entry, let trade play out"
- **Reality:** Gives trades room to develop, lets exit signals work
- **Result:** 15% stop rate, $161k P&L, best per-trade average

### Stop Strategy Recommendations

**✅ USE:**
- Static stops (set at entry, never move except trailing after +2R)
- Initial stop: min(swing_low - 0.5×ATR, VWAP - 1.0×ATR)
- Trailing stop: 10-day low after +2R achieved

**❌ DO NOT USE:**
- Any tightening stop strategies
- Time-based stop tightening
- Volatility-adjusted stops that move daily
- Trailing stops that move up aggressively

**Future Research (Optional):**
- Test wider initial stops (0.75×ATR instead of 0.5×ATR)
- Sector-specific initial widths (but still static once set)

---

## 3️⃣ PARAMETER OPTIMIZATION

**Status:** ✅ VALIDATED (November 22, 2025)  
**Source:** TIME_STOP_OPTIMIZATION_RESULTS.md

### Time Stop Optimization: 20 Bars Optimal

**Problem:** 44% of trades hitting time stop (too many dead positions)  
**Goal:** Reduce to <25% while maintaining expectancy  
**Solution:** Extend from 12 bars to 20 bars

**Results:**

| Bars | TIME_STOP Rate | Win Rate | Expectancy | Trades | Verdict |
|------|---------------|----------|------------|--------|---------|
| 12 | 44% | 63.9% | +8.73% | 443 | Too aggressive |
| 15 | 34% | 65.2% | +13.15% | 210 | Better |
| **20** | **23%** | **63.9%** | **+13.71%** | **208** | ✅ OPTIMAL |

**Impact:**
- ✅ TIME_STOP rate reduced from 44% to 23% (goal achieved)
- ✅ Expectancy improved +57% (+8.73% → +13.71%)
- ✅ Win rate maintained at 63.9%
- ✅ Quality over quantity (208 trades vs 443, but much better per-trade)

**Why 20 Bars Works:**
1. Gives setups time to develop (accumulation needs time)
2. Filters out false signals (setups that fail by bar 15 are likely false)
3. Balanced patience (not too quick like 8 bars, not too slow like no limit)

### Entry Threshold Optimization: 6.0-6.5 Range

**Analysis by Threshold:**

| Threshold | Win Rate | Expectancy | Trades | Assessment |
|-----------|----------|------------|--------|------------|
| ≥5.5 | 39.3% | +0.43% | High | Too many marginal trades |
| ≥6.0 | 68.2% | +8.89% | Medium | ✅ Balanced approach |
| ≥6.5 | 61.5% | +3.10% | Low | Quality but fewer opportunities |
| ≥7.0 | 62.0% | +8.57% | Low | Very selective |

**Recommendations:**
- **6.0**: Best balanced approach (base_config)
- **6.5**: Capital preservation (conservative_config)
- **Avoid <6.0**: Too many low-quality trades
- **Avoid >7.0**: Miss too many good opportunities

### Risk Per Trade: 0.75-1.0%

**Current Standard:** 0.75% per trade  
**Range:** 0.5-1.0% depending on risk tolerance

**Conservative (0.5% risk):**
- Smaller positions
- Lower drawdowns
- Expected annual: 8-12%

**Moderate (0.75% risk):**
- Standard positions
- Balanced risk/reward
- Expected annual: 12-18%

**Aggressive (1.0% risk):**
- Larger positions
- Higher drawdowns
- Expected annual: 18-25%

---

## 4️⃣ CONFIGURATION TESTING

**Status:** ✅ CURRENT (December 9, 2025)  
**Context:** Post-bug-fix testing (signal filtering corrected)  
**Source:** CORRECTED_CONFIG_COMPARISON.md

### Configuration Comparison Results

**Test:** 4-ticker portfolio (VRT, GLD, SLV, APP), 24-month period

| Config | Entry Threshold | Time Stop | Win Rate | Net Profit | Assessment |
|--------|----------------|-----------|----------|-----------|------------|
| **Base** | 6.0 | 20 bars | **68.2%** | **+8.89%** | ✅ Most balanced |
| **Conservative** | 6.5 | 0 bars | 61.5% | +3.10% | ✅ Capital preservation |
| **Aggressive** | 5.5 | 8 bars | 39.3% | +0.43% | ❌ NOT RECOMMENDED |

### Key Finding: Time Stop Impact is Critical

**Time Stop Performance:**

| Config | Time Stop | Time Stop % of Exits | Impact |
|--------|-----------|---------------------|---------|
| Conservative | 0 bars | 0% | Let winners run fully |
| Base | 20 bars | 36% | Reasonable timeout for laggards |
| Aggressive | 8 bars | **89%** | ❌ Kills most trades before development |

**Critical Discovery:** Aggressive config's 8-bar time stop exits 89% of positions before they can develop - this is devastating.

### Configuration Recommendations

**✅ Base Config - RECOMMENDED DEFAULT**
- Entry threshold: 6.0 (balanced)
- Time stop: 20 bars (optimal)
- Win rate: 68.2% (best)
- Use when: Balanced risk tolerance, systematic approach

**✅ Conservative Config - CAPITAL PRESERVATION**
- Entry threshold: 6.5 (higher quality)
- Time stop: 0 bars (let winners run)
- Win rate: 61.5% (good)
- Use when: Risk-averse, smaller accounts, volatile markets

**❌ Aggressive Config - AVOID OR MODIFY**
- Current form: Poor performance (39.3% win rate)
- Problem: 8-bar time stop + low threshold (5.5) = over-trading + premature exits
- To improve: Increase time stop to 15-20 bars OR disable entirely
- Transaction costs: Use standard, not stress-test levels

### Suggested Optimal Config

```yaml
entry_threshold: 6.0  # Balanced quality/quantity
time_stop: 20 bars    # Optimal from testing
stop_strategy: static  # Winner from validation
risk_per_trade: 0.75%  # Standard
regime_filter: SPY + Sector  # Quality filter
```

---

## 5️⃣ VALIDATION TIMELINE & LESSONS

### The November 2025 Contradiction

**Critical incident showing importance of validation rigor:**

**November 16, 2025** - VARIABLE_STOP_LOSS_FINDINGS.md:
- Finding: "Time_decay wins! 1.52R vs 1.25R static (+22%)"
- Conclusion: "IMPLEMENT IMMEDIATELY"
- Method: R-multiple metric, 4,249 trades
- Status: 🔬 PRELIMINARY

**November 22, 2025** - STOP_STRATEGY_VALIDATION.md:
- Finding: "Static wins by 3x! $161k vs $53k time_decay"
- Conclusion: "Change defaults to static"
- Method: Dollar P&L, 982 trades, same portfolio for all strategies
- Status: ✅ VALIDATED

**Why Contradiction Occurred:**
1. Different metrics (R-multiple vs dollar P&L)
2. Different portfolios (not apples-to-apples comparison)
3. Nov 16 declared "winner" without cross-validation
4. Premature "IMPLEMENT IMMEDIATELY" recommendation

**Resolution:**
- Nov 22 testing used proper methodology (same portfolio, multiple metrics)
- Nov 16 marked as 🔬 PRELIMINARY/SUPERSEDED
- Created validation-rigor-standard Cline rule to prevent recurrence

### Validation Rigor Standard

**All validation must now be labeled:**

**🔬 PRELIMINARY** - Single metric, not cross-validated, DO NOT implement  
**✅ VALIDATED** - Multiple metrics confirm, apples-to-apples comparison, safe for production

**Requirements for ✅ VALIDATED:**
1. Same portfolio, same period for all strategies
2. Multiple metrics (P&L, stop rate, per-trade avg)
3. 100+ trades minimum (statistical significance)
4. Reproducible methodology documented

**See:** `.clinerules/validation-rigor-standard.md` for complete standard

---

## 6️⃣ CURRENT STATUS & REVIEW SCHEDULE

**Living Status Document:** `docs/VALIDATION_STATUS.md` (updated monthly)

### Currently Validated ✅

**Entry Signals:**
- ✅ Moderate Buy (≥6.0) - Production ready

**Stop Strategies:**
- ✅ Static stops - Production ready

**Parameters:**
- ✅ Time stop: 20 bars
- ✅ Entry threshold: 6.0-6.5
- ✅ Risk: 0.75-1.0%

**Configurations:**
- ✅ Base config - Recommended default
- ✅ Conservative config - Capital preservation
- ⚠️ Aggressive config - Needs modification

### Deprecated/Failed ❌

**Entry Signals:**
- ❌ Stealth Accumulation - Failed out-of-sample
- ❌ Strong Buy - Regime-dependent failure
- ❌ Volume Breakout - Insufficient data

**Stop Strategies:**
- ❌ Time Decay - 3x worse than static
- ❌ Vol Regime - Excessive stops (32%)

### Review Schedule

**Monthly:**
- Update VALIDATION_STATUS.md with latest month's data
- Check if validated signals maintain performance
- Monitor stop rates and win rates

**Quarterly:**
- Re-run out-of-sample validation
- Test on new data (last 3 months)
- Update validation manual if needed

**Before Major Changes:**
- Full validation required
- Use validation-rigor-standard
- Document methodology and results

---

## 7️⃣ DETAILED REFERENCE DOCUMENTS

**For deep dives into validation evidence:**

### Entry Signal Validation
- **STRATEGY_VALIDATION_COMPLETE.md** - Complete 24-month analysis
  - 342 trades (Moderate Buy)
  - Regime breakdown (choppy vs rally)
  - Out-of-sample testing
  - Outlier analysis
  - Walk-forward validation

### Stop Strategy Validation
- **STOP_STRATEGY_VALIDATION.md** - Three-way comparison
  - 982 trades total
  - Dollar P&L analysis
  - Stop rate analysis
  - Exit type distribution
  - Mechanism explanation

### Parameter Optimization
- **TIME_STOP_OPTIMIZATION_RESULTS.md** - Three-way parameter test
  - 12 vs 15 vs 20 bars
  - TIME_STOP rate reduction
  - Expectancy improvement
  - Trade quality analysis

### Configuration Testing
- **CORRECTED_CONFIG_COMPARISON.md** - Post-bug-fix comparison
  - Signal filtering fix context
  - 4-ticker portfolio test
  - Transaction cost analysis
  - Time stop impact analysis

### Tools & Methodology
- **ANALYSIS_SCRIPTS_OVERLAP.md** - Analysis tools guide
  - Which tool to use when
  - Script purposes
  - Workflow recommendations

### Framework & Planning
- **PROFESSIONAL_ANALYSIS_PLAN.md** - Professional metrics framework
  - Maximum drawdown calculation
  - Sharpe/Sortino ratios
  - Monthly return distribution
  - Loss streak analysis

---

## 8️⃣ RECOMMENDATIONS FOR TRADERS

### Production Trading Setup

**Entry:**
- Use Moderate Buy Pullback (≥6.0) ONLY
- Wait for signal confirmation
- Enter at next day open

**Position Sizing:**
- Risk 0.75-1.0% per trade
- Position sizes: 5-10% of portfolio
- Use base_config or conservative_config

**Stop Management:**
- Static stops (set at entry)
- Initial: min(swing_low - 0.5×ATR, VWAP - 1.0×ATR)
- Trail after +2R: 10-day low

**Exit Priority:**
1. Profit Taking (if fires)
2. Momentum Exhaustion (if fires)
3. Distribution Warning (common exit)
4. Time Stop (20 bars if not working)

**Portfolio:**
- Use ibd.txt ticker list (validated: 59.6% win, +5.21% median)
- Alternative: ibd20.txt (57.2% win, +4.59% median)
- Avoid: ltl.txt (47.9% win, -0.28% median)

### Realistic Expectations

**Per Trade:**
- Win rate: 60-65%
- Median return: +6-7%
- Best case: +20-50% (20% of trades)
- Worst case: -10-15% (stop loss)

**Annual:**
- Conservative: 10-12%
- Moderate: 12-18%
- Aggressive: 18-25% (with higher drawdowns)

**Psychological:**
- Expect losing months (30-40% of months)
- Expect consecutive losses (5-7 in a row possible)
- Don't chase outliers (+100% trades are rare)
- Focus on consistency, not home runs

### Before Trading Live

**Checklist:**
- [ ] Understand validation findings (this document)
- [ ] Set realistic expectations (12-18% annual, not 60%+)
- [ ] Choose appropriate config (base or conservative)
- [ ] Test position sizing for your account
- [ ] Paper trade 1-3 months
- [ ] Monitor execution quality (slippage, fills)
- [ ] Verify you can handle drawdowns psychologically
- [ ] Have risk management plan in place

---

## 9️⃣ MAINTENANCE & UPDATES

**This Document:**
- Updated monthly with new validation results
- Updated quarterly with out-of-sample tests
- Updated immediately if validation contradictions arise

**Validation Status:**
- See `docs/VALIDATION_STATUS.md` for current live status
- Updated monthly after each month's trading

**Detailed Evidence:**
- Detailed validation documents remain in root and docs/
- Archived documents moved to docs/history/validation/
- All evidence preserved for reference

**Contact:**
- Questions about validation: Review detailed documents
- Found an issue: Report via PROJECT-STATUS.md
- Suggest improvements: Document in tasks.md

---

## 🔟 RELATED DOCUMENTATION

**Primary References:**
- `STOP_STRATEGY_VALIDATION.md` - Detailed stop testing (982 trades)
- `STRATEGY_VALIDATION_COMPLETE.md` - Entry signal validation (archived)
- `TIME_STOP_OPTIMIZATION_RESULTS.md` - Parameter optimization
- `CORRECTED_CONFIG_COMPARISON.md` - Configuration testing

**Supporting:**
- `docs/VALIDATION_STATUS.md` - Current status dashboard
- `.clinerules/validation-rigor-standard.md` - Validation requirements
- `ANALYSIS_SCRIPTS_OVERLAP.md` - Analysis tools guide
- `PROFESSIONAL_ANALYSIS_PLAN.md` - Professional metrics framework

**Cline Rules:**
- `.clinerules/validation-rigor-standard.md` - Prevent premature validation
- `.clinerules/parameter-propagation.md` - Prevent configuration bugs
- `.clinerules/financial-data-verification.md` - Prevent data confusion

**System Documentation:**
- `README.md` - Quick start and commands
- `CODE_MAP.txt` - Module architecture
- `TRADING_STRATEGY.md` - Complete strategy guide
- `configs/README.md` - Configuration usage

---

**Document Status:** ✅ COMPLETE AND CURRENT  
**Last Validation Update:** December 11, 2025  
**Next Review:** Monthly (January 2026)
