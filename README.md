# 📊 Advanced Stock Volume Analysis Tool

A sophisticated Python tool for analyzing stock accumulation and distribution patterns using advanced volume indicators and visual signal detection.

---

## 🚨 CRITICAL VALIDATION UPDATE (2025-11-08)

### ❌ Stealth Accumulation Signal - FAILED OUT-OF-SAMPLE VALIDATION

**DO NOT USE Stealth Accumulation signal** until completely redesigned and re-validated.

**Out-of-Sample Test Results (6 months):**
- Win Rate: **22.7%** (collapsed from 53.2% expected) ❌
- Median Return: **-7.65%** (was +2.29% expected) ❌ 
- This is textbook overfitting - signal looked great on training data but failed on new data

**See:** `OUT_OF_SAMPLE_VALIDATION_REPORT.md` for complete analysis

### ⚠️ Moderate Buy Signal - Lower Returns Than Expected

**Out-of-Sample Performance:**
- Win Rate: **64.6%** (maintained/improved) ✅
- Median Return: **+2.18%** (dropped from +5.21% expected) ⚠️
- Signal still works but with lower profit per trade

**Revised Expectations:** Use **+2-3% median per trade** (not +5%)

---

## 🚀 Features

### **Complete Entry & Exit Signal System**
- **Entry Signals**: Strong Buy, Moderate Buy (VALIDATED), ~~Stealth Accumulation (DEPRECATED)~~, Multi-Signal Confluence, Volume Breakouts
- **5 Exit Signal Types**: Profit Taking, Distribution Warning, Sell Signals, Momentum Exhaustion, Stop Loss Triggers
- **⚠️ ONLY USE MODERATE BUY** - Other entry signals require validation
- **Advanced Technical Indicators**: OBV divergence, A/D Line analysis, VWAP positioning, support level detection
- **Dual Scoring System**: Entry Score (0-10) + Exit Score (1-10) with threshold-based alerts and visual markers

### **Professional Visualization**
- **Entry Signal Markers**: 🟢 Green dots (Strong Buy), 🟡 Yellow dots (Moderate Buy - USE THIS), ~~💎 Cyan diamonds (Stealth - DEPRECATED)~~, ⭐ Magenta stars (Confluence), 🔥 Orange triangles (Breakouts)
- **Exit Signal Markers**: 🟠 Orange dots (Profit Taking), ⚠️ Gold squares (Distribution Warning), 🔴 Red dots (Sell), 💜 Purple X's (Momentum Exhaustion), 🛑 Dark red triangles (Stop Loss)
- **Multi-panel Charts**: Price action with all signals, Volume indicators with divergences, Volume bars with dual scoring
- **Enhanced Threshold Lines**: Visual zones at levels 2, 4, 6, 7, and 8 for both entry and exit scoring

### **Command Line Interface**
- **Flexible Usage**: Analyze any stock ticker with customizable time periods
- **Batch Processing**: Process multiple tickers from files with individual output reports
- **Multi-timeframe Analysis**: Cross-reference signals across different time horizons
- **Screen Optimized**: Charts sized perfectly for 16-inch Mac displays

### **Smart Data Caching System with Schema Versioning (NEW)**
- **Local Cache**: Stores Yahoo Finance data locally to avoid redundant downloads
- **Incremental Updates**: Only downloads new data since last cache update
- **Automatic Management**: Creates and maintains cache automatically
- **Cache Information**: View cached tickers and their status
- **Selective Clearing**: Clear cache for specific tickers or entire cache
- **Force Refresh**: Override cache when fresh data is needed
- **Schema Versioning**: Advanced cache data integrity and compatibility system
  - **Metadata Headers**: Each cache file contains JSON metadata with schema version, checksums, and data provenance
  - **Data Integrity**: SHA-256 checksums ensure cached data hasn't been corrupted
  - **Automatic Migration**: Legacy cache files are automatically upgraded to current schema format
  - **Backward Compatibility**: Handles existing cache files seamlessly during system updates
  - **Version Validation**: Invalid or incompatible cache files are automatically detected and refreshed
- **Timezone Handling**: Robust timezone management for consistent data processing
  - Automatically normalizes timezone-aware and timezone-naive datetime objects
  - Uses period-based API calls instead of explicit dates to avoid timezone conflicts
  - Ensures consistent timezone handling between cached and newly downloaded data

### **Batch Processing & File Output**
- **File Input**: Process ticker lists from text files (one ticker per line)
- **Individual Reports**: Generate separate analysis files for each ticker
- **Stealth Ranking**: Focus on recent stealth accumulation over historical averages
- **Chart Export**: Optional PNG chart generation for batch processing
- **Summary Reports**: Consolidated rankings with stealth activity scores

## 📚 Development & Upgrade Documentation

The system is under active development with a comprehensive upgrade roadmap. Documentation is organized for efficient context management:

### **Quick Reference Documents**
- **`upgrade_summary.md`** (~2K tokens) - Progress overview and next priorities
- **`upgrade_status_active.md`** (~5K tokens) - Pending items and implementation details
- **`upgrade_status_completed.md`** (~50K tokens) - Historical archive of completed items
- **`upgrade_spec.md`** (~70K tokens) - Complete technical specifications for all upgrade items
- **`CODE_MAP.txt`** (~15K tokens) - File organization, dependencies, and implementation matrix

### **Current Development Status**
- **Progress**: 10/13 items complete (77%)
- **Latest**: Item #13 (RiskManager Framework) completed with full test coverage
- **Next**: Item #5 (P&L-Aware Exit Logic) ready for implementation

For developers contributing or extending the system, start with `upgrade_summary.md` for orientation, then consult `upgrade_status_active.md` for current work priorities.

##  Installation

### Requirements
```bash
pip install pandas numpy yfinance matplotlib argparse requests
```

### Python Version
- Python 3.7 or higher required
- Tested on Python 3.12

---

## 🚀 Getting Started - Complete Workflow

This guide walks you through the complete workflow from initial setup to daily/monthly trading routines.

### Initial Setup (One-Time, ~15 minutes)

#### 1. Install Dependencies
```bash
pip install pandas numpy yfinance matplotlib boto3
```

#### 2. Configure Massive.com Credentials (Optional but Recommended)

For 40x faster data downloads, configure your Massive.com credentials:

```bash
# Create or edit ~/.aws/credentials
[massive]
aws_access_key_id = your-key-id
aws_secret_access_key = your-secret-key
```

#### 3. Test Connection
```bash
python test_massive_bulk_single_day.py
```

**Expected output**: ✅ Successfully downloaded and parsed test file

---

### Step 1: Populate Historical Cache (~10 minutes)

**Goal**: Download 24 months of historical data for all your tickers

```bash
# Start conservative (test run - 30 seconds)
python populate_cache_bulk.py --months 1

# Expand to full dataset (8 minutes)
python populate_cache_bulk.py --months 24
```

**What happens**: 
- Downloads daily files from Massive.com containing ALL US stocks
- Splits data by your tracked tickers
- Caches in `data_cache/` directory (uncompressed, ready to use)
- Optionally saves other tickers in `massive_cache/` (compressed archive)

**Storage**: ~135 MB for 24 months + 53 tickers

**Key Advantage**: Extends automatically - if interrupted, just re-run and it skips already-cached dates

---

### Step 2: Organize Your Ticker Lists (5 minutes)

Create ticker files (one ticker per line) to organize your watchlists:

```bash
# Your core watchlist (10-20 stocks you monitor closely)
cat > stocks.txt << EOF
AAPL
MSFT
GOOGL
NVDA
TSLA
EOF

# IBD stocks (if you follow IBD 50/85)
# Edit ibd.txt and ibd20.txt

# Sector ETFs (already provided)
# sector_etfs.txt contains 11 sector ETFs (XLK, XLV, XLF, etc.)
```

**File Organization Tips**:
- `stocks.txt` - Your core watchlist (10-20 stocks)
- `ibd.txt` - IBD 50/85 stocks for rotation scanning
- `sector_etfs.txt` - 11 sector ETFs (provided)
- Comments allowed: Lines starting with `#` are ignored

---

### Step 3: Validate Strategy with Backtesting (~30 minutes)

**Goal**: Understand which entry/exit signals work best for your stocks

```bash
# Test your core watchlist (10 min)
python batch_backtest.py -f stocks.txt -p 12mo

# Test IBD stocks (15 min)
python batch_backtest.py -f ibd.txt -p 12mo

# Review aggregate report
# Location: backtest_results/AGGREGATE_optimization_12mo_*.txt
```

**What to look for in the report**:
- ✅ **Moderate Buy** win rate (should be 60-65%)
- ✅ Positive expectancy (+2-3% per trade)
- ✅ Profit factor >2.0
- ⚠️ Sample size (need 50+ trades for reliability)

**Key Takeaway**: This shows you which signals are profitable with YOUR stocks in YOUR timeframe

