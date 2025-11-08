# Backtest Report Simplification Tasks

## Context
- Focus on end-of-day data with a 12-month lookback; intraday segmentation is unnecessary.
- Current outputs duplicate interpretation guidance per ticker and mix high-level insights with dense trade logs.
- Goal: keep richer analytics available, but make the default artifacts faster to scan for mid/long-term decision making.

## Task 1 – Consolidated Scoreboard Output
- Add a post-processing step inside `batch_backtest.py` (and single-ticker runs) that aggregates per-ticker metrics before writing individual reports.
- Include: ticker, sample size, win rate, expectancy, avg return, avg holding period, best/worst trades, recommended entry/exit combo, and profit factor.
- Emit both CSV (for spreadsheet work) and Markdown (for quick reading) to `results_volume/scoreboards/` with timestamped filenames.
- Acceptance: running an existing batch creates the scoreboard file without extra flags; contents match the data already present in the per-ticker reports.

## Task 2 – Interpretation Guide De-duplication
- Move the static “Win Rate / Expectancy / Profit Factor” explanations out of the ticker reports into a shared doc (e.g., `docs/interpretation_guide.md`).
- Replace the repeated block in report writers with a one-line pointer that links to the shared guide.
- Acceptance: ticker files lose ~20 lines each, and the guide remains available through a single, version-controlled document.

## Task 3 – Split Risk-Managed Reports
- Update risk-managed output routines to create two artifacts per ticker:
  1. `*_summary.txt` containing configuration, aggregate stats, R-multiple distribution, and key insights.
  2. `*_trades.txt` (or appended appendix) listing the detailed trade log.
- Ensure the summary links to the trade log path so drill-down remains accessible.
- Acceptance: main summary stays under ~2 pages while trade details are preserved separately.

## Task 4 – Enhanced Batch Summary
- Extend `batch_summary_12mo_*.txt` generation to add a table comparing baseline vs risk-managed metrics side by side (win rate, avg return, expectancy).
- Highlight deltas (e.g., +5% expectancy improvement) and surface “top movers” where risk management materially helps or hurts.
- Acceptance: opening the batch summary alone gives a portfolio-wide view; no need to open individual files to know where risk controls matter.

## Task 5 – Output Controls / CLI Flags
- Introduce flags (`--summary-only`, `--include-trade-log`, etc.) that control which sections/files are produced during backtests.
- Default behavior should favor concise summaries; detailed logs only generate when explicitly requested.
- Acceptance: running with default options yields the new streamlined artifact set; enabling flags reproduces the original verbosity.

## Suggested Implementation Order
1. Build the scoreboard generator (unblocks downstream summaries).
2. Deduplicate the interpretation guide to immediately shrink files.
3. Restructure risk-managed outputs (depends on new CLI flags).
4. Enhance batch summaries using the new scoreboard data.
5. Wire up CLI flags and documentation updates last.

