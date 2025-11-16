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
   pip install pandas numpy yfinance matplotlib boto3 requests
   ```
2. **Populate cache (start small, then scale)**
   ```bash
   python populate_cache_bulk.py --months 1
   python populate_cache_bulk.py --months 24
   ```
3. **Run analysis & dashboards**
   ```bash
   # Single ticker analysis
   python vol_analysis.py --period 6mo --ticker AAPL 

   #file with tickers
   python vol_analysis.py --period 24mo --file cmb.txt --chart-backend plotly --save-charts

   # Batch backtest a watchlist
   python batch_backtest.py -f stocks.txt -p 24mo --risk-managed
   # Risk-managed runs now default to time_decay stops; override via --stop-strategy

   # Sector dashboards
   python sector_dashboard.py --top 5 --compare
   python sector_dashboard_with_backtest.py --top 5

   # Variable stop loss testing (4,249 trades validated)
   python test_variable_stops.py --file cmb.txt --period 2y
   python test_variable_stops.py --tickers AAPL MSFT --strategies static vol_regime time_decay
   ```

Need the full operational routine (daily/monthly/quarterly)? See `docs/USER_PLAYBOOK.md`.

---

## Validation Status

- **Moderate Buy** – ✅ Live, but expect +2‑3% median returns (see `OUT_OF_SAMPLE_VALIDATION_REPORT.md`).
- **Variable Stop Loss** – ✅ Validated with 4,249 trades. Time Decay winner: **+22% improvement** (1.52R vs 1.25R static).
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
- `--stop-strategy {static,vol_regime,atr_dynamic,pct_trail,time_decay}`: choose risk-managed stop logic (default `time_decay`).
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
- `--no-save-others`: skip writing non-tracked tickers to `massive_cache/`.

### `batch_backtest.py`
- `-f` / `--file`: required ticker list.
- `-p` / `--period`: rolling window when no explicit dates provided (default `12mo`).
- `--start-date YYYY-MM-DD`: begin date for regime analysis (requires `--end-date`).
- `--end-date YYYY-MM-DD`: end date (requires `--start-date`).
- `-o` / `--output-dir`: backtest output folder (default `backtest_results`).
- `--risk-managed`: enable full RiskManager exit logic.
- `--stop-strategy {static,vol_regime,atr_dynamic,pct_trail,time_decay}`: stop method when risk-managed (default `time_decay`).

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
| Cache architecture & benchmarks | `BULK_CACHE_POPULATION.md` |
| Massive.com integration | `MASSIVE_INTEGRATION.md` |
| Sector rotation dashboard | `SECTOR_ROTATION_GUIDE.md` |
| Sector-aware trading rules | `TRADING_STRATEGY_SECTOR_AWARE.md` |
| Variable stop loss validation | `VARIABLE_STOP_LOSS_FINDINGS.md` |
| Architecture & indicators | `docs/ARCHITECTURE_REFERENCE.md` |
| Module responsibilities & dependencies | `CODE_MAP.txt` |
| Cache schema & migrations | `docs/CACHE_SCHEMA.md` |
| Validation history | `STRATEGY_VALIDATION_COMPLETE.md`, `docs/VALIDATION_STATUS.md` |
| Troubleshooting | `docs/TROUBLESHOOTING.md` |

---

## Support

1. Start with `docs/TROUBLESHOOTING.md` for dependency, credential, or performance issues.
2. Run `python test_massive_bulk_single_day.py` to confirm S3 access before opening issues.
3. Capture logs/backtest outputs in `massive_*` markdown files when reporting bugs.

---

## License

See `LICENSE` (if present) or contact the repository owner for usage terms.
