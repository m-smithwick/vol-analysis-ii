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
   # Start with 1 month to test
   python populate_cache.py --all -m 1
   
   # Scale up to 24 months
   python populate_cache.py --all -m 24
   ```
   
   **Option B: Massive.com (Advanced - Requires AWS S3 credentials and massive.com subscription)**
   ```bash
   # For users with Massive.com access (faster bulk downloads)
   # Default: uses ticker_lists/stocks.txt
   python populate_cache_bulk.py --months 1
   
   # Specify different ticker file(s)
   python populate_cache_bulk.py --months 24 --ticker-files ticker_lists/ibd20.txt
   
   # Use multiple ticker files
   python populate_cache_bulk.py --months 12 --ticker-files ticker_lists/indices.txt ticker_lists/sector_etfs.txt

   # use a date range for catching up the last few days. 
   python populate_cache_bulk.py --start 2025-11-20 --end 2025-11-24  --ticker-files cmb.txt
   ```
   
   > 💡 **New users**: Start with Option A (Yahoo Finance). It works immediately without any setup.
   > Option B is for advanced users with Massive.com subscriptions who need to backfill years of data quickly.
3. **Run analysis & dashboards**
   ```bash
   # Single ticker analysis
   python vol_analysis.py AAPL --period 6mo

   #file with tickers
   python vol_analysis.py --file cmb.txt --period 24mo --chart-backend plotly --save-charts
   python vol_analysis.py  --period 24mo --chart-backend plotly --save-charts --file cmb.txt

   # Batch backtest a watchlist
  python batch_backtest.py  -p 12mo -f cmb.txt --no-individual-reports
   # Risk-managed runs default to static stops (optimal performance validated Nov 2025)
   # Override via --stop-strategy if testing alternatives

   # Sector dashboards
   python sector_dashboard.py --top 5 --compare
   python sector_dashboard_with_backtest.py --top 5

   # Variable stop loss testing (4,249 trades validated)
   python test_variable_stops.py --file cmb.txt --period 2y
   python test_variable_stops.py --tickers AAPL MSFT --strategies static vol_regime time_decay
   ```

Need the full operational routine (daily/monthly/quarterly)? See `docs/USER_PLAYBOOK.md`.

---

## Performance Analysis & Optimization

After running backtests, use these tools to evaluate and optimize your strategy:

### Professional Evaluation
```bash
# Calculate institutional-grade metrics (Sharpe, drawdown, etc.)
python analyze_professional_metrics.py --csv backtest_results/LOG_FILE_cmb_36mo_20251122_153033.csv
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

- **Moderate Buy** – ✅ Live, but expect +2‑3% median returns (see `OUT_OF_SAMPLE_VALIDATION_REPORT.md`).
- **Variable Stop Loss** – ✅ Validated with 4,249 trades. Time Decay winner: **+22% improvement** (1.52R vs 1.25R static).
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
- `--save-charts`: store PNG/HTML charts during batch runs.
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

### `populate_cache_bulk.py`
- `--months N`: number of months to backfill (mutually exclusive with `--start`).
- `--start YYYY-MM-DD`: explicit start date.
- `--end YYYY-MM-DD`: optional end date (defaults to today).
- `--ticker-files FILE [FILE ...]`: ticker file(s) to use (space-separated, default: `stocks.txt`).
- `--no-save-others`: skip writing non-tracked tickers to `massive_cache/`.

### `batch_backtest.py`
- `-f` / `--file`: required ticker list.
- `-p` / `--period`: rolling window when no explicit dates provided (default `12mo`).
- `--start-date YYYY-MM-DD`: begin date for regime analysis (requires `--end-date`).
- `--end-date YYYY-MM-DD`: end date (requires `--start-date`).
- `-o` / `--output-dir`: backtest output folder (default `backtest_results`).
- `--risk-managed`: (default) ensure RiskManager is active for all trades.
- `--simple`: disable RiskManager and run legacy entry/exit pairing.
- `--stop-strategy {static,vol_regime,atr_dynamic,pct_trail,time_decay}`: stop method when risk-managed (default `static` - RECOMMENDED). See `STOP_STRATEGY_VALIDATION.md` for validation results.
- `--time-stop-bars N`: number of bars before TIME_STOP exit if <+1R (default `12`, set to `0` to disable time stops).
- `--no-individual-reports`: skip creating individual text files per ticker (saves disk space; XLSX ledger contains all trade details).
- `--account-value`: starting account equity for risk-managed batch jobs (default `100000`).

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

## Documentation Map

| Topic | Reference |
|-------|-----------|
| Operational workflow | `docs/USER_PLAYBOOK.md` |
| Professional performance analysis | `PROFESSIONAL_ANALYSIS_PLAN.md`, `professional_evaluation.txt` |
| Analysis scripts (purposes & overlap) | `ANALYSIS_SCRIPTS_OVERLAP.md` |
| Cache architecture & benchmarks | `BULK_CACHE_POPULATION.md` |
| Massive.com integration | `MASSIVE_INTEGRATION.md` |
| Sector rotation dashboard | `SECTOR_ROTATION_GUIDE.md` |
| Sector-aware trading rules | `TRADING_STRATEGY_SECTOR_AWARE.md` |
| Variable stop loss validation | `VARIABLE_STOP_LOSS_FINDINGS.md` |
| **Stop strategy validation (Nov 2025)** | `STOP_STRATEGY_VALIDATION.md` |
| Architecture & indicators | `docs/ARCHITECTURE_REFERENCE.md` |
| Module responsibilities & dependencies | `CODE_MAP.txt` |
| Cache schema & migrations | `docs/CACHE_SCHEMA.md` |
| Validation history | `STRATEGY_VALIDATION_COMPLETE.md`, `docs/VALIDATION_STATUS.md` |
| Backtest validation methodology | `BACKTEST_VALIDATION_METHODOLOGY.md` |
| Troubleshooting | `docs/TROUBLESHOOTING.md` |

---

## Support

1. Start with `docs/TROUBLESHOOTING.md` for dependency, credential, or performance issues.
2. Run `python test_massive_bulk_single_day.py` to confirm S3 access before opening issues.
3. Capture logs/backtest outputs in `massive_*` markdown files when reporting bugs.

---

## License

See `LICENSE` (if present) or contact the repository owner for usage terms.