---

### Step 4: Initial Stock Analysis (15 minutes)

Analyze individual stocks to understand current signals:

```bash
# Single ticker deep dive
python vol_analysis.py AAPL -p 6mo

# Batch analysis with charts (saves HTML files)
python vol_analysis.py -f stocks.txt -p 6mo --save-charts
```

**Review checklist**:
- [ ] Current entry score (look for 5-7 range for Moderate Buy)
- [ ] Active signals (any 🟡 yellow dots recently?)
- [ ] Exit score (should be <4 for healthy positions)
- [ ] Swing structure (is stock near support?)

---

### Daily Routine (10-15 minutes)

**Monday-Friday Morning Routine**:

```bash
# 1. Check sector strength (2 min)
python sector_dashboard.py --compare --top 5

# 2. Update cache with latest data (1 min)
python populate_cache_bulk.py --months 25  # Extends by 1 month

# 3. Scan watchlist for new signals (5-10 min)
python vol_analysis.py -f stocks.txt -p 3mo --save-charts

# 4. Review charts for new opportunities
# Location: results/*.html or results/*.png
```

**Decision Framework** (based on sector score):

| Top Sector Score | Your Action | Position Size | Entry Criteria |
|-----------------|-------------|---------------|----------------|
| **≥8/14** | Trade aggressively | 100% | Enter all Moderate Buy signals |
| **6-7/14** | Trade normally | 75-90% | Enter best Moderate Buy setups |
| **4-5/14** | Trade defensively | 50-75% | Only exceptional setups |
| **≤3/14** | Hold cash | 0-25% | Avoid new entries |

**Signal Priority**:
1. ✅ Look for **🟡 Moderate Buy** signals (validated, 64.6% win rate)
2. ✅ Confirm stock's sector scores ≥6/14
3. ✅ Check position near support + above VWAP
4. ✅ Monitor existing positions for exit signals (🟠⚠️🔴)

---

### Monthly Routine (30-45 minutes)

**First Sunday of Each Month**:

```bash
# 1. Full sector analysis with backtesting (10 min)
python sector_dashboard_with_backtest.py -p 6mo --compare -o monthly_reports

# 2. Review sector rotation alerts
# Check for sectors with >3 point changes

# 3. Rebalance portfolio based on sector scores
# - Reduce sectors that dropped >3 points
# - Increase sectors that rose >3 points  
# - Exit positions in sectors scoring <4/14

# 4. Re-validate backtest with fresh data (15 min)
python batch_backtest.py -f stocks.txt -p 12mo -o monthly_backtest

# 5. Update ticker lists based on performance
# - Remove underperformers (negative expectancy)
# - Add new stocks from leading sectors

# 6. Extend historical cache (5 min)
python populate_cache_bulk.py --months 25
```

**Portfolio Review Checklist**:
- [ ] Are current holdings in sectors scoring ≥6/14?
- [ ] Any rotation alerts requiring action?
- [ ] Any positions showing Distribution Warning or Sell signals?
- [ ] New opportunities in leading sectors?
- [ ] Backtest results still positive for strategy?

---

### Quarterly Deep Dive (1-2 hours)

**Comprehensive Strategy Validation**:

```bash
# 1. Full 24-month backtest
python batch_backtest.py -f stocks.txt -p 24mo

# 2. Walk-forward threshold validation  
python vol_analysis.py AAPL -p 24mo --validate-thresholds

# 3. Long-term sector analysis
python sector_dashboard_with_backtest.py -p 12mo --compare

# 4. Review and refine strategy based on results
```

**Questions to answer**:
- Is my win rate maintaining 60-65% on Moderate Buy?
- Is expectancy still positive (+2-3%)?
- Which sectors have been most profitable?
- Any signals consistently underperforming?

---

### Adding New Tickers (5 minutes)

**When you discover a new stock to track**:

```bash
# 1. Add to appropriate ticker file
echo "NVDA" >> stocks.txt

# 2. Populate cache for new ticker (8 min for 24 months)
python populate_cache_bulk.py --months 24

# Result: Only downloads NVDA data
# (existing tickers automatically skipped due to smart deduplication)
```

**Alternative** (if you saved `massive_cache/`):
- Extract ticker from compressed archive (instant, zero downloads)
- Requires custom extraction script (see BULK_CACHE_POPULATION.md)

---

### Quick Reference Commands

**Most Common Daily/Weekly Commands**:

```bash
# Daily quick scan
python vol_analysis.py -f stocks.txt -p 3mo --save-charts

# Weekly sector check  
python sector_dashboard.py --compare --top 5

# Monthly full sector analysis
python sector_dashboard_with_backtest.py -p 6mo --compare -o monthly_reports

# Add new ticker
echo "TICKER" >> stocks.txt && python populate_cache_bulk.py --months 24

# Backtest validation
python batch_backtest.py -f stocks.txt -p 12mo

# Single stock deep dive
python vol_analysis.py AAPL -p 6mo --backtest
```

**Cache Management**:
```bash
# View cache info
python vol_analysis.py --cache-info

# Clear specific ticker
python vol_analysis.py --clear-cache AAPL

# Force fresh download
python vol_analysis.py AAPL --force-refresh
```

---

### Time Investment Summary

| Activity | Frequency | Time Required |
|----------|-----------|---------------|
| Initial setup | One-time | 15 minutes |
| Cache population | One-time | 10 minutes |
| Daily routine | Mon-Fri | 10-15 minutes |
| Weekly sector check | Monday | 2 minutes |
| Monthly analysis | First Sunday | 30-45 minutes |
| Quarterly deep dive | Quarterly | 1-2 hours |

**Total weekly commitment**: ~1 hour (50-75 min daily + 30-45 min monthly spread)

---

## 🔧 Usage

### Basic Usage
```bash
# Analyze AAPL with default 1-year period
python vol_analysis.py

# Analyze specific ticker
python vol_analysis.py TSLA

# Custom time period
python vol_analysis.py NVDA --period 6mo

# Short form
python vol_analysis.py MSFT -p 3mo
```

### Batch Processing
```bash
# Process all tickers from a file
python vol_analysis.py --file stocks.txt

# Batch processing with custom period and output directory
python vol_analysis.py -f stocks.txt --period 3mo --output-dir results

# Batch with charts saved including plotly
python vol_analysis.py --file ibd.txt -p 12mo --save-charts --chart-backend plotly

# Include chart images for all tickers
python vol_analysis.py -f stocks.txt --save-charts

# Full batch processing example
python vol_analysis.py -f matt.txt -p 6mo -o matt_output --save-charts --chart-backend plotly
```

### Data Caching Options
```bash
# View cache information
python vol_analysis.py --cache-info

# Clear cache for specific ticker
python vol_analysis.py --clear-cache AAPL

# Clear entire cache
python vol_analysis.py --clear-cache all

# Force refresh (ignore cache)
python vol_analysis.py AAPL --force-refresh

# Force refresh in batch processing
python vol_analysis.py -f stocks.txt --force-refresh
```

### Bulk Cache Population from Massive.com (NEW)

**Efficient mass data retrieval** - Download 24 months of data for all tickers in ~8 minutes (40x faster than per-ticker approach).

```bash
# Populate cache with 1 month of data (test run)
python populate_cache_bulk.py --months 1

# Extend to 6 months (automatically skips already-cached dates)
python populate_cache_bulk.py --months 6

# Full 24 months of historical data
python populate_cache_bulk.py --months 24

# Specific date range
python populate_cache_bulk.py --start 2024-01-01 --end 2024-12-31

# Skip saving non-tracked tickers (faster, less storage)
python populate_cache_bulk.py --months 12 --no-save-others
```

**Key Features:**
- **40x Faster**: Downloads each daily file once (contains all US stocks), not once per ticker
- **Sectional Population**: Build cache incrementally - extend 1 month to 6 months automatically
- **Smart Deduplication**: Automatically skips already-cached dates, no redundant downloads
- **Two-Tier Caching**: 
  - `data_cache/` - Your tracked tickers (uncompressed, ready to use)
  - `massive_cache/` - All other US stocks (compressed, for future use)

**Performance:**
- 1 month (~20 days): ~30 seconds
- 6 months (~130 days): ~2 minutes  
- 24 months (~500 days): ~8 minutes

See [BULK_CACHE_POPULATION.md](BULK_CACHE_POPULATION.md) for comprehensive guide.

### Schema Management & Migration (NEW)
```bash
# Check which cache files need migration
python migrate_cache.py --dry-run

# Migrate all legacy cache files to current schema
python migrate_cache.py

# Validate migrated files have correct schema
python migrate_cache.py --validate

# View migration status and file information
python migrate_cache.py --dry-run
```

