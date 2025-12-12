# 📊 Advanced Stock Volume Analysis

Python toolkit for analyzing accumulation/distribution behavior, running disciplined backtests, and managing cache-heavy data workflows.

---

## Table of Contents
1. [Overview](#overview)
2. [Quick Start & Commands](#quick-start--commands)
3. [Validation Status](#validation-status)
4. [CLI Options](#cli-options)
5. [Documentation Map](#documentation-map)
6. [Support](#support)

---

## Overview

- **Signals**: Moderate Buy (production), Strong Buy & Confluence (experimental), Exit suite (profit taking, distribution, stops).
- **Visualization**: Three-panel charts with emoji markers, CMF divergences, and threshold overlays (`chart_builder.py`, `chart_builder_plotly.py`).
- **Backtests**: Batch and single-ticker runs with risk-managed variants (`batch_backtest.py`, `risk_manager.py`).
- **Cache system**: Bulk ingestion from Massive.com with schema-aware migrations and duplicate detection (`populate_cache_bulk.py`).
- **Sector toolkit**: `sector_dashboard*.py` and `TRADING_STRATEGY_SECTOR_AWARE.md` align exposure with sector strength.

Need the deeper architecture or indicator breakdown? See `docs/ARCHITECTURE_REFERENCE.md`.

---

## Quick Start & Commands

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
2. **Populate cache (start small, then scale)**
   
   **Option A: Yahoo Finance (Recommended - No credentials needed)**
   ```bash
   # Populate all known ticker files with 1 month
   python populate_cache.py --all -m 1
   
   # Populate specific ticker file with 6 months
   python populate_cache.py -f ticker_lists/ibd.txt -m 6
   
   # Quick daily update (5 days) - ideal for keeping cache current
   python populate_cache.py  -d 5 -f ticker_lists/ibd50-nov-29.txt 
   python populate_cache.py  -d 5 -f ticker_lists/indices.txt
   python populate_cache.py  -d 7 -f ticker_lists/sector_etfs.txt
   
   # Update with 30 days of data
   python populate_cache.py --file stocks.txt -d 30
   
   # Scale up to 24 months for full history
   python populate_cache.py --all -m 24
   ```
   
   **Option B: Massive.com (Advanced - Requires AWS S3 credentials and massive.com subscription)**
   ```bash
   # For users with Massive.com access (faster bulk downloads)
   # Single ticker (NEW - convenient for testing/updates)
   python populate_cache_bulk.py --ticker AAPL --months 24 --use-duckdb
   
   # Default: uses ticker_lists/stocks.txt
   python populate_cache_bulk.py --months 1
   
   # Specify different ticker file(s)
   python populate_cache_bulk.py --months 24 --ticker-files ticker_lists/ibd20.txt
   
   # Use multiple ticker files
   python populate_cache_bulk.py --months 12 --ticker-files ticker_lists/indices.txt ticker_lists/sector_etfs.txt

   # Use a date range for catching up the last few days
   python populate_cache_bulk.py --start 2020-12-05 --end 2025-12-05 --ticker-files ticker_lists/indices.txt ticker_lists/sector_etfs.txt
   ```
   
   **⚡ Performance Optimization (Optional - 10-20x faster for Massive.com users):**
   ```bash
   # Build DuckDB index once (30-60 seconds, one-time operation)
   python scripts/build_massive_index.py
   
   # Then use fast mode (4-8 min vs 41-84 min for 24 months, 50 tickers)
   python populate_cache_bulk.py --months 24 --use-duckdb
   python populate_cache_bulk.py --months 24 --use-duckdb --ticker-files ticker_lists/ibd50-nov-29.txt 
   python populate_cache_bulk.py --months 24 --use-duckdb --ticker-files ticker_lists/nasdaq100.txt
   python populate_cache_bulk.py --months 24 --use-duckdb --ticker-files ticker_lists/sp100.txt
   ```
   > 📖 **Details**: See `docs/DUCKDB_OPTIMIZATION.md` for complete guide
   
   > 💡 **New users**: Start with Option A (Yahoo Finance). It works immediately without any setup.
   > Option B is for advanced users with Massive.com subscriptions who need to backfill years of data quickly.

3. **🚀 Complete Single-Ticker Workflow (NEW)**
   ```bash
   # All-in-one: Cache → Analysis → Backtest → HTML Chart
   # Default: 24 months, conservative config, $100K account
   python single_ticker_workflow.py AAPL
   
   # Custom time period
   python single_ticker_workflow.py NVDA --months 36
   
   # With specific configuration
   python single_ticker_workflow.py TSLA --config configs/aggressive_config.yaml
   
   # Skip cache if already populated
   python single_ticker_workflow.py MSFT --skip-cache
   
   # Custom account parameters
   python single_ticker_workflow.py GOOGL --account-value 50000 --risk-pct 1.0
   
   # All outputs saved to results/TICKER/ directory:
   #   • Interactive HTML chart (plotly)
   #   • Risk-managed backtest report
   #   • Signal analysis summary
   ```
   
   **Workflow Steps**:
   1. Populate cache from massive_cache (DuckDB fast mode)
   2. Run volume analysis with signal generation
   3. Execute risk-managed backtest
   4. Generate interactive HTML chart
   5. Save all outputs to organized directory
   
   **Best for**: Quick single-ticker analysis with all outputs in one command.

4. **Run analysis & dashboards**
   ```bash
   # Single ticker analysis
   python vol_analysis.py NBIX --period 6mo

   # Batch processing with various output options
   python vol_analysis.py --file ticker_lists/stocks.txt --period 12mo --save-charts
   python vol_analysis.py --file ticker_lists/ibd.txt --period 6mo --save-excel --save-charts
   python vol_analysis.py  --period 24mo --chart-backend plotly --save-charts --file cmb.txt --save-excel
   python vol_analysis.py  --period 12mo --chart-backend plotly --save-charts --file ticker_lists/ibd50-nov-29.txt   
   
   # 🚀 OPTIMIZED: Charts generated ONLY for actionable tickers (80-90% faster)
   # Actionable = Active signals meeting empirical thresholds
   # - Moderate Buy (≥6.5 threshold, 64.3% win rate)
   # - Strong Buy / Confluence (always actionable when active)
   # - Stealth Accumulation (≥4.5 threshold, 58.7% win rate)
   # - Profit Taking (≥7.0 threshold, 96.1% win rate)
   # Example: 100 tickers → ~10-15 charts vs 100 charts (saves 8-15 minutes)
   
   # Excel export provides complete DataFrame access (60+ columns)
   # Includes: OHLCV, indicators, signals, scores, regime data
   # Two sheets: Analysis_Data (raw) + Summary (key metrics)
   python vol_analysis.py --file ticker_lists/short.txt --save-excel --output-dir custom_results

   # Batch backtest a watchlist
   python batch_backtest.py  -p 36mo  --no-individual-reports -f ticker_lists/ibd50-nov-29.txt
   # Risk-managed runs default to static stops (optimal performance validated Nov 2025)
   # Override via --stop-strategy if testing alternatives

   # Sector dashboards
   python sector_dashboard.py --top 5 --compare
   python sector_dashboard_with_backtest.py --top 5

   # Variable stop loss testing (4,249 trades validated)
   python test_variable_stops.py --file cmb.txt --period 2y
   python test_variable_stops.py --tickers AAPL MSFT --strategies static vol_regime time_decay
   
   # Momentum screening (RS Velocity + VCP)
   python momentum_screener.py --file ticker_lists/ibd20.txt
   python momentum_screener.py --file ticker_lists/sp100.txt --output sp100_momentum.csv
   python momentum_screener.py --tickers AAPL MSFT GOOGL --period 18mo
   ```

Need the full operational routine (daily/monthly/quarterly)? See `docs/USER_PLAYBOOK.md`.

---

## Momentum Screening (NEW)

Identify "Momentum Ignition" candidates using RS Velocity and Volatility Contraction Patterns:

```bash
# Quick test with 4 tickers
python momentum_screener.py --file ticker_lists/short.txt

# Screen IBD 20 stocks
python momentum_screener.py --file ticker_lists/ibd20.txt

# Screen S&P 100 with custom output
python momentum_screener.py --file ticker_lists/sp100.txt --output sp100_momentum.csv

# Direct ticker screening
python momentum_screener.py --tickers AAPL MSFT GOOGL --period 18mo
```

**Screening Criteria**:
1. **RS Velocity Increasing**: 10-day RS slope > 50-day RS slope (momentum accelerating)
2. **VCP Active**: Current volatility < 50% of 20-day average (tight consolidation)
3. **Above 200-day SMA**: Price > 200-day simple moving average (trend confirmed)
4. **Liquidity OK**: 20-day average volume > 500,000 shares

**Output**: Console table + timestamped CSV with full metrics

**Prerequisites**: All tickers must be cached. Requires minimum 250 trading days of data.

**Documentation**: See `docs/MOMENTUM_SCREENER.md` for complete methodology, interpretation guide, and workflows.

---

## Performance Analysis & Optimization

After running backtests, use these tools to evaluate and optimize your strategy:

### Professional Evaluation
```bash
# Calculate institutional-grade metrics (Sharpe, drawdown, etc.)
python analyze_professional_metrics.py --csv backtest_results/LOG_FILE_passed_12mo_conservative_20251211_215934.csv
```
**Outputs:** Sharpe ratio (3.35), maximum drawdown (-9.37%), monthly consistency (73.9%),  
loss streaks (16 max), professional grading (Institutional Quality: Grade A-)

**Use when:** Evaluating system for real money trading, comparing to professional standards

### Signal Optimization
```bash
# Find optimal thresholds and best-performing signals
python analyze_trade_quality.py backtest_results/LOG_FILE_cmb_24mo.csv -o backtest_results
```
**Outputs:** Threshold analysis, signal comparisons, entry-exit pairings, visualizations (charts/heatmaps)

**Use when:** Deciding which signals to trade, tuning score thresholds, optimizing entry criteria

### Portfolio Sizing
```bash
# Understand if you should trade 10, 25, or 40 tickers
# First run sensitivity test:
python test_portfolio_size_sensitivity.py
# Then analyze:
python analyze_portfolio_decomposition.py
```
**Outputs:** Volume vs sizing effect decomposition, trade quality by portfolio size

**Use when:** Deciding optimal ticker count, understanding concentration vs diversification trade-offs

### Realistic Expectations
```bash
# Calculate weighted expected returns by exit path frequency
python calculate_realistic_expectations.py
```
**Outputs:** Entry-exit frequency matrix, weighted expectations, best-case vs typical-case comparison

**Use when:** Setting performance expectations, understanding exit path probabilities

### Understanding Results
```bash
# Explains why exit returns differ from entry returns
python explain_exit_returns.py
```
**Outputs:** Educational explanation of entry vs exit metrics

**Use when:** Confused about why exit signal returns are higher than entry returns

For detailed script purposes and overlap analysis, see `ANALYSIS_SCRIPTS_OVERLAP.md`.

---

## Validation Status

- **Moderate Buy** – ✅ Live, expect +9% median returns with conservative config (70% win rate, +13.35% expectancy).
- **Signal Threshold Optimization** – ✅ **EMPIRICALLY VALIDATED (Dec 1, 2025)**: 434 trades analyzed
  * **Conservative Config (6.5 threshold)**: 70% win rate, +13.35% expectancy, +9.16% median return — **NEW DEFAULT**
  * Base Config (6.0 threshold): 68% win rate, +9.17% expectancy, +6.24% median return (45% worse expectancy)
  * Optimal threshold analysis shows 7.5 threshold best (71% win, +14.08% expectancy, 317 trades)
  * **Key finding**: Raising threshold from 6.0→6.5 improves expectancy 45% with only 10% fewer trades
  * Conservative_config now auto-loads in vol_analysis.py and batch_backtest.py
- **Configuration System** – ✅ **VALIDATED (Nov 27, 2025)**: 6 configurations tested on 24 tickers, 36-month period
  * **BALANCED (RECOMMENDED for mixed portfolios)**: +90.75% return, -12.09% drawdown, **7.51 return/DD ratio**
  * Conservative: +121.92% return, -31.73% drawdown (highest returns, painful drawdowns)
  * Base: +68.21% return, -11.86% drawdown (smoothest equity curve - historical reference only)
  * **Key finding**: 20-bar time stops optimal (vs 0, 8, or 12 bars)
  * See `PROJECT-STATUS.md` for complete analysis
- **Variable Stop Loss** – ✅ Two-phase validation:
  * **Phase 1 (Historical)**: 4,249 trades tested 5 variable strategies. Time Decay best among variables: +22% improvement (1.52R vs 1.25R other variables)
  * **Phase 2 (Nov 2025)**: 982 trades, 36-month full validation proved **static stops superior to ALL variables**
  * **Current Recommendation**: Use static stops (see Stop Strategy below)
- **Stop Strategy** – ✅ **CRITICAL UPDATE (Nov 2025)**: Validated across 982 trades, 36-month period
  * **STATIC (RECOMMENDED)**: $161,278 P&L, 15% stop rate, $417/trade avg — **New default**
  * Time_decay: $53,359 P&L, 23% stop rate (3x worse than static) — **Not recommended**
  * Vol_regime: $146,572 P&L, 32% stop rate (excessive stops) — **Not recommended**
  * **Key finding**: Variable stops tighten too aggressively, cutting winners short
  * See `STOP_STRATEGY_VALIDATION.md` for complete analysis
- **Stealth Accumulation** – ❌ Failed out-of-sample; do not use.
- **Others (Strong Buy, Confluence, Breakout)** – 🚧 Require fresh validation.

Full details and review cadence live in `docs/VALIDATION_STATUS.md`.

---

## CLI Options

### `vol_analysis.py`
- `ticker` (positional): default `AAPL`; ignored when `--file` is used.
- `-f` / `--file`: batch mode ticker file.
- `-p` / `--period`: analysis period (e.g., `6mo`, `24mo`, `ytd`).
- `-o` / `--output-dir`: batch output directory (default `results_volume`).
- `--config` / `-c`: **NEW** Path to YAML configuration file (e.g., `configs/aggressive_config.yaml`). Applies signal thresholds and all config settings.
- `--save-charts`: store PNG/HTML charts during batch runs.
- `--all-charts`: generate charts for ALL tickers in batch mode (default: only actionable signals). Actionable tickers have active signals meeting empirical thresholds (Moderate Buy ≥6.5, Profit Taking ≥7.0, etc.). Using this flag increases processing time 5-10x but provides complete portfolio visibility.
- `--save-excel`: save Excel files with complete DataFrame data (requires openpyxl: pip install openpyxl).
- `--chart-backend {matplotlib,plotly}`: control renderer (default `matplotlib`).
- `--data-source {yfinance,massive}`: select data provider.
- `--stop-strategy {static,vol_regime,atr_dynamic,pct_trail,time_decay}`: choose risk-managed stop logic (default `static` - RECOMMENDED). Performance: static=$161k/15% stops, time_decay=$53k/23% stops, vol_regime=$147k/32% stops. See `STOP_STRATEGY_VALIDATION.md`.
- `--account-value`: starting account equity for risk-managed runs (default `100000`).
- `--multi`: run multi-timeframe analysis (single ticker only).
- `--force-refresh`: bypass cache and redownload data.
- `--clear-cache all|TICKER`: purge cache globally or per ticker.
- `--cache-info`: display cache metadata.
- `--backtest`: enable risk-managed backtest flow (now default behavior when flag present).
- `--simple`: entry-to-exit backtest without risk manager.
- `--risk-managed`: alias for `--backtest` (kept for compatibility).
- `--debug`: verbose logging.
- `--validate-thresholds`: run walk-forward threshold validation routine.

**Configuration Examples**:
```bash
# Default: Uses conservative_config.yaml automatically (6.5 threshold, 70% win rate, +13.35% expectancy)
python vol_analysis.py AAPL

# Explicitly specify conservative (same as default)
python vol_analysis.py AAPL --config configs/conservative_config.yaml

# Use balanced settings (alternative - best risk-adjusted for mixed portfolios)
python vol_analysis.py AAPL --config configs/balanced_config.yaml

# Use base settings (historical baseline - 6.0 threshold, superseded by conservative)
python vol_analysis.py AAPL --config configs/base_config.yaml
```

### `populate_cache_bulk.py`
- `--months N`: number of months to backfill (mutually exclusive with `--start`).
- `--start YYYY-MM-DD`: explicit start date.
- `--end YYYY-MM-DD`: optional end date (defaults to today).
- `--ticker SYMBOL`: **NEW** single ticker symbol to populate (e.g., `AAPL`). Mutually exclusive with `--ticker-files`. Ideal for testing or updating individual tickers with DuckDB fast mode.
- `--ticker-files FILE [FILE ...]`: ticker file(s) to use (space-separated, default: `stocks.txt`). Mutually exclusive with `--ticker`.
- `--use-duckdb`: use DuckDB fast mode (10-20x faster, requires index built with `scripts/build_massive_index.py`).
- `--no-save-others`: skip writing non-tracked tickers to `massive_cache/`.

### `batch_backtest.py`
- `-f` / `--file`: required ticker list.
- `-p` / `--period`: rolling window when no explicit dates provided (default `12mo`).
- `--start-date YYYY-MM-DD`: begin date for regime analysis (requires `--end-date`).
- `--end-date YYYY-MM-DD`: end date (requires `--start-date`).
- `-o` / `--output-dir`: backtest output folder (default `backtest_results`).
- `-c` / `--config`: **NEW** Path to YAML configuration file (e.g., `configs/aggressive_config.yaml`). Overrides default risk management settings.
- `--risk-managed`: (default) ensure RiskManager is active for all trades.
- `--simple`: disable RiskManager and run legacy entry/exit pairing.
- `--stop-strategy {static,vol_regime,atr_dynamic,pct_trail,time_decay}`: stop method when risk-managed (default `static` - RECOMMENDED). See `STOP_STRATEGY_VALIDATION.md` for validation results.
- `--time-stop-bars N`: number of bars before TIME_STOP exit if <+1R (default `12`, set to `0` to disable time stops).
- `--no-individual-reports`: skip creating individual text files per ticker (saves disk space; XLSX ledger contains all trade details).
- `--account-value`: starting account equity for risk-managed batch jobs (default `100000`).

**Configuration Examples**:
```bash
# Default: Uses conservative_config.yaml automatically (6.5 threshold, 70% win rate)
python batch_backtest.py -f ticker_lists/ibd.txt

# Explicitly specify conservative (same as default)
python batch_backtest.py -f ticker_lists/nasdaq100.txt -c configs/conservative_config.yaml

# Use balanced settings (alternative - best risk-adjusted for mixed portfolios)
python batch_backtest.py -f ticker_lists/ibd.txt -c configs/balanced_config.yaml

# Use base settings (historical baseline - 6.0 threshold, superseded by conservative)
python batch_backtest.py -f ticker_lists/ibd.txt -c configs/base_config.yaml

# Compare all configurations
python batch_config_test.py -c configs/*.yaml -f ticker_lists/ibd.txt

python batch_backtest.py \
  -f ticker_lists/nasdaq100.txt \
  -c configs/conservative_config.yaml \
  --start-date 2020-12-07 \
  --end-date 2025-12-05
```

### `batch_config_test.py`
- `-c` / `--configs`: **required** space-separated paths to YAML config files to test (e.g., `configs/*.yaml`).
- `-f` / `--file`: **required** ticker file for backtesting.
- `-o` / `--output-dir`: output directory for comparison reports (default `backtest_results/config_comparison`).
- **Outputs**: CSV, Excel (with conditional formatting), and detailed text report comparing all configurations.
- **Use for**: Systematically comparing multiple configurations to find optimal parameters for your portfolio.

### `sector_dashboard.py`
- `-p` / `--period {1mo,3mo,6mo,12mo}`: scoring window (default `3mo`).
- `-o` / `--output-dir`: save dashboard report to directory.
- `--compare`: highlight changes vs last saved results.
- `--top N`: display only the top-N sectors.

### `sector_dashboard_with_backtest.py`
- `-p` / `--period {1mo,3mo,6mo,12mo}`: scoring window (default `3mo`).
- `-o` / `--output-dir`: save report/CSV artifacts.
- `--compare`: show changes since prior run.
- `--top N`: limit visible sectors.
- `--quick`: skip per-sector backtests (volume scores set to 0 for faster execution).

### `test_variable_stops.py`
- `--tickers TICKER [TICKER ...]`: ticker symbols to test (default: AAPL MSFT NVDA TSLA AMD).
- `-f` / `--file`: ticker file (one per line) - overrides `--tickers` if provided.
- `-p` / `--period`: data period (default: 12mo). Legacy `1y/2y` inputs are converted to `mo` automatically.
- `--strategies`: strategies to test (default: all 5). Options: static, atr_dynamic, pct_trail, vol_regime, time_decay.
- `--output`: output file path (default: backtest_results/variable_stop_comparison.txt).

Refer to each script's `--help` flag for full descriptions and examples.

---

## Documentation Structure

This project uses a multi-volume documentation structure optimized for different audiences:

### 📍 Quick Reference (LLMs & Developers)
- `CODE_MAP.txt` - Fast module lookup: "Change X → Edit file Y"
- `DOCUMENTATION_INVENTORY.md` - Complete file inventory with categorization
- `docs/ARCHITECTURE_REFERENCE.md` - System design and conceptual overview

### 📚 Volume 1: User Documentation (Traders)
- `README.md` - Quick start, commands, validation status (this file)
- `TRADING_STRATEGY.md` - Volume analysis methodology, signals, risk management
- `docs/USER_PLAYBOOK.md` - Daily operational workflow
- `docs/TROUBLESHOOTING.md` - Problem solving guide
- `configs/README.md` - Configuration system guide

### 🔧 Volume 2: Technical Documentation (Developers)
- `CODE_MAP.txt` - Module responsibilities and dependencies
- `docs/ARCHITECTURE_REFERENCE.md` - System design philosophy
- `docs/CACHE_SCHEMA.md` - Data structure and schema
- `docs/DUCKDB_OPTIMIZATION.md` - Performance optimization (10-20x speedup)
- `docs/TRANSACTION_COSTS.md` - Cost modeling documentation

### 🔬 Volume 3: Research & Validation (Analysts)
- `STOP_STRATEGY_VALIDATION.md` - Stop strategy testing (Nov 2025)
- `STRATEGY_VALIDATION_COMPLETE.md` - Overall validation findings
- `PROFESSIONAL_ANALYSIS_PLAN.md` - Metrics framework
- `VARIABLE_STOP_LOSS_FINDINGS.md` - Variable stop research
- `docs/CONFIGURATION_STRATEGY_ANALYSIS.md` - Config empirical study

### 📊 Volume 4: Tools & Analysis (Advanced Users)
- `SECTOR_ROTATION_ANALYSIS_GUIDE.md` - Macro sector analysis tools (see note below)
- `ANALYSIS_SCRIPTS_OVERLAP.md` - Script purposes and workflow
- `ALGORITHM_IMPROVEMENT_PLAN.md` - Future development roadmap

### ⚠️ Sector Analysis Tools Note

**Available Tools** (Implemented):
- ✅ `sector_dashboard.py` - Sector scoring and rotation analysis
- ✅ `sector_rotation.py` - Macro sector strength tracking
- ✅ Sector ETF regime filters (50-day MA checks in signal generation)

**NOT Implemented** (Trading system does NOT):
- ❌ Adjust position sizing based on sector scores
- ❌ Check sector strength beyond regime filters for entry criteria
- ❌ Vary risk management by sector environment

**Current Use**: Sector tools provide macro rotation analysis for **manual trading decisions**. The automated trading system uses **fixed position sizing** (0.75% risk per trade) and **static risk management** regardless of sector scores.

**See**: `SECTOR_ROTATION_ANALYSIS_GUIDE.md` for using sector data in manual trading decisions.

---

## Documentation Map

| Topic | Reference |
|-------|-----------|
| Operational workflow | `docs/USER_PLAYBOOK.md` |
| Professional performance analysis | `PROFESSIONAL_ANALYSIS_PLAN.md`, `professional_evaluation.txt` |
| Analysis scripts (purposes & overlap) | `ANALYSIS_SCRIPTS_OVERLAP.md` |
| Cache architecture & benchmarks | `BULK_CACHE_POPULATION.md` |
| Massive.com integration | `MASSIVE_INTEGRATION.md` |
| **DuckDB optimization (10-20x speedup)** | `docs/DUCKDB_OPTIMIZATION.md` |
| **Momentum screening (RS Velocity + VCP)** | `docs/MOMENTUM_SCREENER.md` |
| Sector rotation dashboard | `SECTOR_ROTATION_GUIDE.md` |
| Sector rotation analysis guide | `SECTOR_ROTATION_ANALYSIS_GUIDE.md` |
| Variable stop loss validation | `VARIABLE_STOP_LOSS_FINDINGS.md` |
| **Stop strategy validation (Nov 2025)** | `STOP_STRATEGY_VALIDATION.md` |
| Architecture & indicators | `docs/ARCHITECTURE_REFERENCE.md` |
| Module responsibilities & dependencies | `CODE_MAP.txt` |
| Cache schema & migrations | `docs/CACHE_SCHEMA.md` |
| Validation history | `STRATEGY_VALIDATION_COMPLETE.md`, `docs/VALIDATION_STATUS.md` |
| Backtest validation methodology | `BACKTEST_VALIDATION_METHODOLOGY.md` |
| **Configuration system (NEW Nov 2025)** | `configs/README.md` |
| **Hardcoded parameters audit** | `docs/HARDCODED_PARAMETERS_AUDIT.md` |
| Troubleshooting | `docs/TROUBLESHOOTING.md` |

---

## Support

1. Start with `docs/TROUBLESHOOTING.md` for dependency, credential, or performance issues.
2. Run `python test_massive_bulk_single_day.py` to confirm S3 access before opening issues.
3. Capture logs/backtest outputs in `massive_*` markdown files when reporting bugs.

---

## License

See `LICENSE` (if present) or contact the repository owner for usage terms.
