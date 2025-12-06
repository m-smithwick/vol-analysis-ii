import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse
import sys
import os
import importlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple

# Import error handling framework
from error_handler import (
    ErrorContext, DataValidationError, CacheError, DataDownloadError,
    FileOperationError, validate_ticker, validate_period, validate_dataframe,
    validate_file_path, safe_operation, get_logger, setup_logging
)

# Import configuration loader
from config_loader import load_config, ConfigValidationError

# Import data manager for smart data retrieval with multiple sources
from analysis_service import prepare_analysis_dataframe
from data_manager import (
    read_ticker_file as dm_read_ticker_file,
    clear_cache as dm_clear_cache,
    list_cache_info as dm_list_cache_info,
)

from signal_metadata import get_signal_meta

# Import chart builder module for visualization
import chart_builder

# Import batch processor module for multi-ticker processing
import batch_processor

# Import empirically validated signal thresholds
import threshold_config
import threshold_validation

# Import regime filter module for market/sector regime checks (Item #6)
import regime_filter


def resolve_chart_engine(chart_backend: str = 'matplotlib'):
    """
    Resolve the requested chart backend to a generator function and file extension.
    
    Args:
        chart_backend (str): Requested backend ('matplotlib' or 'plotly').
        
    Returns:
        Tuple[callable, str]: Chart generator function and file extension without dot.
        
    Raises:
        ValueError: If an unsupported backend is requested.
        ImportError: If the Plotly backend is requested but not available.
    """
    backend = (chart_backend or 'matplotlib').lower()
    if backend not in {'matplotlib', 'plotly'}:
        raise ValueError(f"Unsupported chart backend '{chart_backend}'. Choose 'matplotlib' or 'plotly'.")
    
    if backend == 'plotly':
        try:
            plotly_module = importlib.import_module('chart_builder_plotly')
            return plotly_module.generate_analysis_chart, 'html'
        except ModuleNotFoundError as exc:
            raise ImportError(
                "Plotly chart backend not available. "
                "Ensure chart_builder_plotly.py is in the current directory and Plotly dependencies are installed."
            ) from exc
    
    return chart_builder.generate_analysis_chart, 'png'

def read_ticker_file(ticker_file: str) -> List[str]:
    """Proxy to the centralized ticker file reader."""
    return dm_read_ticker_file(ticker_file)



def clear_cache(ticker: str = None) -> None:
    """Clear cache for a ticker (1d) or wipe the entire cache."""
    if ticker:
        dm_clear_cache(ticker.upper(), "1d")
        print(f"🗑️  Cleared cache for {ticker.upper()}")
    else:
        dm_clear_cache()
        print("🗑️  Cleared entire cache directory")

def list_cache_info() -> None:
    """Display cached file information using data_manager."""
    dm_list_cache_info()


def print_regime_status_table(df: pd.DataFrame, ticker: str, num_days: int = 10) -> None:
    """
    Print detailed regime status table for the last N trading days.
    
    Shows overall regime, market regime, sector regime, and all 11 sector ETF regimes.
    
    Args:
        df: DataFrame with regime columns
        ticker: Stock ticker symbol
        num_days: Number of recent days to display (default: 10)
    """
    # Get last N days - ensure no duplicates
    recent_df = df.tail(num_days * 2).copy()  # Get extra rows to account for potential duplicates
    
    # Remove any duplicate indices (keep the last occurrence of each date)
    if recent_df.index.duplicated().any():
        print(f"⚠️  Warning: Found {recent_df.index.duplicated().sum()} duplicate dates in DataFrame")
        recent_df = recent_df[~recent_df.index.duplicated(keep='last')]
    
    # Now get the actual last N days after deduplication
    recent_df = recent_df.tail(num_days)
    
    # Get ticker's assigned sector (from regime_filter module since column may not exist)
    assigned_sector = regime_filter.get_sector_etf(ticker)
    
    print(f"\n{'='*120}")
    print(f"REGIME STATUS - LAST {num_days} TRADING DAYS ({ticker})")
    print(f"Assigned Sector ETF: {assigned_sector}")
    print(f"{'='*120}")
    
    # Header row
    header = (
        f"{'Date':<12} | {'Overall':<7} | {'Market':<7} | "
        f"{'Sector':<7} | {'XLK':<4} | {'XLF':<4} | {'XLV':<4} | {'XLE':<4} | "
        f"{'XLY':<4} | {'XLP':<4} | {'XLI':<4} | {'XLU':<4} | {'XLRE':<4} | {'XLB':<4} | {'XLC':<4}"
    )
    print(header)
    print(f"{'-' * 120}")
    
    # Data rows
    for date, row in recent_df.iterrows():
        date_str = date.strftime('%Y-%m-%d')
        
        # Get regime values (handle missing columns gracefully)
        overall = '✅' if row.get('Overall_Regime_OK', False) else '❌'
        market = '✅' if row.get('Market_Regime_OK', False) else '❌'
        sector = '✅' if row.get('Sector_Regime_OK', False) else '❌'
        
        # Individual sector ETF regimes
        xlk = '✅' if row.get('xlk_regime_ok', False) else '❌'
        xlf = '✅' if row.get('xlf_regime_ok', False) else '❌'
        xlv = '✅' if row.get('xlv_regime_ok', False) else '❌'
        xle = '✅' if row.get('xle_regime_ok', False) else '❌'
        xly = '✅' if row.get('xly_regime_ok', False) else '❌'
        xlp = '✅' if row.get('xlp_regime_ok', False) else '❌'
        xli = '✅' if row.get('xli_regime_ok', False) else '❌'
        xlu = '✅' if row.get('xlu_regime_ok', False) else '❌'
        xlre = '✅' if row.get('xlre_regime_ok', False) else '❌'
        xlb = '✅' if row.get('xlb_regime_ok', False) else '❌'
        xlc = '✅' if row.get('xlc_regime_ok', False) else '❌'
        
        # Print row
        row_str = (
            f"{date_str:<12} | {overall:<7} | {market:<7} | "
            f"{sector:<7} | {xlk:<4} | {xlf:<4} | {xlv:<4} | {xle:<4} | "
            f"{xly:<4} | {xlp:<4} | {xli:<4} | {xlu:<4} | {xlre:<4} | {xlb:<4} | {xlc:<4}"
        )
        print(row_str)
    
    print(f"{'='*120}")
    print(f"Legend: Overall = Market AND Sector both pass | Market = SPY > 200-day MA | Sector = Assigned ETF > 50-day MA")
    print(f"{'='*120}\n")