### Backtesting & Validation (NEW)
```bash
# Run risk-managed backtest (DEFAULT - full trade management)
python vol_analysis.py AAPL --backtest

# Risk-managed backtest with custom period
python vol_analysis.py TSLA -p 6mo --backtest

# Simple entry-to-exit backtest (basic win rate analysis)
python vol_analysis.py NVDA --backtest --simple

# Walk-forward threshold validation (Item #9 prototype)
python vol_analysis.py AAPL -p 24mo --validate-thresholds
```

> ℹ️ **Risk-managed backtesting is now the default** - it provides professional-grade metrics including R-multiples, position sizing, stops, profit scaling, and trailing stops. Use `--simple` flag only if you need basic entry-to-exit analysis.

```bash
# Show per-ticker progress/log output
python vol_analysis.py -f stocks.txt --debug
```

### Risk-Managed Backtesting Features (Item #5 - DEFAULT MODE)
```bash
# Default backtest now includes full risk management
python vol_analysis.py AAPL --backtest

# All these commands now run risk-managed backtest:
python vol_analysis.py TSLA -p 12mo --backtest
python vol_analysis.py NVDA -p 6mo --backtest

# Legacy flag (--risk-managed) still supported for backward compatibility
python vol_analysis.py AAPL --risk-managed  # Same as --backtest
```

**Risk Management Features:**
- **Position Sizing**: Risk 0.75% per trade (configurable)
- **Initial Stop**: `min(swing_low - 0.5*ATR, VWAP - 1*ATR)`
- **Hard Stop**: Exit if price falls below initial stop
- **Time Stop**: Exit after 12 bars if <+1R (dead position management)
- **Regular Exit Signals**: Uses proven exit system (Distribution Warning, Momentum Exhaustion, Sell Signal, etc.)
- **Profit Scaling**: Take 50% at +2R, trail remainder
- **Trailing Stop**: 10-day low after +2R achieved

**Critical Fixes (Nov 2025):**
- ✅ **End-of-Day Signal Timing**: Fixed execution bug where exit checks were running on the same bar as entry, causing immediate (0-day) exits
- ✅ **Exit Logic Optimization**: Removed aggressive momentum check (CMF<0/price<VWAP) that caused 93% immediate exits; now uses proven exit signals
- **Proper Implementation**: Entry signals fire at close of day T, execution at open of day T+1, exit checks start on day T+2 or later
- **Result**: Realistic holding periods (9.7 days avg) with positive expectancy (+0.26R vs -0.05R)

### Batch Backtesting - Strategy Optimization (NEW)
```bash
# Run backtests across multiple tickers from a file
python batch_backtest.py -f stocks.txt

# Batch backtest with custom period
python batch_backtest.py -f watchlist.txt -p 6mo

# Custom output directory
python batch_backtest.py -f cmb.txt -p 24mo -o backtest_results

# Risk-managed batch backtesting (Item #5)
python batch_backtest.py -f stocks.txt --risk-managed

# Full example with all options
python batch_backtest.py -f watchlist.txt -p 12mo -o backtest_analysis --risk-managed

# Often Run
python batch_backtest.py -f ibd.txt -p 12mo

# Using --file (long form) also works
python batch_backtest.py --file stocks.txt --period 6mo
```

**Risk-Managed Batch Features:**
- Runs RiskManager on each ticker in the batch
- Generates individual risk-managed reports per ticker
- Aggregates R-multiples and exit type distributions
- Shows system-wide risk management effectiveness
- Identifies which tickers work best with risk management

### Advanced Options
```bash
# Multi-timeframe analysis (single ticker)
python vol_analysis.py GOOGL --multi

# Get help
python vol_analysis.py --help
```

## 📊 Backtesting Systems

### Single-Ticker Backtesting

The single-ticker backtesting feature validates signal performance by analyzing actual entry-to-exit trade pairs using historical data.

### **Entry-to-Exit Paired Analysis**

Matches each entry signal with its corresponding exit signal to simulate real trading:
- **Actual holding periods**: Real days between entry and exit
- **True returns**: Entry price to exit price performance
- **Strategy comparison**: Identifies most profitable entry/exit combinations
- **Real-world simulation**: Models how trades would actually execute

### **Sample Backtest Output**
```
═══════════════════════════════════════════════════════════════════
🎯 ENTRY-TO-EXIT STRATEGY ANALYSIS
═══════════════════════════════════════════════════════════════════

📊 OVERALL TRADING STATISTICS:
  Total Trades Generated: 18
  Closed Trades: 15
  Open Positions: 3

🚀 ENTRY STRATEGY COMPARISON:
  
  💎 Stealth Accumulation:
    Trades: 8 closed, 2 open
    Win Rate: 75.0% (6W-2L)
    Average Return: +4.23%
    Avg Win: +6.45% | Avg Loss: -1.78%
    Avg Holding Period: 18.5 days
    Profit Factor: 2.89
    ✅ GOOD - Strong positive edge

  🟢 Strong Buy:
    Trades: 5 closed, 1 open
    Win Rate: 80.0% (4W-1L)
    Average Return: +5.67%
    Avg Win: +7.12% | Avg Loss: -0.89%
    Avg Holding Period: 14.2 days
    Profit Factor: 3.21
    ✅ EXCELLENT - Highly profitable strategy

⭐ OPTIMAL STRATEGY COMBINATIONS:
  Best Entry Signal: ⭐ Multi-Signal Confluence
  Best Exit Signal: 🟠 Profit Taking
  
💡 RECOMMENDED STRATEGY:
  Entry: ⭐ Multi-Signal Confluence
  Exit: 🟠 Profit Taking
```

### **Key Metrics Explained**

- **Win Rate**: Percentage of profitable trades
- **Average Return**: Mean profit/loss per trade  
- **Profit Factor**: Ratio of gross profit to gross loss (>2.0 is excellent)
- **Expectancy**: Expected profit per trade (positive = profitable system)
- **Holding Period**: Average days from entry to exit

### **Best Practices**
- Past performance doesn't guarantee future results
- Focus on consistency across different periods
- Pay attention to win rate AND expectancy together
- Re-run backtests periodically as new data becomes available

### Batch Backtesting - Multi-Ticker Strategy Optimization

The `batch_backtest.py` module performs comprehensive strategy optimization by analyzing signal performance across multiple stocks simultaneously. This provides statistically robust insights into which entry and exit signals work best across different market conditions and stocks.

#### **What It Does**

- **Processes Multiple Tickers**: Runs backtests on all stocks in a ticker file
- **Aggregates Results**: Combines data across all tickers for comprehensive analysis
- **Ranks Strategies**: Identifies the most profitable entry and exit signal combinations
- **Statistical Validation**: Provides confidence levels based on sample size
- **Individual Reports**: Generates detailed reports for each ticker
- **Aggregate Optimization Report**: Creates a master report with strategy recommendations

#### **Independent Analysis Methodology**

The batch backtesting system uses a sophisticated approach where entry and exit signals are analyzed independently before being combined into optimal strategies:

**Independent Signal Analysis:**
- **Entry signals** are aggregated across ALL trades that used each signal type, regardless of which exit signal was used
- **Exit signals** are aggregated across ALL trades that used each signal type, regardless of which entry signal was used
- This independence allows evaluation of each signal's performance in isolation

**Strategy Combination:**
- The optimal strategy recommendation combines the best-performing entry and exit signals
- The "Combined Strategy Performance" shows results only for trades where BOTH the recommended entry AND exit signals occurred
- For example: "Moderate Buy" might show 151 total trades, "Profit Taking" might show 47 total uses, but their combination represents only the 26 trades where both signals occurred together

**Why This Approach:**
- Identifies which entry signals generate the most profitable opportunities
- Determines which exit signals most effectively preserve profits  
- Validates that the best individual signals also work well when combined
- Provides statistical confidence through large sample sizes for each signal type

#### **Command-Line Usage**

```bash
# Basic usage - analyze all tickers in file
python batch_backtest.py -f stocks.txt

# Specify analysis period
python batch_backtest.py -f watchlist.txt -p 6mo

# Custom output directory
python batch_backtest.py -f stocks.txt -o optimization_results

# Full example
python batch_backtest.py -f watchlist.txt -p 12mo -o backtest_analysis

# Using --file (long form) also works
python batch_backtest.py --file watchlist.txt --period 12mo
```

