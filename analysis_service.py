"""
Shared analysis pipeline utilities.

Provides a single prepare_analysis_dataframe() entry point so CLI tools,
batch backtests, and validation harnesses all build indicators the same way.
"""

import numpy as np
import pandas as pd

from error_handler import (
    ErrorContext,
    DataValidationError,
    DataDownloadError,
    CacheError,
    validate_ticker,
    validate_period,
    get_logger,
)
from data_manager import get_smart_data
import indicators
import regime_filter
import signal_generator
import swing_structure
import volume_features
import momentum_confirmation


def prepare_analysis_dataframe(
    ticker: str,
    period: str,
    *,
    data_source: str = "yfinance",
    force_refresh: bool = False,
    verbose: bool = False,
) -> pd.DataFrame:
    """
    Build the full indicator + signal DataFrame used by analysis/backtesting.
    """
    with ErrorContext("preparing analysis dataframe", ticker=ticker, period=period):
        validate_ticker(ticker)
        validate_period(period)
        logger = get_logger()

        try:
            df = get_smart_data(
                ticker,
                period,
                interval="1d",
                force_refresh=force_refresh,
                data_source=data_source,
            )
            logger.info(
                f"Retrieved {len(df)} rows for {ticker} ({period}) via {data_source}"
            )
        except (DataValidationError, DataDownloadError, CacheError):
            raise
        except Exception as exc:
            raise DataDownloadError(f"Failed to get data for {ticker}: {exc}")

    # --- Volume/price feature engineering (kept in sync with vol_analysis.py) ---
    df["CMF_20"] = volume_features.calculate_cmf(df, period=20)
    df["CMF_Z"] = volume_features.calculate_cmf_zscore(
        df, cmf_period=20, zscore_window=20
    )

    df["PriceVolumeCorr"] = indicators.calculate_price_volume_correlation(
        df, window=20
    )

    df["Price_MA"] = df["Close"].rolling(window=10).mean()
    df["Price_Trend"] = (df["Close"] > df["Price_MA"]).fillna(False)
    df["Price_Rising"] = (df["Close"] > df["Close"].shift(5)).fillna(False)

    df["CMF_Positive"] = (df["CMF_Z"] > 0).fillna(False)
    df["CMF_Strong"] = (df["CMF_Z"] > 1.0).fillna(False)

    price_delta = df["Close"].diff().fillna(0)
    obv_direction = np.sign(price_delta).fillna(0)
    df["OBV"] = (obv_direction * df["Volume"]).fillna(0).cumsum()
    df["OBV_MA"] = df["OBV"].rolling(window=10).mean()
    df["OBV_Trend"] = (df["OBV"] > df["OBV_MA"]).fillna(False)

    high_low_range = (df["High"] - df["Low"]).replace(0, np.nan)
    money_flow_multiplier = (
        ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / high_low_range
    )
    money_flow_multiplier = money_flow_multiplier.replace(
        [np.inf, -np.inf], 0
    ).fillna(0)
    money_flow_volume = money_flow_multiplier * df["Volume"]
    df["AD_Line"] = money_flow_volume.cumsum()
    df["AD_MA"] = df["AD_Line"].rolling(window=10).mean()
    df["AD_Rising"] = df["AD_Line"].diff().fillna(0) > 0

    df["Volume_MA"] = df["Volume"].rolling(window=20).mean()
    df["Volume_Spike"] = (df["Volume"] > (df["Volume_MA"] * 1.5)).fillna(False)
    df["Relative_Volume"] = volume_features.calculate_volume_surprise(df, window=20)

    df["VWAP"] = indicators.calculate_anchored_vwap(df)
    df["Above_VWAP"] = (df["Close"] > df["VWAP"]).fillna(False)

    swing_low, swing_high = swing_structure.calculate_swing_levels(df, lookback=3)
    (
        df["Recent_Swing_Low"],
        df["Recent_Swing_High"],
    ) = swing_low, swing_high
    (
        df["Near_Support"],
        df["Lost_Support"],
        df["Near_Resistance"],
    ) = swing_structure.calculate_swing_proximity_signals(
        df,
        df["Recent_Swing_Low"],
        df["Recent_Swing_High"],
        atr_series=None,
        use_volatility_aware=False,
    )
    df["Support_Level"] = df["Recent_Swing_Low"]

    df["TR"], df["ATR20"] = indicators.calculate_atr(df, period=20)
    df["Event_Day"] = volume_features.detect_event_days(
        df, atr_multiplier=2.5, volume_threshold=2.0
    )

    df = indicators.standardize_features(df, window=20)
    df = indicators.apply_prefilters(
        ticker=ticker,
        df=df,
        min_dollar_volume=5_000_000,
        min_price=3.00,
        earnings_window_days=3,
    )

    accumulation_conditions = [
        (
            df["AD_Rising"]
            & ~df["Price_Rising"]
            & df["Volume_Spike"]
            & df["Above_VWAP"]
        ),
        (
            df["CMF_Strong"]
            & df["Above_VWAP"]
            & df["Near_Support"]
            & df["Price_Trend"]
        ),
        (
            df["CMF_Positive"]
            & (df["PriceVolumeCorr"].rolling(window=5).mean().fillna(0) > 0.3)
            & df["Volume_Spike"]
        ),
    ]
    df["Strong_Accumulation"] = accumulation_conditions[0]
    df["Moderate_Accumulation"] = accumulation_conditions[1]
    df["Support_Accumulation"] = accumulation_conditions[2]
    df["Distribution"] = (
        df["Price_Rising"] & ~df["CMF_Positive"] & ~df["Above_VWAP"]
    )
    df["Phase"] = np.select(
        [
            df["Strong_Accumulation"],
            df["Moderate_Accumulation"],
            df["Support_Accumulation"],
            df["Distribution"],
        ],
        [
            "Strong_Accumulation",
            "Moderate_Accumulation",
            "Support_Accumulation",
            "Distribution",
        ],
        default="Neutral",
    )

    # Generate scores first (used for display and analysis)
    df["Accumulation_Score"] = signal_generator.calculate_accumulation_score(df)
    df["Exit_Score"] = signal_generator.calculate_exit_score(df)
    df["Moderate_Buy_Score"] = signal_generator.calculate_moderate_buy_score(df)
    df["Profit_Taking_Score"] = signal_generator.calculate_profit_taking_score(df)
    df["Stealth_Accumulation_Score"] = (
        signal_generator.calculate_stealth_accumulation_score(df)
    )

    # Generate all signals using unified function (applies MINIMUM_ACCUMULATION_SCORE filter)
    # Updated 2025-11-22: Uses generate_all_entry_signals() which applies global threshold
    df = signal_generator.generate_all_entry_signals(df, apply_prefilters=False)
    df = signal_generator.generate_all_exit_signals(df)

    # Apply historical regime filter (bar-by-bar for backtest accuracy)
    # This eliminates lookahead bias by checking regime status for each historical date
    try:
        market_regime, sector_regime, overall_regime = (
            regime_filter.calculate_historical_regime_series(ticker, df)
        )
        
        # Add regime status columns
        df['Market_Regime_OK'] = market_regime
        df['Sector_Regime_OK'] = sector_regime
        df['Overall_Regime_OK'] = overall_regime
        
        # Preserve raw signals before filtering
        entry_signals = [
            'Strong_Buy', 'Moderate_Buy', 'Stealth_Accumulation',
            'Confluence_Signal', 'Volume_Breakout'
        ]
        
        for signal_col in entry_signals:
            # Preserve raw signal
            df[f'{signal_col}_raw'] = df[signal_col].copy()
            
            # Apply regime filter bar-by-bar
            df[signal_col] = df[signal_col] & df['Overall_Regime_OK']
        
        if verbose:
            filtered_count = sum(
                (df[f'{sig}_raw'].sum() - df[sig].sum()) 
                for sig in entry_signals
            )
            total_raw = sum(df[f'{sig}_raw'].sum() for sig in entry_signals)
            if filtered_count > 0:
                logger.info(f"🌍 Regime filter: {filtered_count}/{total_raw} signals filtered ({filtered_count/total_raw*100:.1f}%)")
            else:
                logger.info(f"🌍 Regime filter: All {total_raw} signals passed")
            
    except Exception as e:
        logger.warning(f"Failed to apply historical regime filter: {e}")
        logger.warning("Continuing without regime filtering")
        # Add default regime columns
        df['Market_Regime_OK'] = True
        df['Sector_Regime_OK'] = True
        df['Overall_Regime_OK'] = True
    
    # Apply momentum confirmation filter (2025-11-22)
    # Requires price above 20-day MA and positive CMF to reduce TIME_STOP rate
    df = momentum_confirmation.apply_momentum_filter(df, verbose=verbose)

    df = indicators.create_next_day_reference_levels(df)

    signal_columns = [
        "Strong_Buy",
        "Moderate_Buy",
        "Stealth_Accumulation",
        "Confluence_Signal",
        "Volume_Breakout",
        "Profit_Taking",
        "Distribution_Warning",
        "Sell_Signal",
        "Momentum_Exhaustion",
        "Stop_Loss",
    ]
    for column in signal_columns:
        df[f"{column}_display"] = df[column].shift(1)

    return df
