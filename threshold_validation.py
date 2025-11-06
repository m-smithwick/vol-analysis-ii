"""
Threshold validation utilities (Item #9).

This module provides the scaffolding for walk-forward validation of
signal thresholds to identify overfitting. Actual logic will be filled
in subsequent implementation steps.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd

import backtest
from error_handler import DataValidationError, get_logger, setup_logging

# Ensure logger is configured consistently with rest of application
setup_logging()
logger = get_logger()

@dataclass
class WalkForwardWindow:
    """
    Represents a single walk-forward slice with training and validation ranges.

    Attributes:
        train_start: Start timestamp (inclusive) for the optimization window.
        train_end: End timestamp (inclusive) for the optimization window.
        test_start: Start timestamp (inclusive) for the validation window.
        test_end: End timestamp (inclusive) for the validation window.
    """

    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


@dataclass
class ThresholdValidationConfig:
    """
    Configuration parameters governing walk-forward analysis.

    Attributes:
        train_period_days: Number of calendar days in each optimization window.
        test_period_days: Number of calendar days in each validation window.
        step_days: How far to slide the window after each iteration.
        minimum_trades: Minimum trades required in validation to consider metrics.
        max_win_rate_drop: Allowed drop in win rate (percentage points) before flagging degradation.
        max_expectancy_drop: Allowed drop in expectancy (percentage points) before flagging degradation.
        minimum_expected_expectancy: Absolute minimum expectancy tolerated in validation.
        signal_thresholds: Mapping of signal names to score column names.
    """

    train_period_days: int = 252  # ~12 months of trading days
    test_period_days: int = 63    # ~3 months of trading days
    step_days: int = 63
    minimum_trades: int = 10
    max_win_rate_drop: float = 12.5
    max_expectancy_drop: float = 1.0
    minimum_expected_expectancy: float = 0.0
    signal_thresholds: Dict[str, str] = None

    def __post_init__(self) -> None:
        if self.signal_thresholds is None:
            self.signal_thresholds = {
                "Moderate_Buy": "Moderate_Buy_Score",
                "Stealth_Accumulation": "Stealth_Accumulation_Score",
                "Profit_Taking": "Profit_Taking_Score",
            }


@dataclass
class ThresholdMetrics:
    """
    Captures performance metrics for a given signal threshold.
    """

    trades: int
    win_rate: float
    expectancy: float
    profit_factor: float
    sample_size: int

    @classmethod
    def from_metrics_dict(cls, metrics: Dict[str, float]) -> "ThresholdMetrics":
        """Create ThresholdMetrics from backtest metrics dictionary."""
        return cls(
            trades=int(metrics.get("trades", 0) or 0),
            win_rate=float(metrics.get("win_rate", 0.0) or 0.0),
            expectancy=float(metrics.get("expectancy", 0.0) or 0.0),
            profit_factor=float(metrics.get("profit_factor", 0.0) or 0.0),
            sample_size=int(metrics.get("sample_size", metrics.get("trades", 0)) or 0),
        )


@dataclass
class WalkForwardResult:
    """
    Stores per-slice validation results keyed by signal name.
    """

    window: WalkForwardWindow
    train_metrics: Dict[str, Optional[ThresholdMetrics]]
    validation_metrics: Dict[str, Optional[ThresholdMetrics]]
    selected_thresholds: Dict[str, Optional[float]]
    degradation_flags: Dict[str, Optional[bool]]


def build_walk_forward_windows(
    df: pd.DataFrame,
    config: ThresholdValidationConfig,
) -> List[WalkForwardWindow]:
    """
    Compute walk-forward windows for a time-indexed DataFrame.

    The initial implementation will populate this function with logic to:
    1. Sort the DataFrame by index.
    2. Iterate through the index generating rolling train/test slices
       according to `config`.
    3. Skip any window where the validation period does not have enough
       data to meet `minimum_trades` once threshold filtering is applied.

    Returns:
        A list of `WalkForwardWindow` instances covering the available data.
    """

    if df.empty:
        return []

    if not isinstance(df.index, pd.DatetimeIndex):
        raise DataValidationError("DataFrame index must be a DatetimeIndex for walk-forward validation.")

    df_sorted = df.sort_index()
    df_sorted = df_sorted[~df_sorted.index.duplicated(keep="first")]

    train_delta = pd.Timedelta(days=config.train_period_days)
    test_delta = pd.Timedelta(days=config.test_period_days)
    step_delta = pd.Timedelta(days=config.step_days)

    windows: List[WalkForwardWindow] = []
    current_start = df_sorted.index[0]
    last_index = df_sorted.index[-1]

    while current_start <= last_index:
        train_end_target = current_start + train_delta
        test_start = train_end_target + pd.Timedelta(days=1)
        test_end_target = test_start + test_delta

        train_slice = df_sorted.loc[(df_sorted.index >= current_start) & (df_sorted.index <= train_end_target)]
        test_slice = df_sorted.loc[(df_sorted.index >= test_start) & (df_sorted.index <= test_end_target)]

        if train_slice.empty:
            logger.debug("Skipping window starting %s: no training data.", current_start.date())
        elif test_slice.empty:
            logger.debug("Stopping window generation at %s: insufficient validation data.", current_start.date())
            break
        else:
            window = WalkForwardWindow(
                train_start=train_slice.index[0],
                train_end=train_slice.index[-1],
                test_start=test_slice.index[0],
                test_end=test_slice.index[-1],
            )
            windows.append(window)

        next_start = current_start + step_delta
        # Stop if next window would start beyond available data
        if next_start >= last_index:
            break
        current_start = next_start

    return windows


def run_walk_forward_validation(
    df: pd.DataFrame,
    config: ThresholdValidationConfig,
) -> List[WalkForwardResult]:
    """
    Execute walk-forward validation across all configured signals.

    Responsibilities that will be implemented in later steps:
        • Use `build_walk_forward_windows` to derive train/test slices.
        • For each signal, run the existing optimization utilities on the
          training slice to determine optimal thresholds.
        • Evaluate the chosen thresholds on the validation slice, collecting
          metrics via the existing backtest analysis pipeline.
        • Flag instances where validation metrics degrade materially relative
          to training (criteria to be defined alongside Item #9 requirements).
        • Aggregate per-window results so downstream reporting can surface
          rolling performance trends.

    Returns:
        Ordered list of `WalkForwardResult` structures, one per window.
    """

    validate_required_columns(df, config.signal_thresholds)
    windows = build_walk_forward_windows(df, config)

    results: List[WalkForwardResult] = []

    for window in windows:
        train_df = df.loc[window.train_start:window.train_end].copy()
        test_df = df.loc[window.test_start:window.test_end].copy()

        train_metrics: Dict[str, Optional[ThresholdMetrics]] = {}
        validation_metrics: Dict[str, Optional[ThresholdMetrics]] = {}
        degradation_flags: Dict[str, Optional[bool]] = {}
        selected_thresholds: Dict[str, Optional[float]] = {}

        for signal_col, score_col in config.signal_thresholds.items():
            signal_train_metrics, threshold = optimize_on_training_slice(
                train_df,
                signal_col,
                score_col,
                config.minimum_trades,
            )
            train_metrics[signal_col] = signal_train_metrics
            selected_thresholds[signal_col] = threshold

            if signal_train_metrics is None or threshold is None:
                validation_metrics[signal_col] = None
                degradation_flags[signal_col] = True
                continue

            validation_metrics[signal_col] = evaluate_on_validation_slice(
                test_df,
                signal_col,
                score_col,
                threshold,
            )

            degradation_flags[signal_col] = flag_degradation(
                train_metrics[signal_col],
                validation_metrics[signal_col],
                config,
            )

        results.append(
            WalkForwardResult(
                window=window,
                train_metrics=train_metrics,
                validation_metrics=validation_metrics,
                selected_thresholds=selected_thresholds,
                degradation_flags=degradation_flags,
            )
        )

    return results


def summarize_validation_results(
    results: List[WalkForwardResult],
) -> Dict[str, Dict[str, Optional[float]]]:
    """
    Produce aggregate summaries for reporting.

    Planned responsibilities:
        • Compute average train vs validation win rate/expectancy deltas
          for each signal.
        • Identify the worst observed degradation across windows.
        • Expose counts of windows that failed minimum trade thresholds.
        • Provide structured data that can be rendered as text tables or
          exported as JSON for documentation updates.

    Returns:
        Nested dict keyed by signal name with summary statistics.
    """

    if not results:
        return {}

    summary: Dict[str, Dict[str, Optional[float]]] = {}

    for signal in results[0].selected_thresholds.keys():
        train_win_rates: List[float] = []
        val_win_rates: List[float] = []
        train_expectancies: List[float] = []
        val_expectancies: List[float] = []
        degradation_count = 0
        window_count = 0

        for result in results:
            train_metric = result.train_metrics.get(signal)
            val_metric = result.validation_metrics.get(signal)
            degraded = result.degradation_flags.get(signal)

            if train_metric and val_metric:
                train_win_rates.append(train_metric.win_rate)
                val_win_rates.append(val_metric.win_rate)
                train_expectancies.append(train_metric.expectancy)
                val_expectancies.append(val_metric.expectancy)
                window_count += 1

            if degraded:
                degradation_count += 1

        if window_count == 0:
            summary[signal] = {
                "avg_train_win_rate": None,
                "avg_validation_win_rate": None,
                "avg_train_expectancy": None,
                "avg_validation_expectancy": None,
                "windows": 0,
                "degradation_flags": degradation_count,
            }
        else:
            summary[signal] = {
                "avg_train_win_rate": sum(train_win_rates) / len(train_win_rates) if train_win_rates else None,
                "avg_validation_win_rate": sum(val_win_rates) / len(val_win_rates) if val_win_rates else None,
                "avg_train_expectancy": sum(train_expectancies) / len(train_expectancies)
                if train_expectancies else None,
                "avg_validation_expectancy": sum(val_expectancies) / len(val_expectancies)
                if val_expectancies else None,
                "windows": window_count,
                "degradation_flags": degradation_count,
            }

    return summary


def generate_validation_report(results: List[WalkForwardResult]) -> str:
    """
    Build a human-readable validation report summarizing walk-forward outcomes.

    Args:
        results: Ordered walk-forward results from `run_walk_forward_validation`.

    Returns:
        str: Multi-line report suitable for console output or markdown docs.
    """

    if not results:
        return "⚠️ No validation results available."

    summary = summarize_validation_results(results)
    report_lines: List[str] = []

    report_lines.append("🎯 THRESHOLD VALIDATION SUMMARY")
    report_lines.append("=" * 80)
    report_lines.append("Signal                Windows  Deg Flags  Train Win%  Valid Win%  Train Exp%  Valid Exp%")
    report_lines.append("-" * 80)

    for signal, stats in summary.items():
        train_win = stats.get("avg_train_win_rate")
        val_win = stats.get("avg_validation_win_rate")
        train_exp = stats.get("avg_train_expectancy")
        val_exp = stats.get("avg_validation_expectancy")
        windows = stats.get("windows", 0) or 0
        deg_flags = stats.get("degradation_flags", 0) or 0

        report_lines.append(
            f"{signal:<20} {windows:>7}  {deg_flags:>9}  "
            f"{train_win:>10.1f}  {val_win:>10.1f}  {train_exp:>10.2f}  {val_exp:>10.2f}"
            if windows
            else f"{signal:<20} {windows:>7}  {deg_flags:>9}  {'n/a':>10}  {'n/a':>10}  {'n/a':>10}  {'n/a':>10}"
        )

    report_lines.append("")
    report_lines.append("📅 WALK-FORWARD WINDOWS")
    report_lines.append("-" * 80)

    for idx, result in enumerate(results, start=1):
        window = result.window
        report_lines.append(
            f"Window {idx}: Train {window.train_start.date()} → {window.train_end.date()} | "
            f"Validate {window.test_start.date()} → {window.test_end.date()}"
        )

        for signal, threshold in result.selected_thresholds.items():
            train_metric = result.train_metrics.get(signal)
            val_metric = result.validation_metrics.get(signal)
            degraded = result.degradation_flags.get(signal)
            status = "✅" if degraded is False else "⚠️"

            if train_metric and val_metric:
                report_lines.append(
                    f"  {status} {signal:<18} thr ≥{threshold:.1f} | "
                    f"Train: {train_metric.win_rate:>5.1f}% / {train_metric.expectancy:+5.2f}% "
                    f"({train_metric.trades} trades) → "
                    f"Valid: {val_metric.win_rate:>5.1f}% / {val_metric.expectancy:+5.2f}% "
                    f"({val_metric.trades} trades)"
                )
            elif train_metric and not val_metric:
                report_lines.append(
                    f"  {status} {signal:<18} thr ≥{threshold:.1f} | "
                    f"Train: {train_metric.win_rate:>5.1f}% / {train_metric.expectancy:+5.2f}% "
                    f"({train_metric.trades} trades) → Valid: n/a (0 trades)"
                )
            else:
                report_lines.append(
                    f"  ⚠️ {signal:<18} insufficient training trades to evaluate window"
                )

        report_lines.append("")

    return "\n".join(report_lines)


def validate_required_columns(df: pd.DataFrame, signal_thresholds: Dict[str, str]) -> None:
    """Ensure DataFrame contains all required signal/score columns."""
    missing_columns = []
    for signal_col, score_col in signal_thresholds.items():
        if signal_col not in df.columns:
            missing_columns.append(signal_col)
        if score_col not in df.columns:
            missing_columns.append(score_col)

    required_exit_cols = [
        "Profit_Taking",
        "Distribution_Warning",
        "Sell_Signal",
        "Momentum_Exhaustion",
        "Stop_Loss",
        "Next_Open",
        "Close",
    ]
    for col in required_exit_cols:
        if col not in df.columns:
            missing_columns.append(col)

    if missing_columns:
        message = f"DataFrame missing required columns for threshold validation: {sorted(set(missing_columns))}"
        raise DataValidationError(message)


def optimize_on_training_slice(
    train_df: pd.DataFrame,
    signal_col: str,
    score_col: str,
    minimum_trades: int,
) -> Tuple[Optional[ThresholdMetrics], Optional[float]]:
    """Run optimization on the training slice and determine best threshold."""
    results = backtest.optimize_signal_thresholds(
        train_df,
        signal_col=signal_col,
        score_col=score_col,
        signal_name=signal_col,
    )

    valid_results = {
        threshold: metrics
        for threshold, metrics in results.items()
        if metrics.get("trades", 0) >= minimum_trades
    }

    if not valid_results:
        logger.debug(
            "No valid thresholds for %s in training slice (%s to %s).",
            signal_col,
            train_df.index.min().date(),
            train_df.index.max().date(),
        )
        return None, None

    best_threshold, best_metrics = max(
        valid_results.items(),
        key=lambda item: item[1].get("expectancy", float("-inf")),
    )

    return ThresholdMetrics.from_metrics_dict(best_metrics), best_threshold


def evaluate_on_validation_slice(
    test_df: pd.DataFrame,
    signal_col: str,
    score_col: str,
    threshold: float,
) -> Optional[ThresholdMetrics]:
    """Evaluate a specific threshold on the validation slice."""
    results = backtest.optimize_signal_thresholds(
        test_df,
        signal_col=signal_col,
        score_col=score_col,
        signal_name=signal_col,
        thresholds=[threshold],
    )

    metrics = results.get(threshold)
    if not metrics or metrics.get("trades", 0) == 0:
        logger.debug(
            "Validation slice produced no trades for %s threshold %.2f (%s to %s).",
            signal_col,
            threshold,
            test_df.index.min().date(),
            test_df.index.max().date(),
        )
        return None

    return ThresholdMetrics.from_metrics_dict(metrics)


def flag_degradation(
    train_metrics: Optional[ThresholdMetrics],
    validation_metrics: Optional[ThresholdMetrics],
    config: ThresholdValidationConfig,
) -> Optional[bool]:
    """Determine whether validation performance represents degradation."""
    if train_metrics is None:
        return True

    if validation_metrics is None:
        return True

    if validation_metrics.trades < config.minimum_trades:
        return True

    if validation_metrics.expectancy < config.minimum_expected_expectancy:
        return True

    win_rate_drop = train_metrics.win_rate - validation_metrics.win_rate
    if win_rate_drop > config.max_win_rate_drop:
        return True

    expectancy_drop = train_metrics.expectancy - validation_metrics.expectancy
    if expectancy_drop > config.max_expectancy_drop:
        return True

    return False