**Arguments:**
- `-f, --file`: Path to file with ticker symbols (one per line, comments with # supported) [REQUIRED]
- `-p, --period`: Analysis period (default: 12mo)
- `-o, --output-dir`: Directory for output reports (default: backtest_results)
- `--risk-managed`: Use RiskManager for P&L-aware exits

#### **Output Files Generated**

The batch backtesting process creates multiple output files:

**Individual Ticker Reports:**
- `{TICKER}_{PERIOD}_backtest_{TIMESTAMP}.txt` - One per ticker analyzed
- Contains complete backtest analysis for that specific stock
- Example: `AAPL_12mo_backtest_20241103_121500.txt`

**Aggregate Optimization Report:**
- `AGGREGATE_optimization_{PERIOD}_{TIMESTAMP}.txt`
- Master report combining all ticker data
- Example: `AGGREGATE_optimization_12mo_20241103_121530.txt`

All files are saved to the specified output directory (default: `backtest_results/`)

#### **Sample Aggregate Report Output**

```
═══════════════════════════════════════════════════════════════════
🎯 COLLECTIVE STRATEGY OPTIMIZATION REPORT
═══════════════════════════════════════════════════════════════════

📊 BATCH PROCESSING SUMMARY:
  Tickers Analyzed: 15
  Tickers Failed: 0
  Total Trades Generated: 245
  Closed Trades: 203
  Open Positions: 42

✅ Successfully Analyzed:
  AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META, NFLX, AMD, INTC, ...

═══════════════════════════════════════════════════════════════════
🚀 COLLECTIVE ENTRY STRATEGY ANALYSIS
═══════════════════════════════════════════════════════════════════

Ranked by Expected Value per Trade:

1. ⭐ Multi-Signal Confluence
   ──────────────────────────────────────────────────────────────
   Total Trades: 48 (42 closed, 6 open)
   Win Rate: 76.2% (32 wins, 10 losses)
   Average Return: +5.83%
   Median Return: +4.95%
   Avg Win: +8.12% | Avg Loss: -2.45%
   Best Trade: 2024-08-15 (+18.34%)
   Worst Trade: 2024-09-22 (-6.78%)
   Avg Holding: 16.8 days
   Profit Factor: 3.31
   Expectancy: +4.21%
   Rating: ⭐⭐⭐ EXCELLENT - Top tier strategy

2. 💎 Stealth Accumulation
   ──────────────────────────────────────────────────────────────
   Total Trades: 62 (55 closed, 7 open)
   Win Rate: 69.1% (38 wins, 17 losses)
   Average Return: +4.12%
   Median Return: +3.67%
   Avg Win: +7.45% | Avg Loss: -2.89%
   Best Trade: 2024-07-12 (+15.23%)
   Worst Trade: 2024-10-05 (-7.12%)
   Avg Holding: 19.3 days
   Profit Factor: 2.58
   Expectancy: +2.85%
   Rating: ⭐⭐ GOOD - Strong positive edge

═══════════════════════════════════════════════════════════════════
💡 OPTIMAL STRATEGY RECOMMENDATION
═══════════════════════════════════════════════════════════════════

🎯 RECOMMENDED ENTRY SIGNAL:
   ⭐ Multi-Signal Confluence
   • Win Rate: 76.2%
   • Expectancy: +4.21% per trade
   • Average Return: +5.83%
   • Profit Factor: 3.31
   • Based on 42 closed trades

🎯 RECOMMENDED EXIT SIGNAL:
   🟠 Profit Taking
   • Win Rate: 82.5%
   • Average Return: +6.45%
   • Profit Factor: 3.89
   • Based on 67 closed trades

📊 COMBINED STRATEGY PERFORMANCE:
   Trades: 28 closed
   Win Rate: 85.7%
   Average Return: +7.12%
   Expectancy: +6.18%
   Profit Factor: 4.23
   Avg Holding: 14.5 days
   ⭐⭐⭐ EXCEPTIONAL combined performance!

═══════════════════════════════════════════════════════════════════
📈 STATISTICAL SIGNIFICANCE
═══════════════════════════════════════════════════════════════════

  Total Sample Size: 203 closed trades
  ✅ Large sample - results are statistically robust
```

#### **Key Metrics Explained**

**Entry Strategy Metrics:**
- **Expectancy**: Expected profit per trade (most important metric)
- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Ratio of gross profit to gross loss (>2.0 is excellent)
- **Average Return**: Mean profit/loss per trade
- **Holding Period**: Average days from entry to exit

**Strategy Rankings:**
- Entries are ranked by **Expectancy** (expected value per trade)
- Exits are ranked by **Win Rate** (reliability)
- ⭐⭐⭐ EXCELLENT: Expectancy ≥2.0% AND Win Rate ≥65%
- ⭐⭐ GOOD: Expectancy ≥1.0% AND Win Rate ≥55%
- ⭐ FAIR: Expectancy ≥0.5% AND Win Rate ≥50%

**Statistical Significance:**
- ✅ Large sample (≥100 trades): Results are statistically robust
- ✓ Moderate sample (50-99 trades): Results reasonably reliable
- ⚠️ Small sample (20-49 trades): Use caution, may not be representative
- ❌ Very small sample (<20 trades): Results may not be reliable

#### **Interpretation Guide**

**Understanding the Aggregate Report:**

1. **Entry Strategy Rankings**: Shows which buy signals are most profitable across all stocks
   - Focus on signals with positive expectancy and high win rates
   - "Expectancy" tells you how much profit to expect per trade on average
   - Higher profit factors (>2.0) indicate stronger strategies

2. **Exit Strategy Rankings**: Shows which exit signals preserve profits best
   - Win rate is crucial for exits - you want to exit while ahead
   - Profit factors >2.0 indicate the signal helps lock in gains

3. **Combined Strategy**: Tests the optimal entry+exit combination
   - This shows real-world performance when using both signals together
   - Exceptional (⭐⭐⭐) combined performance validates the strategy

4. **Per-Ticker Breakdown**: Shows how strategies perform on individual stocks
   - Reveals if certain stocks favor specific signals
   - Helps identify stock-specific strategy adaptations

**Using the Results:**

- **For Trading**: Use the recommended entry and exit signals
- **Position Sizing**: Increase size on high-expectancy signals
- **Risk Management**: Pay attention to average loss figures for stop-loss placement
- **Validation**: Larger sample sizes provide more reliable results

#### **Best Practices for Batch Backtesting**

1. **Sample Size**: Use longer periods (12mo) or larger ticker lists for robust results
2. **Diversification**: Include stocks from different sectors and market caps
3. **Periodic Re-analysis**: Re-run quarterly as new data becomes available
4. **Combined Analysis**: Use both single-ticker and batch results together
5. **Market Conditions**: Consider analyzing different periods (bull vs bear markets)

#### **Ticker File Format**

Same format as batch processing:
```
AAPL
MSFT
GOOGL
# Technology sector
TSLA
NVDA

# Finance sector
JPM
GS
```

#### **Troubleshooting**

**"No closed trades available"**
- Try a longer analysis period (12mo or more)
- Ensure tickers have sufficient trading history
- Some tickers may have limited signals in shorter periods

**"Failed to process [TICKER]"**
- Invalid or delisted ticker symbol
- Insufficient data available from Yahoo Finance
- Failed tickers are listed in the report with error messages

**Low statistical significance warning**
- Use longer time periods to generate more trades
- Add more tickers to the analysis
- Results with <20 trades should be used cautiously

### Ticker File Format
Create a text file with one ticker symbol per line:
```
AAPL
MSFT
GOOGL
TSLA
NVDA
# Comments start with # and are ignored
AMZN
```

### Batch Processing Output
All files are saved to the `results/` directory by default.

**Individual Analysis Files**: `{TICKER}_{PERIOD}_{STARTDATE}_{ENDDATE}_analysis.txt`
- Example: `results/AAPL_6mo_20240404_20241003_analysis.txt`

**Chart Files** (when `--save-charts` used): `{TICKER}_{PERIOD}_{STARTDATE}_{ENDDATE}_chart.<ext>`
- `ext = png` when `--chart-backend matplotlib` (static image)
- `ext = html` when `--chart-backend plotly` (interactive chart from `../charts`)
- Example: `results/AAPL_6mo_20240404_20241003_chart.html`

**Summary Report**: `batch_summary_{PERIOD}_{TIMESTAMP}.txt`
- Example: `results/batch_summary_6mo_20241004_122312.txt`
- Contains ranked list of all processed tickers

### Available Time Periods
- `1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `10y`, `ytd`, `max`

## 🔄 Sector Rotation Dashboard (NEW - Nov 2025)

A comprehensive sector strength analysis system that helps identify leading and lagging sectors for optimal portfolio allocation. Uses the same volume analysis framework applied to sector ETFs.

### **What It Does**

The sector rotation dashboard analyzes 11 sector ETFs to identify which sectors are currently leading the market and deserve overweighting in your portfolio. This helps you:

- **Identify sector leaders** before the rotation is obvious
- **Avoid weak sectors** that drag down performance
- **Time sector rotations** using objective, data-driven signals
- **Adapt to market cycles** instead of being married to one sector

### **The 11 Sector ETFs Analyzed**

| ETF | Sector | Characteristics |
|-----|--------|----------------|
| XLK | Technology | Growth, innovation, high volatility |
| XLC | Communication Services | Tech-adjacent (Meta, Google, Netflix) |
| XLY | Consumer Discretionary | Consumer spending, economy-sensitive |
| XLF | Financials | Banks, insurance, interest rate sensitive |
| XLV | Healthcare | Pharma, biotech, defensive |
| XLI | Industrials | Manufacturing, infrastructure |
| XLE | Energy | Oil, gas, commodity-linked |
| XLB | Materials | Mining, commodities, cyclical |
| XLRE | Real Estate | REITs, interest rate sensitive |
| XLP | Consumer Staples | Defensive, stable earnings |
| XLU | Utilities | Most defensive, dividend-focused |

### **Sector Scoring System (0-14 Points)**

Each sector receives a comprehensive score based on three components:

#### **Momentum Score (6 points max)**
- Above 50-day MA: +2 points
- Above 200-day MA: +2 points
- 20-day return >5%: +2 points

#### **Volume Analysis Score (6 points max)**
*Requires backtest - use `sector_dashboard_with_backtest.py`*
- Win rate >60% on Moderate Buy signal: +2 points
- Positive expectancy: +2 points
- Recent signal activity (<14 days): +2 points

#### **Relative Strength Score (2 points max)**
- Outperforming SPY benchmark: +1 point
- Top-3 sector ranking: +1 point (bonus)

### **Command-Line Usage**

#### **Quick Analysis (Fast - No Backtest)**
```bash
# Basic 3-month sector analysis (momentum + relative strength only)
python sector_dashboard.py

# 6-month analysis
python sector_dashboard.py -p 6mo

# Show only top 5 sectors
python sector_dashboard.py --top 5

# Compare to previous run (detect rotations)
python sector_dashboard.py --compare

# Save detailed report
python sector_dashboard.py -o sector_reports
```

**Performance**: ~10 seconds (analyzes 11 sectors + SPY)

#### **Complete Analysis (Slow - With Volume Scoring)**
```bash
# Full analysis with backtesting (complete 14-point scoring)
python sector_dashboard_with_backtest.py

# First run takes 5-10 minutes
# Subsequent runs use 7-day cache (much faster!)

# Quick mode (skip backtest if needed)
python sector_dashboard_with_backtest.py --quick

# With comparison and saved report
python sector_dashboard_with_backtest.py --compare -o sector_analysis
```

**Performance**: 
- First run: ~5-10 minutes (runs backtests)
- Cached runs: ~10 seconds (backtests cached for 7 days)

### **Sample Dashboard Output**

```
🎯 SECTOR ROTATION DASHBOARD

Analysis Period: 3mo
Generated: 2025-11-09 19:00:00
Benchmark: SPY (S&P 500)

📊 SECTOR STRENGTH RANKING

🥇 RANK #1: XLK (Technology) - Score: 10/14 ⭐⭐⭐
   ──────────────────────────────────────────────────────────────────────
   Momentum Score: 6/6
     • Above 50-day MA: ✅ +2 (Price: $288.16, MA: $282.13)
     • Above 200-day MA: ✅ +2 (Price: $288.16, MA: $265.40)
     • 20-day Return: ✅ +2 (+8.5%)
   
   Volume Score: 2/6
     • Win Rate: ✅ +2 (68.5% vs 60% threshold)
     • Expectancy: ❌ 0 (-1.2%)
     • Recent Signals: ❌ 0 (23 days ago)
   
   Relative Strength: 2/2
     • vs SPY: ✅ +1 (+7.58% vs SPY +4.69%, +2.89%)
     • Top-3 Bonus: ✅ +1 (Rank #1)
   
   💡 RECOMMENDATION: OVERWEIGHT
   📊 Target Allocation: 35-50% of portfolio

🥈 RANK #2: XLV (Healthcare) - Score: 9/14 ⭐⭐⭐
   [Similar detailed breakdown]
   💡 RECOMMENDATION: OVERWEIGHT
   📊 Target Allocation: 35-50% of portfolio

[... Continue for all 11 sectors ...]

📈 RECOMMENDED PORTFOLIO ALLOCATION

Based on current sector strength scores:

LEADING SECTORS (Score 8-10): 70% Total Allocation
  • XLK (Technology): 42%
  • XLV (Healthcare): 28%

STRONG SECTORS (Score 6-7): 20% Total Allocation
  • XLI (Industrials): 20%

OPPORTUNISTIC (Score 4-5): 10% Total Allocation
  • XLE (Energy): 10%

AVOID (Score 0-3): 0% Allocation
  • XLF, XLB, XLRE, XLP, XLU, XLC, XLY

⚠️ ROTATION ALERTS

🚨 2 SIGNIFICANT CHANGES DETECTED:

📉 XLF (Financials): 7/14 → 4/14 (-3 points)
   💡 Action: Consider reducing exposure

🔥 XLE (Energy): 3/14 → 6/14 (+3 points)
   💡 Action: Potential entry opportunity
```

### **Interpreting the Results**

#### **Score Categories**

- **8-10 (LEADING)**: Overweight 35-50%
  - All green signals: momentum, volume, outperformance
  - These sectors should dominate your portfolio
  
- **6-7 (STRONG)**: Market weight 15-25%
  - Mostly positive signals, some weakness
  - Include but don't overallocate
  
- **4-5 (NEUTRAL)**: Light weight 5-10%
  - Mixed signals, proceed with caution
  - Small opportunistic positions only
  
- **0-3 (WEAK)**: Avoid 0%
  - Multiple red flags
  - Stay away completely

#### **Rotation Signals**

**When to Rotate INTO a Sector:**
- Score increases by 3+ points
- Score crosses above 6 (enters "strong" territory)
- Momentum score reaches 6/6 (all MAs positive)

**When to Rotate OUT OF a Sector:**
- Score drops by 3+ points
- Score falls below 6 (loses "strong" status)
- Momentum score drops to 0-2 (losing MA support)

### **Recommended Workflow**

#### **Weekly Review (Every Monday)**
```bash
# Quick 2-minute check
python sector_dashboard.py --compare --top 5

# If major changes detected (>3 point moves):
python sector_dashboard_with_backtest.py --compare
```

#### **Monthly Deep Dive (First Sunday)**
```bash
# Full 6-month analysis with saved report
python sector_dashboard_with_backtest.py -p 6mo -o monthly_reports

# Review allocation recommendations
# Rebalance portfolio based on new sector rankings
```

#### **Quarterly Validation**
```bash
# Run 12-month analysis for long-term perspective
python sector_dashboard_with_backtest.py -p 12mo --compare

# Validate that your portfolio sectors still score >6
# Make strategic shifts if sector leadership has changed
```

### **Practical Example - Using the Dashboard**

**Scenario**: You notice tech (XLK) dropping from 10/14 to 6/14

**Action Plan:**

1. **Identify new leaders** from dashboard
   ```bash
   python sector_dashboard.py --compare
   ```
   Result: Healthcare (XLV) now scores 9/14

2. **Reduce tech exposure**
   - Take profits on tech stocks showing Distribution Warning
   - Shift from 50% tech → 25% tech

3. **Build healthcare positions**
   - Run backtest on healthcare stocks
   ```bash
   python batch_backtest.py -f healthcare_stocks.txt -p 12mo
   ```
   - Enter positions showing Moderate Buy signals

4. **Monitor weekly**
   - Watch if tech recovers (score >6 again)
   - Watch if healthcare maintains leadership

### **Files Created**

- `sector_etfs.txt` - List of 11 sector ETFs
- `sector_rotation.py` - Core scoring algorithms
- `sector_dashboard.py` - Fast dashboard (no backtest)
- `sector_dashboard_with_backtest.py` - Complete dashboard (with backtest)
- `sector_cache/` - Cached backtest results and historical scores

### **Cache Management**

**Backtest Cache:**
- Location: `sector_cache/backtest_results_{period}.json`
- Validity: 7 days
- Auto-refresh: Runs new backtest if cache expired

**Score History:**
- Location: `sector_cache/scores_{period}_latest.json`
- Used for: `--compare` mode to detect rotations
- Updated: Every dashboard run

### **Integration with Stock Selection**

Once you identify leading sectors (score ≥6), use batch backtesting to find the best stocks within those sectors:

```bash
# 1. Dashboard identifies XLK (Tech) and XLV (Healthcare) as leaders

# 2. Run backtests on stocks in those sectors
python batch_backtest.py -f tech_stocks.txt -p 12mo
python batch_backtest.py -f healthcare_stocks.txt -p 12mo

# 3. Select stocks with:
#    - Moderate Buy win rate >60%
#    - Positive expectancy
#    - Recent signal activity

# 4. Monitor sectors weekly for rotation signals
python sector_dashboard.py --compare
```

### **Benefits of Sector Rotation**

Based on your backtest comparison:
- Your tech-heavy portfolio: +10.71% expectancy, 66.5% win rate
- Matt's diversified portfolio: +0.32% expectancy, 42.9% win rate

**The difference?** You focused on the leading sector (tech). The dashboard ensures you **always** focus on leading sectors, not just during tech bull markets.

### **Key Insights**

✅ **Sector matters more than stock selection** - Being in the right sector (tech) gave you 33x better results than being diversified across weak sectors

✅ **Rotation detection prevents giving back gains** - Exit tech when it weakens (score drops to <6) before the correction

✅ **Systematic rebalancing** - Removes emotion and guesswork from sector allocation

✅ **Works with your existing system** - Uses same volume analysis signals on sector ETFs

---

## 🎯 Sector-Aware Trading Strategy

**Purpose**: Adapt position sizing, entry frequency, and risk management based on current sector strength to optimize returns across all market environments.

### **Core Principle**

**Market environment dictates aggression level.** When sectors are strong (score ≥8/14), trade aggressively. When sectors are weak (score ≤5/14), trade defensively. This adaptive approach prevents giving back gains during market transitions.

### **Position Sizing Framework**

| Top Sector Score | Market Environment | Position Size | Cash Allocation | Entry Frequency |
|-----------------|-------------------|---------------|-----------------|-----------------|
| **≥10/14** | Elite bull market | 100-125%* | 10-15% | Aggressive - enter all Moderate Buy signals |
| **8-9/14** | Strong bull market | 90-100% | 15-20% | Normal - enter most Moderate Buy signals |
| **6-7/14** | Mixed/choppy market | 75-90% | 20-30% | Selective - best Moderate Buy setups only |
| **4-5/14** | Weak/transitional | 50-75% | 30-40% | Very selective - exceptional setups only |
| **≤3/14** | Very weak/defensive | 0-25% | 60-80% | Minimal - rare entries, mostly cash |

*125% = using margin on exceptional setups only when market leadership is crystal clear

### **Entry Qualification Matrix**

**Sector-aware entry rules ensure you're always trading with the market, not against it:**

| Sector Score | Stock Signal | Support Proximity | CMF | VWAP | Action | Size |
|--------------|--------------|-------------------|-----|------|--------|------|
| **≥8/14** | Moderate Buy | Any | Any | Above | ✅ ENTER | 100% |
| **≥8/14** | Weak Moderate Buy | Near support | >1.0σ | Above | ✅ ENTER | 75% |
| **6-7/14** | Moderate Buy | Near support | >1.0σ | Above | ✅ ENTER | 75% |
| **6-7/14** | Moderate Buy | Far from support | <0.5σ | Below | ❌ SKIP | - |
| **4-5/14** | Moderate Buy | Near support | >1.5σ | Above | ⚠️ CONSIDER | 50% |
| **4-5/14** | Moderate Buy | Any other | Any | Any | ❌ SKIP | - |
| **≤3/14** | ANY signal | ANY | ANY | ANY | ❌ SKIP | - |

**Key Requirements by Environment:**

**Strong Market (≥8/14):**
- ✅ Moderate Buy signal (required)
- ✅ Stock in top-scoring sector (required)
- → Enter with confidence

**Normal Market (6-7/14):**
- ✅ Moderate Buy signal (required)
- ✅ Near support (within 1 ATR) (required)
- ✅ Strong CMF (>1.0σ) (required)
- ✅ Above VWAP (required)
- → Enter if all criteria met

**Weak Market (4-5/14):**
- ✅ Moderate Buy signal (required)
- ✅ Near support (within 0.5 ATR) (required)
- ✅ Very strong CMF (>1.5σ) (required)
- ✅ Above VWAP (required)
- ✅ Additional confirmation (recent pivot, volume spike)
- → Only enter exceptional setups

**Very Weak Market (≤3/14):**
- ❌ **No new entries** - move to cash and wait for leadership

### **Risk Management Adjustments**

**Initial Stop Placement:**

| Market Environment | Stop Formula | Rationale |
|-------------------|-------------|-----------|
| Strong (≥8/14) | `min(swing_low - 0.5*ATR, VWAP - 1*ATR)` | Standard stops, give room |
| Normal (6-7/14) | `min(swing_low - 0.5*ATR, VWAP - 0.75*ATR)` | Slightly tighter |
| Weak (4-5/14) | `min(swing_low - 0.25*ATR, VWAP - 0.5*ATR)` | Tight stops, quick exit |
| Very Weak (≤3/14) | `VWAP - 0.25*ATR` | Very tight, minimal risk |

**Time Stops:**

| Market Environment | Bars Until Time Stop | Dead Position Threshold |
|-------------------|---------------------|------------------------|
| Strong (≥8/14) | 15 bars | <+0.5R after 15 bars |
| Normal (6-7/14) | 12 bars | <+1R after 12 bars |
| Weak (4-5/14) | 10 bars | <+1R after 10 bars |
| Very Weak (≤3/14) | 8 bars | <+0.5R after 8 bars |

**Profit Targets:**

| Market Environment | First Target | Amount | Trailing Stop |
|-------------------|-------------|--------|---------------|
| Strong (≥8/14) | +2R | 50% | 10-day low |
| Normal (6-7/14) | +2R | 50% | 10-day low |
| Weak (4-5/14) | +1.5R | 50% | 7-day low |
| Very Weak (≤3/14) | +1R | 100% | None - exit completely |

**Exit Signal Sensitivity:**

| Market Environment | Exit Signal Action |
|-------------------|-------------------|
| Strong (≥8/14) | Wait for confirmation (2+ exit signals) |
| Normal (6-7/14) | Act on first strong exit signal |
| Weak (4-5/14) | Exit on first Distribution Warning |
| Very Weak (≤3/14) | Exit on ANY exit signal |

### **Sector Selection Rules**

**Primary Rule**: Only consider stocks from sectors scoring ≥4/14

**Within qualifying sectors:**
1. **Focus 60-80%** of capital on the **top-scoring sector**
2. **Allocate 15-25%** to the **second-best sector** (if score ≥6/14)
3. **Keep 5-15%** in **third sector** as diversification (if score ≥6/14)
4. **Avoid completely** any sector scoring <4/14

**Example Current Market (Top = 5/14):**
```
XLK (Tech): 5/14        → 60% of deployed capital
XLV (Healthcare): 4/14  → 25% of deployed capital
XLE (Energy): 4/14      → 15% of deployed capital
All others: <4/14       → 0% allocation

With 50% position sizing and 40% cash:
- Tech positions: 30% of total capital (60% of 50%)
- Healthcare: 12.5% of total capital
- Energy: 7.5% of total capital
- Cash: 40%
- Total: 90% (10% buffer)
```

### **Weekly Monitoring Protocol**

**Every Monday Morning:**
```bash
# 1. Check sector strength
python sector_dashboard.py --compare --top 5

# 2. Identify top-scoring sector and its score
# 3. Adjust strategy for the week based on score:
```

**If score ≥8**: Resume normal aggressive trading  
**If score 6-7**: Trade normally but be selective  
**If score 4-5**: Defensive - small sizes, exceptional setups only  
**If score ≤3**: Very defensive - mostly cash, rare entries  

### **Monthly Rebalancing Protocol**

**First Sunday of Month:**
```bash
# 1. Full 6-month analysis
python sector_dashboard_with_backtest.py -p 6mo --compare -o monthly_reports

# 2. Review allocation recommendations
# 3. Check for rotation alerts (>3 point changes)
# 4. Rebalance portfolio:
```

**Rotation Triggers:**
- Sector drops >3 points: Reduce allocation by 50%
- Sector rises >3 points: Increase allocation by 50%
- Sector crosses below 6: Exit poorest-performing stocks
- Sector crosses above 6: Begin building positions

### **Real-World Example: Current Market (Top = 5/14)**

**Your Current Environment Analysis:**
```
Top Sector Score: 5/14
Market Environment: WEAK/TRANSITIONAL
Recommended Posture: DEFENSIVE
```

**Strategy Dictates:**
1. ✅ Position size: 50-75% (you should be using 50-75% of normal size)
2. ✅ Cash allocation: 30-40% (you should be holding significant cash)
3. ✅ Entry criteria: Only exceptional Moderate Buy setups
   - Must be near support (within 0.5 ATR)
   - Must have strong CMF (>1.5σ)
   - Must be above VWAP
4. ✅ Stop losses: Tight (VWAP - 0.5*ATR)
5. ✅ Time stops: 10 bars
6. ✅ Profit targets: +1.5R (take 50%), then trail with 7-day low
7. ✅ Exit signals: Exit on first Distribution Warning

**This is VERY DIFFERENT from when tech scored 10/14:**
- Then: Full size, aggressive, standard stops, +2R targets
- Now: Half size, selective, tight stops, +1.5R targets

**The sector score tells you HOW to trade, not WHETHER to trade.**

---

## 🎯 Implementation Validation

Once documented, you can validate code against strategy:

```python
# In risk_manager.py - should check sector score:
def calculate_position_size(account_value, risk_pct, entry_price, stop_price, sector_score):
    """
    Calculate position size based on risk and sector environment.
    
    Sector adjustments:
    - Score ≥8: Normal sizing (1.0x multiplier)
    - Score 6-7: Slightly reduced (0.85x multiplier)
    - Score 4-5: Defensive (0.65x multiplier)
    - Score ≤3: Minimal (0.25x multiplier)
    """
    # Standard calculation
    base_size = (account_value * risk_pct) / (entry_price - stop_price)
    
    # Apply sector adjustment
    if sector_score >= 8:
        multiplier = 1.0
    elif sector_score >= 6:
        multiplier = 0.85
    elif sector_score >= 4:
        multiplier = 0.65
    else:
        multiplier = 0.25
    
    return base_size * multiplier
```

Should I add all this strategy documentation to README, guide, and create the comprehensive strategy document?
</response>

### **Three-Panel Layout**

#### **Top Panel: Price Action with Signals**
- **Black line**: Stock price
- **Purple dashed line**: VWAP (Volume Weighted Average Price)
- **Gray dotted line**: Support level (20-day rolling low)
- **Signal markers**: See signal types below

#### **Middle Panel: Volume Indicators**
- **Blue line**: On-Balance Volume (OBV)
- **Orange line**: Accumulation/Distribution Line
- **Dashed lines**: Moving averages of OBV and A/D Line
- **Markers**: Divergence signals overlaid on indicators

#### **Bottom Panel: Volume & Accumulation Score**
- **Color-coded bars**: Volume with phase identification
- **Purple line**: Accumulation confidence score (0-10 scale)
- **Horizontal threshold lines**: Buy zones at scores 3, 5, and 7

## 🎯 Complete Signal System Explained

### **ENTRY SIGNALS**

#### **🟢 Strong Buy Signals (Large Green Dots)**
**Criteria**: Score ≥7, near support, above VWAP, moderate volume (1.2-3.0x average)
- **Meaning**: Highest confidence accumulation opportunity
- **Action**: Prime entry point for accumulation

#### **🟡 Moderate Buy Signals (Medium Yellow Dots)**
**Criteria**: Score 5-7, divergence signals, above VWAP
- **Meaning**: Good accumulation opportunity with some risk
- **Action**: Consider entry with position sizing

#### **~~💎 Stealth Accumulation (Cyan Diamonds)~~ - ❌ DEPRECATED**
**Status**: FAILED OUT-OF-SAMPLE VALIDATION (22.7% win rate vs 53.2% expected)
- **DO NOT USE** until redesigned and re-validated
- **See**: OUT_OF_SAMPLE_VALIDATION_REPORT.md for details
- Signal showed severe overfitting - worked on training data but failed on new data

#### **⭐ Multi-Signal Confluence (Magenta Stars)**
**Criteria**: Multiple indicators aligned (Score ≥6, support, volume, VWAP, divergences)
- **Meaning**: Strongest possible accumulation signal
- **Action**: High-conviction entry point

#### **🔥 Volume Breakout (Orange Triangles)**
**Criteria**: Score ≥5, volume >2.5x average, price up, above VWAP
- **Meaning**: Accumulation with momentum breakout
- **Action**: Momentum-based entry

### **EXIT SIGNALS**

#### **🟠 Profit Taking (Orange Dots)**
**Criteria**: New 20-day highs, high volume (>1.8x), above VWAP, but accumulation waning (<4)
- **Meaning**: Take profits on strength before momentum fades
- **Action**: Consider taking partial profits

#### **⚠️ Distribution Warning (Gold Squares)**
**Criteria**: Distribution phase, below VWAP, above average volume, declining A/D line
- **Meaning**: Early warning signs of institutional selling
- **Action**: Prepare exit strategy, monitor closely

#### **🔴 Sell Signals (Red Dots)**
**Criteria**: Distribution phase, below VWAP, breaking support, declining OBV and A/D line
- **Meaning**: Strong institutional selling pressure detected
- **Action**: Consider exit or avoid entry

#### **💜 Momentum Exhaustion (Purple X's)**
**Criteria**: Price rising but volume declining, low accumulation, extended above MA
- **Meaning**: Volume/price divergence indicating exhaustion
- **Action**: Prepare for potential reversal

#### **🛑 Stop Loss Triggers (Dark Red Triangles)**
**Criteria**: Below support, high volume breakdown, below VWAP and 5-day MA
- **Meaning**: Urgent exit signal for risk management
- **Action**: Immediate exit consideration

## 🏗️ Modular Architecture (Item #7: Refactor/Integration)

The system is built with a clean modular architecture for maintainability and testability:

### **Core Modules**

**`vol_analysis.py`** - Main orchestrator
- Entry point and CLI interface
- Coordinates all analysis modules
- Handles data fetching and caching

**`swing_structure.py`** - Swing analysis (NEW)
- Pivot high/low detection
- Swing-based support/resistance
- Volatility-aware proximity signals
- Swing failure pattern detection

**`volume_features.py`** - Volume analysis (NEW)
- Chaikin Money Flow (CMF) calculation
- Volume spike detection
- Event day identification (earnings/news)
- Volume-price divergence analysis

**`indicators.py`** - Core technical indicators (REFACTORED)
- Anchored VWAP from meaningful pivots
- ATR (Average True Range) calculation
- Z-score normalization for features
- Pre-trade quality filters

**`signal_generator.py`** - Signal logic
- Entry signal generation (5 types)
- Exit signal generation (5 types)
- Accumulation and exit scoring
- Operates on DataFrame columns (module-agnostic)

**`chart_builder.py`** - Visualization
- 3-panel analysis charts
- Signal marker placement
- Swing level visualization

**`risk_manager.py`** - Risk management
- Position sizing (0.5-1% risk per trade)
- Stop placement and trailing stops
- Profit scaling at +2R
- Complete trade lifecycle management

**`regime_filter.py`** - Market regime validation
- SPY 200-day MA checks
- Sector ETF 50-day MA checks
- Signal filtering based on market health

### **Testing Framework**

**`test_swing_structure.py`** - Swing module tests
- Pivot detection validation
- Swing level accuracy
- Proximity signal correctness

**`test_volume_features.py`** - Volume module tests
- CMF calculation validation
- Event detection accuracy
- Volume divergence detection

**`test_risk_manager.py`** - Risk management tests
- Position sizing validation
- Exit condition testing
- Trade lifecycle simulation

### **Benefits of Modular Design**
- ✅ **Maintainability**: Easy to update individual features
- ✅ **Testability**: Comprehensive unit test coverage
- ✅ **Reusability**: Modules can be used independently
- ✅ **Clarity**: Clear separation of concerns
- ✅ **Scalability**: Easy to add new features without tangling

## 📊 Technical Indicators Used

### **Chaikin Money Flow (CMF)** - Primary Volume Indicator
- Single unified volume flow indicator (replaces OBV + A/D Line)
- **Formula**: Weighted by close position within daily range
- **Range**: -1.0 (selling pressure) to +1.0 (buying pressure)
- **Z-Score Normalized**: Consistent thresholds across stocks
- **Usage**: CMF >1.0σ = strong buying, CMF <0 = momentum failure

### **Anchored VWAP** - Smart Money Indicator
- VWAP anchored from most recent swing pivot low
- Represents institutional cost basis from turning points
- **Above VWAP**: Price above institutional cost basis (bullish)
- **Below VWAP**: Price below institutional cost basis (bearish)
- **Advantage**: More meaningful than arbitrary chart-start VWAP

### **Swing-Based Support/Resistance**
- Support = Most recent confirmed pivot low (not rolling min)
- Resistance = Most recent confirmed pivot high (not rolling max)
- **Volatility-Aware Proximity**: Within 1 ATR of level (adaptive)
- **Significance**: Actual defended levels, not arbitrary rolling periods

### **Average True Range (ATR)**
- Measures market volatility
- Used for event detection (ATR spikes >2.5x = news/earnings)
- Used for stop placement and proximity normalization
- 20-period rolling average of True Range

### **Feature Standardization**
- All features converted to z-scores for consistent weighting
- Volume, CMF, TR, ATR normalized to standard deviations
- **Benefits**: Cross-stock consistency, balanced scoring, optimization-friendly

### **Dual Scoring System**

#### **Entry Score (0-10 scale)**
Points awarded for:
- **A/D Line divergence**: +2 points
- **OBV trend divergence**: +2 points  
- **Volume spike**: +1 point
- **Above VWAP**: +1 point
- **Near support**: +1 point

#### **Exit Score (1-10 scale)**
Points awarded for:
- **Distribution phase**: +2 points
- **Below VWAP**: +1.5 points
- **Below support**: +2 points
- **High volume (>2.5x)**: +1.5 points
- **Declining A/D line**: +1 point
- **Declining OBV**: +1 point
- **Low accumulation**: +1 point

**Final scores**: Normalized and clipped to respective scales

## 🎯 Stealth Accumulation Ranking System (NEW)

The batch processing feature uses a **Recent Stealth Activity Score** instead of traditional averages to identify stocks with fresh institutional buying that haven't broken out yet.

### **Stealth Scoring Algorithm (0-10 scale)**

**Recent Stealth Signals** (0-4 points):
- Counts stealth accumulation signals in the last 10 trading days
- Multiple recent signals = higher score

**Signal Recency** (0-3 points):
- Days since the last stealth accumulation signal
- More recent signals = higher score
- Recent (≤2 days) gets maximum points

**Price Containment** (0-3 points):
- Price appreciation during the stealth accumulation period
- Lower price gains = higher score (ideal for stealth buying)
- ≤2% gain = 3 points, ≤5% gain = 2 points, ≤10% gain = 1 point

### **Batch Processing Ranking Display**
```
🎯 TOP STEALTH ACCUMULATION CANDIDATES (by recent activity):
   1. AMZN  - Stealth:  8.0/10 🎯 (Last: Recent, Recent: 1, Price: +0.0%, Total: 1)
   2. AI    - Stealth:  5.3/10 💎 (Last: Recent, Recent: 1, Price: +9.5%, Total: 1)
   3. MSFT  - Stealth:  0.0/10 💤 (Last: None, Recent: 0, Price: +0.0%, Total: 0)
```

**Explanation**:
- **Stealth Score**: Recent activity score (0-10)
- **Last**: Days since last stealth signal ("Recent" = ≤2 days)
- **Recent**: Count of stealth signals in last 10 days
- **Price**: Price change during stealth accumulation period
- **Total**: Total stealth signals across entire analysis period

### **Stealth Score Emojis**
- 🎯 **7-10**: High recent stealth activity - prime candidates
- 💎 **5-7**: Moderate recent stealth activity
- 👁️ **3-5**: Low recent stealth activity
- 💤 **0-3**: No meaningful recent stealth activity

## 🔍 Multi-Timeframe Analysis

Use the `--multi` flag to analyze across multiple timeframes:

```bash
python vol_analysis.py AAPL --multi
```

**Analyzes**: 1-month, 3-month, 6-month, and 1-year periods
**Output**: Consensus strength rating and average accumulation activity

**Interpretation**:
- **🔥 VERY STRONG**: Average score ≥6 across timeframes
- **⚡ STRONG**: Average score ≥4 across timeframes  
- **💡 MODERATE**: Average score ≥2 across timeframes
- **❄️ WEAK**: Average score <2 across timeframes

## 📋 Sample Output Interpretation

```
🎯 ENTRY SIGNAL SUMMARY:
  🟢 Strong Buy Signals: 2 (Large green dots - Score ≥7, near support, above VWAP)
  🟡 Moderate Buy Signals: 5 (Medium yellow dots - Score 5-7, divergence signals)
  💎 Stealth Accumulation: 3 (Cyan diamonds - High score, low volume)
  ⭐ Multi-Signal Confluence: 1 (Magenta stars - All indicators aligned)
  🔥 Volume Breakouts: 0 (Orange triangles - 2.5x+ volume)

🚪 EXIT SIGNAL SUMMARY:
  🟠 Profit Taking: 1 (Orange dots - New highs with waning accumulation)
  ⚠️ Distribution Warning: 0 (Gold squares - Early distribution signs)
  🔴 Sell Signals: 0 (Red dots - Strong distribution below VWAP)
  💜 Momentum Exhaustion: 0 (Purple X's - Rising price, declining volume)
  🛑 Stop Loss Triggers: 0 (Dark red triangles - Support breakdown)
```

**Analysis**: This shows a stock in accumulation phase with multiple entry signals, minimal exit pressure, and one profit-taking opportunity. Low exit score indicates position is stable for continued holding.

## 🔧 Cache Schema Management

The system now includes advanced cache data versioning and integrity validation to ensure reliable data storage and compatibility across system updates.

### **Schema Features**

#### **Metadata Headers**
Each cache file now includes comprehensive metadata:
```
# Volume Analysis System - Cache File
# Generated: 2025-11-03T11:01:50.123456
# Metadata (JSON format):
# {
#   "schema_version": "1.0.0",
#   "creation_timestamp": "2025-11-03T11:01:50.123456",
#   "ticker_symbol": "AAPL",
#   "data_source": "yfinance",
#   "interval": "1h",
#   "auto_adjust": true,
#   "data_checksum": "a1b2c3d4e5f67890",
#   "record_count": 154,
#   "start_date": "2024-10-16T09:30:00",
#   "end_date": "2024-10-16T16:00:00"
# }
```

#### **Data Integrity Validation**
- **Checksum Verification**: SHA-256 checksums detect data corruption
- **Column Validation**: Ensures required columns (Open, High, Low, Close, Volume) are present
- **Type Validation**: Verifies correct data types for all columns
- **Index Validation**: Confirms datetime index format and timezone consistency

#### **Automatic Migration**
- **Legacy Detection**: Automatically identifies files without schema metadata
- **Safe Backup**: Creates `.backup` files before migration
- **Batch Processing**: Migrates multiple files efficiently
- **Validation**: Verifies successful migration with integrity checks

### **Migration Utility Output**
```
🔄 CACHE MIGRATION UTILITY
📁 Found 19 cache files
📋 Current schema version: 1.0.0

📊 MIGRATION SUMMARY:
   🟢 Already current: 0 files
   🟡 Needs migration: 19 files
   🔴 Errors found: 0 files

🚀 STARTING MIGRATION of 19 files...
[ 1/19] Migrating AAPL (1h)...
   ✅ Successfully migrated AAPL (1h)

📈 MIGRATION RESULTS:
   ✅ Successful: 19 files
   ❌ Failed: 0 files

🎉 Migration completed! 19 files upgraded to schema v1.0.0
```

## 🛠️ Troubleshooting

### **Common Issues**

#### **"No module named 'yfinance'"**
```bash
pip install yfinance
```

#### **Flat-lined accumulation scores / All NaN values**
- **Cause**: Insufficient data for CMF z-score calculation
- **Solution**: Use minimum 2-month period (`-p 2mo` or longer)
- **Explanation**: CMF needs 20 days + z-score needs 20 days = 40 days minimum
- **Recommended**: Use 3mo or longer periods for reliable scores

#### **Charts too small/large**
- Chart size optimized for 16-inch Mac displays
- Modify `figsize=(12, 9)` in code if needed

#### **Emoji warnings in plots**
- Cosmetic font warnings, doesn't affect functionality
- Charts will display properly despite warnings

#### **Invalid ticker symbol**
```
❌ Error analyzing XYZ: No data found, symbol may be delisted
```
- Verify ticker symbol is correct and actively traded
- Use proper exchange format (e.g., `BRK-A` not `BRKA`)

#### **Cache Migration Issues**
```
❌ Migration failed for TICKER: Missing required columns
```
- Some legacy files may be corrupted or incomplete
- Failed files will be automatically redownloaded when accessed
- Run `python migrate_cache.py --validate` to check file integrity

#### **Schema Validation Errors**
```
⚠️ Schema validation failed for TICKER - will redownload
```
- Indicates data corruption or format incompatibility
- Files are automatically removed and fresh data will be downloaded
- No user action required - system handles this automatically

### **Performance Tips**
- Use shorter periods (`3mo`, `6mo`) for faster analysis
- Daily intervals only - simplified for closing price analysis
- Longer periods provide more reliable signals

## 💡 Tips for Best Results

### **Signal Quality**
- **Look for clusters**: Multiple signals in same area = higher confidence
- **Confirm with volume**: Best signals have supporting volume patterns
- **Watch divergences**: OBV/A/D rising while price flat = accumulation

### **Complete Trading System**
- **Entry Strategy**: Use entry signals (🟢🟡💎⭐🔥) for position initiation
- **Exit Strategy**: Monitor exit signals (🟠⚠️🔴💜🛑) for position management
- **Signal Transitions**: Watch for Entry→Hold→Exit phase changes

### **Exit Score Interpretation**
- **8-10**: � URGENT - Consider immediate exit
- **6-8**: ⚠️ HIGH RISK - Reduce position size significantly
- **4-6**: 💡 MODERATE RISK - Monitor closely
- **2-4**: ✅ LOW RISK - Normal monitoring
- **1-2**: 🟢 MINIMAL RISK - Position looks healthy

## � Further Reading

- **On-Balance Volume**: [Investopedia OBV](https://www.investopedia.com/terms/o/onbalancevolume.asp)
- **Accumulation/Distribution**: [A/D Line Explanation](https://www.investopedia.com/terms/a/accumulationdistribution.asp)
- **VWAP Trading**: [Volume Weighted Average Price](https://www.investopedia.com/terms/v/vwap.asp)

## 📄 License

This tool is provided for educational and research purposes. Not financial advice.

---

**Happy Trading! 📈**
