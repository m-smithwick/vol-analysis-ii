import pandas as pd

import threshold_validation


def build_mock_dataframe() -> pd.DataFrame:
    """Create a synthetic DataFrame with the required columns for validation tests."""
    dates = pd.date_range("2025-01-01", periods=40, freq="B")
    moderate_buy = [(idx % 4) == 0 for idx in range(len(dates))]
    moderate_score = [6.0 + (idx % 3) for idx in range(len(dates))]

    # Exit signal fires one day after each entry (shifted pattern)
    profit_taking = [False] + moderate_buy[:-1]

    close_prices = [100 + idx * 0.5 for idx in range(len(dates))]
    next_open = close_prices[1:] + [close_prices[-1]]

    data = {
        "Moderate_Buy": moderate_buy,
        "Moderate_Buy_Score": moderate_score,
        "Profit_Taking": profit_taking,
        "Distribution_Warning": [False] * len(dates),
        "Sell_Signal": [False] * len(dates),
        "Momentum_Exhaustion": [False] * len(dates),
        "Stop_Loss": [False] * len(dates),
        "Next_Open": next_open,
        "Close": close_prices,
    }

    return pd.DataFrame(data, index=dates)


def build_test_config() -> threshold_validation.ThresholdValidationConfig:
    """Return a compact validation configuration suitable for small synthetic data."""
    return threshold_validation.ThresholdValidationConfig(
        train_period_days=10,
        test_period_days=5,
        step_days=5,
        minimum_trades=1,
        signal_thresholds={"Moderate_Buy": "Moderate_Buy_Score"},
    )


def test_build_walk_forward_windows_generates_expected_windows():
    df = build_mock_dataframe()
    config = build_test_config()

    windows = threshold_validation.build_walk_forward_windows(df, config)

    # With 40 business days and the specified config we expect multiple windows.
    assert len(windows) >= 3
    for window in windows:
        assert window.train_start <= window.train_end
        assert window.test_start <= window.test_end


def test_run_walk_forward_validation_produces_metrics():
    df = build_mock_dataframe()
    config = build_test_config()

    results = threshold_validation.run_walk_forward_validation(df, config)

    assert results, "Expected at least one validation window result"
    for result in results:
        assert "Moderate_Buy" in result.train_metrics
        assert "Moderate_Buy" in result.validation_metrics
        assert "Moderate_Buy" in result.selected_thresholds
        assert "Moderate_Buy" in result.degradation_flags


def test_generate_validation_report_contains_summary_section():
    df = build_mock_dataframe()
    config = build_test_config()
    results = threshold_validation.run_walk_forward_validation(df, config)

    report = threshold_validation.generate_validation_report(results)

    assert "THRESHOLD VALIDATION SUMMARY" in report
    assert "WALK-FORWARD WINDOWS" in report
