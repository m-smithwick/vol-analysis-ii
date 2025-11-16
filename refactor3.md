# Refactor Review (pass 3)

## Code Organization
- `vol_analysis.py` has become a 600+ line god script: CLI handling, cache orchestration, indicator wiring, chart routing, and batch helpers all live together. The cache helpers (`get_cache_directory`, `load_cached_data`, etc.) are copy/pasted from `data_manager.py`, so cache validation logic now diverges in two places every time a schema rule or error message changes. Extract cache/ticker utilities into a shared module (or reuse the richer `data_manager` functions directly) and keep the CLI file focused on argument parsing + pipeline orchestration.
- `batch_backtest.py` drives each ticker by calling `vol_analysis.analyze_ticker`, which re-runs the single-ticker CLI flow (cache download, indicator build, chart toggles). This doubles the work, hardwires user-facing flags into automation code, and blocks parallelism. Provide a service layer (`analysis_service.py`) that returns prepped DataFrames, and let the batch runner use that directly.
- Risk logic advertises multiple stop strategies across documentation/tests, but `RiskManager` only supports `static` and `vol_regime`. Time-decay, ATR-dynamic, and percentage trails exist in markdown only. Either implement the additional strategies with proper tests and CLI flags or trim the docs to match shipped behavior.
- `test_variable_stops.py` is the only place where all five stop strategies exist. None of its strategy implementations are wired into `vol_analysis` or `batch_backtest`, so production runs cannot select them. Promote the shared logic into `RiskManager` (or a mixin) and expose CLI arguments (`--stop-strategy`) so end-to-end scripts can mirror the findings documented in `VARIABLE_STOP_LOSS_FINDINGS.md`.
- CLI switches are not applied uniformly. `vol_analysis.py` and `batch_backtest.py` both use `-f/--file` and `-p/--period`, but `test_variable_stops.py` exposes `--period` without the `-p` alias and accepts `1y/2y` formats instead of the `mo` variants used elsewhere. This adds friction when jumping between scripts.

## Inefficiency & Duplication
- Cache utilities live in both `vol_analysis.py` and `data_manager.py`, with slightly different validation flows and metadata handling. Keeping two near-identical implementations is brittle; regressions happen when one path is patched and the other is not (e.g., schema migrations).
- Many CLI scripts wrap `vol_analysis` instead of reusing shared services, so downloading/processing happens multiple times per run. This inflates runtime and memory use during batch work while giving identical results.
- Documentation/notes (`VARIABLE_STOP_LOSS_FINDINGS.md`, `README_VARIABLE_STOPS.md`, `README.md`, several strategy markdowns) repeat the same tables and prose with different “last updated” dates. Every refactor requires editing 4–5 files to keep them consistent, and the conflicting recommendations (Vol Regime vs Time Decay) create operational confusion.

## Improvement Opportunities
1. Extract cache/ticker list helpers into a dedicated module consumed by both `vol_analysis` and `data_manager`, or simply let `vol_analysis` import the existing `data_manager` functionality. This removes redundant code paths and centralizes schema validation.
2. Introduce an analysis service that exposes a "prepare indicators" API. Have batch, tests, and CLI all call it rather than nesting CLI entry points. This will reduce duplicated work and make it easier to parallelize or unit-test the pipeline.
3. Move the tested stop-strategy implementations out of `test_variable_stops.py` and into `RiskManager`, surface a `--stop-strategy` flag (batch + single-ticker CLI), and keep the test harness focused on validation. That way the actionable scripts honor the Time Decay recommendations instead of letting the docs drift from reality.
4. Align CLI switches across scripts. Give `test_variable_stops.py` the same `-p/--period` semantics (and ideally accept the same `12mo/24mo` tokens) so users can move between commands without relearning flags.
5. If implementation is not imminent, downgrade the docs so they reflect the real capabilities.
6. Restructure documentation: group stop-loss research into a single canonical doc plus a changelog, and link to it from the README instead of embedding the same tables everywhere. Do the same for trading strategy and cache guides. This reduces drift and keeps the repo lean.

## Execution Plan & Sequencing
1. **Stabilize shared services**
   - [x] Merge cache/ticker helpers (Opportunity #1). `vol_analysis` now imports the shared data_manager helpers.
   - [x] Extract an `analysis_service` used by `vol_analysis`, `batch_backtest`, and the test harness (Opportunity #2).
2. **Unify stop-strategy behavior**
   - [x] Promote variable stop logic into `RiskManager` + expose `--stop-strategy` flags in both CLI entry points (Opportunity #3).
   - [x] Normalize CLI switches/period tokens across scripts, starting with `test_variable_stops.py` (Opportunity #4).
3. **Align documentation with functionality**
   - [x] Update README + stop-loss docs after the code changes above, or explicitly mark unimplemented strategies (Opportunity #5).
   - [x] Consolidate duplicated markdown into canonical references/changelog sections (Opportunity #6).

Update the checkboxes (☑/❌) and leave short notes beneath each bullet as tasks complete so this file remains the running tracker for the refactor.