def generate_analysis_text(ticker: str, df: pd.DataFrame, period: str,
                          account_value: float = 100000, risk_pct: float = 0.75) -> str:
    """
    Generate text analysis report for a ticker.
    
    Args:
        ticker (str): Stock symbol
        df (pd.DataFrame): Analysis results dataframe
        period (str): Analysis period
        account_value (float): Account value for position sizing (default: 100000)
        risk_pct (float): Risk percentage per trade (default: 0.75)
        
    Returns:
        str: Formatted analysis report
    """
    output = []
    
    # Header
    phase_counts = df['Phase'].value_counts()
    output.append("=" * 60)
    output.append(f"📊 ACCUMULATION ANALYSIS FOR {ticker.upper()} ({period})")
    output.append("=" * 60)
    
    # Phase distribution
    output.append("\n📈 PHASE DISTRIBUTION:")
    for phase, count in phase_counts.items():
        percentage = (count / len(df)) * 100
        emoji = {"Strong_Accumulation": "🟢", "Moderate_Accumulation": "🟡", 
                "Support_Accumulation": "🟠", "Distribution": "🔴", "Neutral": "⚪"}.get(phase, "⚪")
        output.append(f"  {emoji} {phase}: {count} days ({percentage:.1f}%)")
    
    # Recent signals - use actual signal booleans and empirical scores (matches batch summary logic)
    recent_df = df.tail(10)
    
    # Check for any active signals using actual signal columns
    signal_columns = ['Moderate_Buy', 'Strong_Buy', 'Stealth_Accumulation', 
                     'Confluence_Signal', 'Volume_Breakout',
                     'Profit_Taking', 'Distribution_Warning', 'Sell_Signal',
                     'Momentum_Exhaustion', 'Stop_Loss']
    
    recent_signals = recent_df[recent_df[signal_columns].any(axis=1)]
    
    output.append(f"\n🔍 RECENT SIGNALS (Last 10 days) - Empirically Validated:")
    if not recent_signals.empty:
        for date, row in recent_signals.iterrows():
            # Get empirical scores
            moderate_score = row.get('Moderate_Buy_Score', 0)
            profit_score = row.get('Profit_Taking_Score', 0)
            stealth_score = row.get('Stealth_Accumulation_Score', 0)
            
            # Check which signals are active
            active_signals = []
            if row.get('Strong_Buy', False):
                active_signals.append('🟢 Strong Buy')
            if row.get('Moderate_Buy', False):
                active_signals.append(f'🟡 Moderate Buy (Score: {moderate_score:.1f})')
            if row.get('Stealth_Accumulation', False):
                active_signals.append(f'💎 Stealth Accumulation (Score: {stealth_score:.1f})')
            if row.get('Confluence_Signal', False):
                active_signals.append('⭐ Confluence')
            if row.get('Volume_Breakout', False):
                active_signals.append('🔥 Volume Breakout')
            if row.get('Profit_Taking', False):
                active_signals.append(f'🟠 Profit Taking (Score: {profit_score:.1f})')
            if row.get('Distribution_Warning', False):
                active_signals.append('⚠️ Distribution Warning')
            if row.get('Sell_Signal', False):
                active_signals.append('🔴 Sell Signal')
            if row.get('Momentum_Exhaustion', False):
                active_signals.append('💜 Momentum Exhaustion')
            if row.get('Stop_Loss', False):
                active_signals.append('🛑 Stop Loss')
            
            if active_signals:
                price = row['Close']
                volume_ratio = row['Relative_Volume']
                
                output.append(f"  {date.strftime('%Y-%m-%d')}: {', '.join(active_signals)}")
                output.append(f"    Price: ${price:.2f}, Volume: {volume_ratio:.1f}x average")
    else:
        output.append("  No significant signals in recent trading days")
    
    # Key metrics
    current_price = df['Close'].iloc[-1]
    current_vwap = df['VWAP'].iloc[-1]
    current_support = df['Support_Level'].iloc[-1]
    avg_acc_score = df['Accumulation_Score'].tail(20).mean()
    
    output.append(f"\n📊 KEY METRICS:")
    output.append(f"  Current Price: ${current_price:.2f}")
    output.append(f"  VWAP: ${current_vwap:.2f} ({'Above' if current_price > current_vwap else 'Below'} VWAP)")
    output.append(f"  Support Level: ${current_support:.2f}")
    output.append(f"  20-day Avg Accumulation Score: {avg_acc_score:.1f}/10")
    output.append(f"  Price-Volume Correlation: {df['PriceVolumeCorr'].mean():.3f}")
    
    # NEW SECTION: Variable Stop Loss Trade Setup
    current_atr = df['ATR20'].iloc[-1]
    current_atr_z = df['ATR_Z'].iloc[-1]
    swing_low = df['Recent_Swing_Low'].iloc[-1]
    
    # Determine volatility regime and multiplier
    if current_atr_z < -0.5:
        multiplier = 1.5
        regime = "🟢 LOW VOLATILITY"
        regime_desc = "Tighter stops appropriate"
    elif current_atr_z > 0.5:
        multiplier = 2.5
        regime = "🔴 HIGH VOLATILITY"
        regime_desc = "Wider stops for safety"
    else:
        multiplier = 2.0
        regime = "🟡 NORMAL VOLATILITY"
        regime_desc = "Standard stops"
    
    # Calculate stop levels
    vol_regime_stop = current_price - (current_atr * multiplier)
    static_stop = min(swing_low - (0.5 * current_atr), 
                     current_vwap - (1.0 * current_atr))
    
    # Position sizing (using provided account value and risk %)
    risk_per_share = current_price - vol_regime_stop
    position_size = int((account_value * risk_pct / 100) / risk_per_share)
    position_value = current_price * position_size
    
    output.append(f"\n💡 VARIABLE STOP LOSS TRADE SETUP:")
    output.append(f"  Based on Volatility Regime-Adjusted stops (371-trade validated, +30% improvement)")
    output.append("")
    output.append(f"  Current Regime: {regime} (ATR_Z: {current_atr_z:.2f})")
    output.append(f"  {regime_desc}")
    output.append(f"  Current ATR: ${current_atr:.2f}")
    output.append("")
    output.append(f"  📍 RECOMMENDED ENTRY: ${current_price:.2f}")
    output.append(f"  🛑 Vol Regime Stop: ${vol_regime_stop:.2f} ({multiplier}x ATR)")
    output.append(f"  📊 Static Stop (compare): ${static_stop:.2f}")
    output.append(f"  💰 Risk per Share: ${risk_per_share:.2f}")
    output.append(f"  📦 Position Size: {position_size:,} shares ({risk_pct}% risk on ${account_value:,})")
    output.append(f"  💵 Total Position Value: ${position_value:,.0f}")
    output.append("")
    output.append(f"  ℹ️  Stop adjusts dynamically based on volatility:")
    output.append(f"     • Low vol (ATR_Z < -0.5): 1.5 ATR stop (tighter)")
    output.append(f"     • Normal vol: 2.0 ATR stop (standard)")
    output.append(f"     • High vol (ATR_Z > +0.5): 2.5 ATR stop (wider)")
    output.append(f"     • Never lowers - only tightens as volatility decreases")
    
    # Accumulation opportunities
    high_score_days = df[df['Accumulation_Score'] >= 6]
    if not high_score_days.empty:
        output.append(f"\n🎯 HIGH CONFIDENCE ACCUMULATION OPPORTUNITIES:")
        output.append(f"  Found {len(high_score_days)} days with score ≥ 6.0")
        latest_opportunity = high_score_days.tail(1)
        if not latest_opportunity.empty:
            last_date = latest_opportunity.index[0]
            last_score = latest_opportunity['Accumulation_Score'].iloc[0]
            last_price = latest_opportunity['Close'].iloc[0]
            days_ago = (df.index[-1] - last_date).days
            output.append(f"  Most recent: {last_date.strftime('%Y-%m-%d')} (Score: {last_score:.1f}, Price: ${last_price:.2f})")
            output.append(f"  That was {days_ago} trading days ago")
    
    # Signal counts - Entry and Exit
    entry_signal_keys = [
        'Strong_Buy', 'Moderate_Buy', 'Stealth_Accumulation',
        'Confluence_Signal', 'Volume_Breakout'
    ]
    exit_signal_keys = [
        'Profit_Taking', 'Distribution_Warning', 'Sell_Signal',
        'Momentum_Exhaustion', 'Stop_Loss'
    ]
    
    output.append(f"\n🎯 ENTRY SIGNAL SUMMARY:")
    for key in entry_signal_keys:
        count = int(df[key].sum())
        meta = get_signal_meta(key)
        marker = meta.chart_marker
        detail = f"{marker} - {meta.description}" if marker else meta.description
        output.append(f"  {meta.display} Signals: {count} ({detail})")
    
    output.append(f"\n🚪 EXIT SIGNAL SUMMARY:")
    for key in exit_signal_keys:
        count = int(df[key].sum())
        meta = get_signal_meta(key)
        marker = meta.chart_marker
        detail = f"{marker} - {meta.description}" if marker else meta.description
        suffix = "Triggers" if key == 'Stop_Loss' else "Signals"
        output.append(f"  {meta.display} {suffix}: {count} ({detail})")
    
    output.append(f"\n📋 ANALYSIS PERIOD: {period}")
    output.append(f"📅 DATE RANGE: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
    output.append(f"📊 TOTAL TRADING DAYS: {len(df)}")
    
    return "\n".join(output)

def analyze_ticker(ticker: str, period='6mo', save_to_file=False, output_dir='.', save_chart=False,
                   force_refresh=False, cache_only=True, show_chart=True, show_summary=True, debug=False,
                   chart_backend: str = 'matplotlib', data_source: str = 'yfinance', config: dict = None,
                   account_value: float = 100000, risk_pct: float = 0.75):
    """
    Retrieve and analyze price-volume data for a given ticker symbol.
    
    Args:
        ticker (str): Stock symbol, e.g. 'AAPL' or 'MSFT'
        period (str): Data period, e.g. '12mo', '6mo', '36mo'
        save_to_file (bool): Whether to save analysis to file instead of printing
        output_dir (str): Directory to save output files
        save_chart (bool): Whether to save chart as PNG file
        force_refresh (bool): If True, ignore cache and download fresh data (overrides cache_only)
        cache_only (bool): If True, only use cached data - never download (default: True)
        show_chart (bool): Whether to display chart interactively (default: True)
        show_summary (bool): Whether to print detailed summary output (default: True)
        debug (bool): Enable additional progress prints when saving artifacts
        chart_backend (str): Chart engine to use ('matplotlib' for PNG, 'plotly' for interactive HTML)
        data_source (str): Data source to use ('yfinance' or 'massive')
        config (dict): Optional configuration dict from YAML config file
        account_value (float): Account value for position sizing (default: 100000)
        risk_pct (float): Risk percentage per trade (default: 0.75)
        
    Raises:
        DataValidationError: If ticker or period is invalid
        DataDownloadError: If data cannot be retrieved
        CacheError: If cache_only=True but no cache exists
        FileOperationError: If file operations fail during save
    """
    with ErrorContext("analyzing ticker", ticker=ticker, period=period):
        # Validate inputs
        validate_ticker(ticker)
        validate_period(period)
        
        # Validate output directory if saving files
        if save_to_file or save_chart:
            validate_file_path(output_dir, check_exists=True, check_writable=True)
        
        logger = get_logger()
    
    # Prepare analysis dataframe with config
    df = prepare_analysis_dataframe(
        ticker,
        period,
        data_source=data_source,
        force_refresh=force_refresh,
        cache_only=cache_only,
        verbose=show_summary,
        config=config,
    )
    
    # --- Generate Chart using selected Chart Builder Module ---
    if save_chart or show_chart:
        selected_backend = (chart_backend or 'matplotlib').lower()
        chart_generator, chart_extension = resolve_chart_engine(selected_backend)
        
        # Create chart filename with date range for save operations
        chart_path = None
        if save_chart:
            start_date = df.index[0].strftime('%Y%m%d')
            end_date = df.index[-1].strftime('%Y%m%d')
            chart_filename = f"{ticker}_{period}_{start_date}_{end_date}_chart.{chart_extension}"
            chart_path = os.path.join(output_dir, chart_filename)
            if debug:
                print(f"📊 Chart saved ({selected_backend}): {chart_filename}")
        
        chart_generator(
            df=df,
            ticker=ticker,
            period=period,
            save_path=chart_path,
            show=show_chart
        )
    
    # Handle text output with error handling
    if save_to_file:
        with ErrorContext("saving analysis to file", ticker=ticker, period=period):
            try:
                # Generate filename with date range
                start_date = df.index[0].strftime('%Y%m%d')
                end_date = df.index[-1].strftime('%Y%m%d')
                filename = f"{ticker}_{period}_{start_date}_{end_date}_analysis.txt"
                filepath = os.path.join(output_dir, filename)
                
                # Validate output directory is writable
                validate_file_path(output_dir, check_exists=True, check_writable=True)
                
                # Generate analysis text with account value and risk percentage
                analysis_text = generate_analysis_text(ticker, df, period, account_value, risk_pct)
                
                # Write to file with error handling
                try:
                    with open(filepath, 'w') as f:
                        f.write(analysis_text)
                    
                    logger.info(f"Analysis saved to {filename}")
                    return df, filepath
                    
                except Exception as e:
                    raise FileOperationError(f"Failed to write analysis file for {ticker}: {str(e)}")
                    
            except Exception as e:
                # Re-raise our custom exceptions, wrap others
                if isinstance(e, (FileOperationError, DataValidationError)):
                    raise e
                else:
                    raise FileOperationError(f"Failed to save analysis for {ticker}: {str(e)}")
    else:
        # Only print detailed summary if show_summary is True
        if show_summary:
            # --- Enhanced Summary with Accumulation Signals ---
            phase_counts = df['Phase'].value_counts()
            print("\n" + "="*60)
            print(f"📊 ACCUMULATION ANALYSIS FOR {ticker.upper()} ({period})")
            print("="*60)
            
            print("\n📈 PHASE DISTRIBUTION:")
            for phase, count in phase_counts.items():
                percentage = (count / len(df)) * 100
                emoji = {"Strong_Accumulation": "🟢", "Moderate_Accumulation": "🟡", 
                        "Support_Accumulation": "🟠", "Distribution": "🔴", "Neutral": "⚪"}.get(phase, "⚪")
                print(f"  {emoji} {phase}: {count} days ({percentage:.1f}%)")
            
            # Recent accumulation signals (last 10 trading days) with empirical thresholds
            recent_df = df.tail(10)
            recent_signals = recent_df[recent_df['Phase'] != 'Neutral']
            
            print(f"\n🔍 RECENT SIGNALS (Last 10 days) - EMPIRICALLY VALIDATED THRESHOLDS:")
            if not recent_signals.empty:
                for date, row in recent_signals.iterrows():
                    # Get empirical scores for current row
                    moderate_score = row['Moderate_Buy_Score']
                    profit_score = row['Profit_Taking_Score'] 
                    stealth_score = row['Stealth_Accumulation_Score']
                    
                    # Get validated thresholds
                    moderate_threshold = threshold_config.OPTIMAL_THRESHOLDS['moderate_buy']['threshold']
                    profit_threshold = threshold_config.OPTIMAL_THRESHOLDS['profit_taking']['threshold']
                    stealth_threshold = threshold_config.OPTIMAL_THRESHOLDS['stealth_accumulation']['threshold']
                    
                    # Check which signals exceed validated thresholds
                    moderate_exceeds = moderate_score >= moderate_threshold
                    profit_exceeds = profit_score >= profit_threshold
                    stealth_exceeds = stealth_score >= stealth_threshold
                    
                    # Determine primary signal type and strength
                    if profit_exceeds:
                        signal_type = "PROFIT_TAKING"
                        primary_score = profit_score
                        threshold_info = f"(exceeds {profit_threshold:.1f} threshold for 96.1% win rate)"
                    elif moderate_exceeds:
                        signal_type = "MODERATE_BUY"
                        primary_score = moderate_score
                        threshold_info = f"(exceeds {moderate_threshold:.1f} threshold for 64.3% win rate)"
                    elif stealth_exceeds:
                        signal_type = "STEALTH_ACCUMULATION"
                        primary_score = stealth_score
                        threshold_info = f"(exceeds {stealth_threshold:.1f} threshold for 58.7% win rate)"
                    else:
                        signal_type = row['Phase']
                        primary_score = row['Accumulation_Score']
                        threshold_info = "(below validated thresholds)"
                    
                    # Signal strength based on validated performance
                    if profit_exceeds or (moderate_exceeds and moderate_score >= 7.5):
                        signal_strength = "🔥 STRONG"
                    elif moderate_exceeds or stealth_exceeds:
                        signal_strength = "⚡ VALIDATED"
                    else:
                        signal_strength = "💡 WEAK"
                    
                    print(f"  {date.strftime('%Y-%m-%d')}: {signal_type} - Score: {primary_score:.1f} {signal_strength}")
                    print(f"    {threshold_info}")
                    print(f"    Price: ${row['Close']:.2f}, Volume: {row['Relative_Volume']:.1f}x average")
                    
                    # Show all empirical scores for reference
                    if moderate_exceeds or profit_exceeds or stealth_exceeds:
                        print(f"    📊 Scores: Moderate={moderate_score:.1f}, Profit={profit_score:.1f}, Stealth={stealth_score:.1f}")
            else:
                print("  No significant signals in recent trading days")
            
            # Key metrics
            current_price = df['Close'].iloc[-1]
            current_vwap = df['VWAP'].iloc[-1]
            current_support = df['Support_Level'].iloc[-1]
            avg_acc_score = df['Accumulation_Score'].tail(20).mean()
            
            print(f"\n📊 KEY METRICS:")
            print(f"  Current Price: ${current_price:.2f}")
            print(f"  VWAP: ${current_vwap:.2f} ({'Above' if current_price > current_vwap else 'Below'} VWAP)")
            print(f"  Support Level: ${current_support:.2f}")
            print(f"  20-day Avg Accumulation Score: {avg_acc_score:.1f}/10")
            print(f"  Price-Volume Correlation: {df['PriceVolumeCorr'].mean():.3f}")
            
            # Accumulation opportunities
            high_score_days = df[df['Accumulation_Score'] >= 6]
            if not high_score_days.empty:
                print(f"\n🎯 HIGH CONFIDENCE ACCUMULATION OPPORTUNITIES:")
                print(f"  Found {len(high_score_days)} days with score ≥ 6.0")
                latest_opportunity = high_score_days.tail(1)
                if not latest_opportunity.empty:
                    last_date = latest_opportunity.index[0]
                    last_score = latest_opportunity['Accumulation_Score'].iloc[0]
                    last_price = latest_opportunity['Close'].iloc[0]
                    days_ago = (df.index[-1] - last_date).days
                    print(f"  Most recent: {last_date.strftime('%Y-%m-%d')} (Score: {last_score:.1f}, Price: ${last_price:.2f})")
                    print(f"  That was {days_ago} trading days ago")
            
            # Get regime filter summary for display
            regime_info = regime_filter.get_regime_status(ticker)
            
            # Enhanced signal counts - Entry and Exit
            entry_signals = {
                'Strong_Buy': df['Strong_Buy'].sum(),
                'Moderate_Buy': df['Moderate_Buy'].sum(), 
                'Stealth_Accumulation': df['Stealth_Accumulation'].sum(),
                'Confluence_Signal': df['Confluence_Signal'].sum(),
                'Volume_Breakout': df['Volume_Breakout'].sum()
            }
            
            # Count regime-filtered signals (difference between raw and filtered)
            entry_signals_raw = {
                'Strong_Buy': df.get('Strong_Buy_raw', df['Strong_Buy']).sum(),
                'Moderate_Buy': df.get('Moderate_Buy_raw', df['Moderate_Buy']).sum(),
                'Stealth_Accumulation': df.get('Stealth_Accumulation_raw', df['Stealth_Accumulation']).sum(),
                'Confluence_Signal': df.get('Confluence_Signal_raw', df['Confluence_Signal']).sum(),
                'Volume_Breakout': df.get('Volume_Breakout_raw', df['Volume_Breakout']).sum()
            }
            
            total_filtered = sum(entry_signals_raw.values()) - sum(entry_signals.values())
            
            exit_signals = {
                'Profit_Taking': df['Profit_Taking'].sum(),
                'Distribution_Warning': df['Distribution_Warning'].sum(),
                'Sell_Signal': df['Sell_Signal'].sum(),
                'Momentum_Exhaustion': df['Momentum_Exhaustion'].sum(),
                'Stop_Loss': df['Stop_Loss'].sum()
            }
            
            print(f"\n🌍 REGIME FILTER STATUS (Item #6):")
            regime_status = "✅ PASS" if regime_info['overall_regime_ok'] else "❌ FAIL"
            print(f"  Overall Regime: {regime_status}")
            
            # Format SPY info (may be None in cache-only mode)
            spy_close = regime_info.get('spy_close')
            spy_200ma = regime_info.get('spy_200ma')
            if spy_close is not None and spy_200ma is not None:
                print(f"  Market (SPY): {'✅' if regime_info['market_regime_ok'] else '❌'} ${spy_close:.2f} vs 200DMA ${spy_200ma:.2f}")
            else:
                print(f"  Market (SPY): {'✅' if regime_info['market_regime_ok'] else '❌'} (cache data used)")
            
            # Format Sector info (may be None in cache-only mode)
            sector_close = regime_info.get('sector_close')
            sector_50ma = regime_info.get('sector_50ma')
            sector_etf = regime_info.get('sector_etf', 'N/A')
            if sector_close is not None and sector_50ma is not None:
                print(f"  Sector ({sector_etf}): {'✅' if regime_info['sector_regime_ok'] else '❌'} ${sector_close:.2f} vs 50DMA ${sector_50ma:.2f}")
            else:
                print(f"  Sector ({sector_etf}): {'✅' if regime_info['sector_regime_ok'] else '❌'} (cache data used)")
            if total_filtered > 0:
                print(f"  ⚠️  {total_filtered} signals filtered due to poor regime")
            
            # Print detailed regime status table
            print_regime_status_table(df, ticker, num_days=10)
            
            print(f"\n🎯 ENTRY SIGNAL SUMMARY:")
            print("  🟢 Strong Buy Signals: {} (Large green dots - Score ≥7, near support, above VWAP)".format(entry_signals['Strong_Buy']))
            print("  🟡 Moderate Buy Signals: {} (Medium yellow dots - Score 5-7, divergence signals)".format(entry_signals['Moderate_Buy']))
            print("  💎 Stealth Accumulation: {} (Cyan diamonds - High score, low volume)".format(entry_signals['Stealth_Accumulation']))
            print("  ⭐ Multi-Signal Confluence: {} (Magenta stars - All indicators aligned)".format(entry_signals['Confluence_Signal']))
            print("  🔥 Volume Breakouts: {} (Orange triangles - 2.5x+ volume)".format(entry_signals['Volume_Breakout']))
            if total_filtered > 0:
                print(f"  📊 Total signals before regime filter: {sum(entry_signals_raw.values())}")
                print(f"  🌍 Signals after regime filter: {sum(entry_signals.values())} ({total_filtered} filtered)")
            
            print(f"\n🚪 EXIT SIGNAL SUMMARY:")
            print("  🟠 Profit Taking: {} (Orange dots - New highs with waning accumulation)".format(exit_signals['Profit_Taking']))
            print("  ⚠️ Distribution Warning: {} (Gold squares - Early distribution signs)".format(exit_signals['Distribution_Warning']))
            print("  🔴 Sell Signals: {} (Red dots - Strong distribution below VWAP)".format(exit_signals['Sell_Signal']))
            print("  💜 Momentum Exhaustion: {} (Purple X's - Rising price, declining volume)".format(exit_signals['Momentum_Exhaustion']))
            print("  🛑 Stop Loss Triggers: {} (Dark red triangles - Support breakdown)".format(exit_signals['Stop_Loss']))
            
            # Enhanced exit strategy guidance
            current_exit_score = df['Exit_Score'].iloc[-1]
            exit_urgency = ("🚨 URGENT" if current_exit_score >= 8 else 
                           "⚠️ HIGH" if current_exit_score >= 6 else 
                           "💡 MODERATE" if current_exit_score >= 4 else 
                           "✅ LOW" if current_exit_score >= 2 else "🟢 MINIMAL")
            
            # Check for recent exit signals
            recent_exit_signals = df[['Profit_Taking', 'Distribution_Warning', 'Sell_Signal', 'Momentum_Exhaustion', 'Stop_Loss']].tail(5)
            has_recent_exit_signal = recent_exit_signals.any().any()
            latest_exit_signal = df[['Profit_Taking', 'Distribution_Warning', 'Sell_Signal', 'Momentum_Exhaustion', 'Stop_Loss']].iloc[-1].any()
            
            print(f"\n📊 CURRENT EXIT ANALYSIS:")
            print(f"  Current Exit Score: {current_exit_score:.1f}/10 - {exit_urgency}")
            print(f"  Latest Exit Signal: {'Yes' if latest_exit_signal else 'No'}")
            print(f"  Recent Exit Activity (5 days): {'Yes' if has_recent_exit_signal else 'No'}")
            
            # Enhanced recommendations based on exit score ranges
            if current_exit_score >= 8:
                print(f"  🎯 RECOMMENDATION: URGENT - Consider immediate exit or tight stop loss")
            elif current_exit_score >= 6:
                print(f"  🎯 RECOMMENDATION: HIGH RISK - Reduce position size significantly")
            elif current_exit_score >= 4:
                print(f"  🎯 RECOMMENDATION: MODERATE RISK - Monitor closely, consider partial exit")
            elif current_exit_score >= 2:
                print(f"  🎯 RECOMMENDATION: LOW RISK - Normal monitoring, position appears stable")
            else:
                print(f"  🎯 RECOMMENDATION: MINIMAL RISK - Position looks healthy for continued holding")
            
            # Additional context based on signal types
            if df['Stop_Loss'].iloc[-1]:
                print(f"  ⚠️ ALERT: Stop loss trigger detected - immediate action recommended")
            elif df['Profit_Taking'].iloc[-1]:
                print(f"  💰 OPPORTUNITY: Profit taking signal - consider taking partial profits")
            elif df['Distribution_Warning'].iloc[-1]:
                print(f"  👀 WATCH: Early distribution warning - prepare exit strategy")
            
            print(f"\n📋 ENHANCED CHART READING GUIDE:")
            print("  • Top Panel: Price with complete entry/exit signal system")
            print("  • Middle Panel: OBV & A/D Line with signal confirmations")
            print("  • Bottom Panel: Volume + dual scoring (Entry=Green, Exit=Red)")
            print("  • Green score >7 = Strong accumulation | Red score >5 = Exit consideration")
            print("  • Look for signal transitions: Entry→Hold→Exit phases")
            print("  • Best trades: Strong entry signals followed by clear exit signals")
            
            # --- Empirical Threshold Configuration Summary (Item #8) ---
            print(f"\n🎯 EMPIRICALLY VALIDATED SIGNAL THRESHOLDS:")
            print("="*60)
            print("  These thresholds are based on backtest optimization and historical performance:")
            print()
            
            for signal_type in ['moderate_buy', 'profit_taking', 'stealth_accumulation']:
                config = threshold_config.OPTIMAL_THRESHOLDS[signal_type]
                metrics = config['backtest_results']
                quality = threshold_config.get_threshold_quality(signal_type)
                
                # Quality emoji
                quality_emoji = {
                    "EXCELLENT": "✅",
                    "GOOD": "✅", 
                    "FAIR": "✓",
                    "POOR": "⚠️"
                }.get(quality, "❓")
                
                print(f"  {quality_emoji} {signal_type.replace('_', ' ').title()} Signal:")
                print(f"     Threshold: ≥{config['threshold']:.1f}")
                print(f"     Performance: {metrics['win_rate']:.1f}% win rate, {metrics['expectancy']:+.2f}% expectancy")
                print(f"     Sample: {metrics['sample_size']} trades, Quality: {quality}")
                print(f"     Usage: {config['usage_context']}")
                print()
            
            print(f"  💡 NOTE: Scores above these thresholds indicate statistically validated opportunities")
            print(f"  📊 Last optimized: {threshold_config.LAST_OPTIMIZATION_DATE} ({threshold_config.OPTIMIZATION_PERIOD} period)")
        
        return df

def multi_timeframe_analysis(ticker: str, periods=['1mo', '3mo', '6mo', '12mo'], chart_backend: str = 'matplotlib'):
    """
    Analyze accumulation signals across multiple timeframes for stronger confirmation.
    
    Args:
        ticker (str): Stock symbol to analyze.
        periods (List[str]): Collection of timeframe strings to process.
        chart_backend (str): Chart engine passed through to analyze_ticker.
    """
    print(f"\n🔍 MULTI-TIMEFRAME ACCUMULATION ANALYSIS FOR {ticker.upper()}")
    print("="*70)
    
    results = {}
    for period in periods:
        print(f"\n📅 Analyzing {period} timeframe...")
        df_temp = analyze_ticker(ticker, period=period, chart_backend=chart_backend)
        
        # Get recent accumulation metrics
        recent_score = df_temp['Accumulation_Score'].tail(5).mean()
        phase_counts = df_temp['Phase'].value_counts()
        acc_percentage = ((phase_counts.get('Strong_Accumulation', 0) + 
                          phase_counts.get('Moderate_Accumulation', 0) + 
                          phase_counts.get('Support_Accumulation', 0)) / len(df_temp)) * 100
        
        results[period] = {
            'recent_score': recent_score,
            'accumulation_percentage': acc_percentage,
            'total_days': len(df_temp),
            'latest_phase': df_temp['Phase'].iloc[-1]
        }
        
        print(f"  Recent 5-day avg score: {recent_score:.1f}/10")
        print(f"  Accumulation days: {acc_percentage:.1f}% of period")
        print(f"  Latest signal: {df_temp['Phase'].iloc[-1]}")
    
    print(f"\n📋 TIMEFRAME CONSENSUS:")
    avg_score = np.mean([r['recent_score'] for r in results.values()])
    avg_acc_pct = np.mean([r['accumulation_percentage'] for r in results.values()])
    
    consensus_strength = ("🔥 VERY STRONG" if avg_score >= 6 else 
                         "⚡ STRONG" if avg_score >= 4 else 
                         "💡 MODERATE" if avg_score >= 2 else "❄️ WEAK")
    
    print(f"  Multi-timeframe Average Score: {avg_score:.1f}/10 {consensus_strength}")
    print(f"  Average Accumulation Activity: {avg_acc_pct:.1f}%")
    
    return results


def main():
    """
    Main function to handle command-line arguments and run the analysis.
    """
    parser = argparse.ArgumentParser(
        description='📊 Advanced Stock Volume Analysis Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single ticker analysis
  python vol_analysis.py                     # Analyze AAPL with default 12-month period
  python vol_analysis.py TSLA                # Analyze TESLA with 12-month period
  python vol_analysis.py NVDA --period 6mo   # Analyze NVIDIA with 6-month period
  python vol_analysis.py MSFT -p 3mo         # Analyze Microsoft with 3-month period
  python vol_analysis.py GOOGL --multi       # Run multi-timeframe analysis
  python vol_analysis.py AAPL -p 36mo        # Analyze AAPL with 3-year period

  # Batch processing from file
  python vol_analysis.py --file stocks.txt                    # Process all tickers in stocks.txt
  python vol_analysis.py -f stocks.txt --period 6mo           # Process with 6-month period
  python vol_analysis.py -f stocks.txt --output-dir results   # Save to 'results' directory
  python vol_analysis.py -f stocks.txt --save-charts          # Also save chart images

Available periods: 1d, 5d, 1mo, 3mo, 6mo, 12mo, 24mo, 36mo, 60mo, ytd, max
Note: Legacy periods (1y, 2y, 5y, etc.) are automatically converted to month equivalents
        """
    )
    
    parser.add_argument(
        'ticker', 
        nargs='?', 
        default='AAPL',
        help='Stock ticker symbol (default: AAPL). Ignored if --file is used.'
    )
    
    parser.add_argument(
        '-f', '--file',
        help='Path to file containing ticker symbols (one per line). When used, processes all tickers in batch mode.'
    )
    
    parser.add_argument(
        '-p', '--period',
        default='12mo',
        help='Analysis period (default: 12mo). Options: 1d, 5d, 1mo, 3mo, 6mo, 12mo, 24mo, 36mo, 60mo, ytd, max'
    )
    
    
    parser.add_argument(
        '-o', '--output-dir',
        default='results_volume',
        help='Output directory for batch processing files (default: results_volume)'
    )
    
    parser.add_argument(
        '--save-charts',
        action='store_true',
        help='Save chart files (PNG for matplotlib, HTML for Plotly) during batch mode'
    )
    
    parser.add_argument(
        '--save-excel',
        action='store_true',
        help='Save Excel files with complete DataFrame data (requires openpyxl: pip install openpyxl)'
    )
    
    parser.add_argument(
        '--text-only',
        action='store_true',
        help='Text-only mode: skip all chart generation and HTML summary (fastest for large batches)'
    )
    
    parser.add_argument(
        '--chart-backend',
        choices=['matplotlib', 'plotly'],
        default='matplotlib',
        help='Select chart renderer: matplotlib (PNG) or plotly (interactive HTML)'
    )
    
    parser.add_argument(
        '--data-source',
        choices=['yfinance', 'massive'],
        default='yfinance',
        help='Data source to use: yfinance (default) or massive (Massive.com flat files)'
    )
    
    parser.add_argument(
        '--multi',
        action='store_true',
        help='Run multi-timeframe analysis instead of single period (single ticker mode only)'
    )
    
    parser.add_argument(
        '--force-refresh',
        action='store_true',
        help='Force refresh - ignore cache and download fresh data (overrides --cache-only)'
    )
    
    parser.add_argument(
        '--allow-download',
        action='store_true',
        help='Allow downloading from yfinance API if cache is missing/stale (default: cache-only mode)'
    )
    
    parser.add_argument(
        '--clear-cache',
        help='Clear cache for specific ticker or all tickers. Use "all" to clear entire cache, or specify ticker symbol.'
    )
    
    parser.add_argument(
        '--cache-info',
        action='store_true',
        help='Display information about cached data'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable verbose logging and progress output'
    )

    parser.add_argument(
        '--validate-thresholds',
        action='store_true',
        help='Run walk-forward threshold validation (Item #9)'
    )
    
    parser.add_argument(
        '--config',
        default='configs/conservative_config.yaml',
        help='Path to YAML configuration file (default: configs/conservative_config.yaml - empirically optimized 6.5 threshold, +45%% better expectancy). Overrides individual parameters.'
    )
    
    parser.add_argument(
        '--account-value',
        type=float,
        default=100000,
        help='Account value for position sizing (default: 100000 = $100K). Used for calculating position sizes in trade logs and volume results.'
    )
    
    parser.add_argument(
        '--risk-pct',
        type=float,
        default=0.75,
        help='Risk percentage per trade (default: 0.75%%). Recommended range: 0.5-1.0%%. Controls position sizing based on stop distance.'
    )
    
    args = parser.parse_args()
    
    # Load configuration if provided
    config_loader = None
    config_dict = None
    if args.config:
        try:
            print(f"\n📋 Loading configuration from {args.config}...")
            config_loader = load_config(args.config)
            config_loader.print_summary()
            config_dict = config_loader.config
            print("\n✅ Configuration will be applied to signal generation!")
            print(f"   Using threshold: {config_dict['signal_thresholds']['entry']['moderate_buy_pullback']:.1f} for Moderate Buy")
            print(f"   Using threshold: {config_dict['signal_thresholds']['entry']['strong_buy']:.1f} for Strong Buy\n")
        except (ConfigValidationError, FileNotFoundError) as e:
            print(f"❌ Configuration error: {e}")
            sys.exit(1)

    # Configure logging verbosity based on debug flag
    log_level = "DEBUG" if args.debug else "WARNING"
    setup_logging(log_level=log_level)
    
    # Validate risk management parameters
    if args.risk_pct < 0.1 or args.risk_pct > 2.0:
        print(f"⚠️  Warning: Risk percentage should be between 0.1% and 2.0%")
        print(f"   Current value: {args.risk_pct}%")
        print(f"   Proceeding anyway, but consider using recommended range: 0.5-1.0%")
    
    if args.account_value < 10000:
        print(f"⚠️  Warning: Account value seems very low: ${args.account_value:,.0f}")
        print(f"   Position sizing may result in very small positions")
    
    try:
        # Handle cache management commands first
        if args.clear_cache:
            if args.clear_cache.lower() == 'all':
                clear_cache()
            else:
                clear_cache(args.clear_cache.upper())
            return
        
        if args.cache_info:
            list_cache_info()
            return
        
        # Regular analysis modes
        if args.file:
            # Batch processing mode - use batch_processor module
            if args.debug:
                print(f"🚀 Starting batch processing from file: {args.file}")
            batch_processor.process_batch(
                ticker_file=args.file,
                period=args.period,
                output_dir=args.output_dir,
                save_charts=args.save_charts,
                save_excel=args.save_excel,
                text_only=args.text_only,
                chart_backend=args.chart_backend,
                verbose=args.debug,
                data_source=args.data_source
            )
            if args.debug:
                print(f"\n✅ Batch processing complete!")
        else:
            # Single ticker mode
            ticker = args.ticker.upper()
            print(f"🚀 Starting analysis for {ticker}...")
            
            if args.multi:
                # Run multi-timeframe analysis
                results = multi_timeframe_analysis(ticker, chart_backend=args.chart_backend)
            else:
                # Run single period analysis with cache-only mode (unless --allow-download specified)
                df = analyze_ticker(
                    ticker, 
                    period=args.period, 
                    force_refresh=args.force_refresh,
                    cache_only=not args.allow_download,
                    show_chart=True,
                    show_summary=True,
                    debug=args.debug,
                    chart_backend=args.chart_backend,
                    data_source=args.data_source,
                    config=config_dict,
                    account_value=args.account_value,
                    risk_pct=args.risk_pct
                )

                if args.validate_thresholds:
                    print(f"\n🧪 Running threshold walk-forward validation for {ticker}...")
                    try:
                        validation_config = threshold_validation.ThresholdValidationConfig()
                        validation_results = threshold_validation.run_walk_forward_validation(df, validation_config)
                        if not validation_results:
                            print("⚠️ Not enough data to create walk-forward windows. Try a longer period (e.g., 24mo).")
                        else:
                            report = threshold_validation.generate_validation_report(validation_results)
                            print("\n" + report)
                    except DataValidationError as err:
                        print(f"⚠️ Threshold validation failed: {err}")
                    except Exception as err:
                        print(f"⚠️ Unexpected error during validation: {err}")
            
            if args.debug:
                print(f"\n✅ Analysis complete for {ticker}!")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("Please check your inputs and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
