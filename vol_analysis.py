import pandas as pd
import numpy as np
import yfinance as yf
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

# Allow imports from the sibling charts project (../charts) if it exists.
PROJECT_ROOT = Path(__file__).resolve().parent
EXTERNAL_CHARTS_DIR = PROJECT_ROOT.parent / "charts"
if EXTERNAL_CHARTS_DIR.exists():
    charts_path = str(EXTERNAL_CHARTS_DIR)
    if charts_path not in sys.path:
        sys.path.append(charts_path)

# Import backtest module if available
try:
    import backtest
    BACKTEST_AVAILABLE = True
except ImportError:
    BACKTEST_AVAILABLE = False
    logger = get_logger()
    logger.warning("backtest.py not found - backtest functionality disabled")

# Import indicators module for technical calculations (core functions)
import indicators

# Import modular feature modules (Item #7: Refactor/Integration Plan)
import swing_structure
import volume_features

# Import signal generator module for buy/sell signals
import signal_generator
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
                "Ensure ../charts is accessible and Plotly dependencies are installed."
            ) from exc
    
    return chart_builder.generate_analysis_chart, 'png'

def read_ticker_file(ticker_file: str) -> List[str]:
    """
    Read ticker symbols from a file (one per line).
    
    Args:
        ticker_file (str): Path to file containing ticker symbols
        
    Returns:
        List[str]: List of ticker symbols
        
    Raises:
        FileOperationError: If file cannot be read
        DataValidationError: If no valid tickers found
    """
    with ErrorContext("reading ticker file", ticker_file=ticker_file):
        # Validate file path
        validate_file_path(ticker_file, check_exists=True, check_readable=True)
        
        logger = get_logger()
        tickers = []
        
        try:
            with open(ticker_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    ticker = line.strip().upper()
                    
                    # Skip empty lines and comments
                    if not ticker or ticker.startswith('#'):
                        continue
                    
                    # Basic ticker validation (alphanumeric, 1-5 chars)
                    if ticker.isalpha() and 1 <= len(ticker) <= 5:
                        tickers.append(ticker)
                    else:
                        logger.warning(f"Skipping invalid ticker on line {line_num}: '{ticker}'")
            
            if not tickers:
                raise DataValidationError(f"No valid ticker symbols found in {ticker_file}")
            
            logger.info(f"Read {len(tickers)} ticker symbols from {ticker_file}")
            return tickers
            
        except Exception as e:
            if isinstance(e, (DataValidationError, FileOperationError)):
                raise e
            else:
                raise FileOperationError(f"Failed to read ticker file {ticker_file}: {str(e)}")

def get_cache_directory() -> str:
    """Get or create the data cache directory."""
    cache_dir = os.path.join(os.getcwd(), 'data_cache')
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
        print(f"📁 Created cache directory: {cache_dir}")
    return cache_dir

def get_cache_filepath(ticker: str) -> str:
    """Get the cache file path for a given ticker."""
    cache_dir = get_cache_directory()
    return os.path.join(cache_dir, f"{ticker}_data.csv")

def load_cached_data(ticker: str) -> Optional[pd.DataFrame]:
    """
    Load cached data for a ticker if it exists and is valid.
    
    Args:
        ticker (str): Stock symbol
        
    Returns:
        Optional[pd.DataFrame]: Cached data if valid, None otherwise
        
    Raises:
        CacheError: If cache corruption is detected and cannot be recovered
    """
    with ErrorContext("loading cached data", ticker=ticker):
        # Validate ticker first
        validate_ticker(ticker)
        
        cache_file = get_cache_filepath(ticker)
        logger = get_logger()
        
        if not os.path.exists(cache_file):
            return None
        
        # Validate file path and permissions
        validate_file_path(cache_file, check_exists=True, check_readable=True)
        
        try:
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            
            # Validate cached data structure
            validate_dataframe(df, required_columns=['Open', 'High', 'Low', 'Close', 'Volume'])
            
            logger.info(f"Loaded cached data for {ticker}: {len(df)} days ({df.index[0].date()} to {df.index[-1].date()})")
            return df
            
        except (pd.errors.EmptyDataError, pd.errors.ParserError) as e:
            # Handle pandas-specific errors
            logger.warning(f"Corrupted cache file for {ticker}: {str(e)}")
            
            # Attempt to recover by removing corrupted cache
            recovery_result = safe_operation(
                lambda: os.remove(cache_file),
                f"removing corrupted cache file for {ticker}"
            )
            
            if recovery_result['success']:
                logger.info(f"Removed corrupted cache file for {ticker}")
            else:
                raise CacheError(f"Cache corruption detected for {ticker} and could not be cleaned up: {recovery_result['error']}")
            
            return None
            
        except Exception as e:
            # Handle other file system or data validation errors
            raise CacheError(f"Failed to load cached data for {ticker}: {str(e)}")

def save_to_cache(ticker: str, df: pd.DataFrame) -> None:
    """
    Save DataFrame to cache.
    
    Args:
        ticker (str): Stock symbol
        df (pd.DataFrame): Data to cache
        
    Raises:
        CacheError: If data cannot be saved to cache
        DataValidationError: If DataFrame is invalid
    """
    with ErrorContext("saving data to cache", ticker=ticker):
        # Validate inputs
        validate_ticker(ticker)
        validate_dataframe(df, required_columns=['Open', 'High', 'Low', 'Close', 'Volume'])
        
        cache_file = get_cache_filepath(ticker)
        logger = get_logger()
        
        # Validate cache directory exists and is writable
        cache_dir = os.path.dirname(cache_file)
        validate_file_path(cache_dir, check_exists=True, check_writable=True)
        
        try:
            df.to_csv(cache_file)
            logger.info(f"Cached data for {ticker}: {len(df)} days saved to cache")
            
        except Exception as e:
            raise CacheError(f"Failed to save cache for {ticker}: {str(e)}")

def append_to_cache(ticker: str, new_data: pd.DataFrame) -> None:
    """
    Append new data to existing cache file.
    
    Args:
        ticker (str): Stock symbol
        new_data (pd.DataFrame): New data to append
        
    Raises:
        CacheError: If data cannot be appended to cache
        DataValidationError: If DataFrame is invalid
    """
    with ErrorContext("appending data to cache", ticker=ticker):
        # Validate inputs
        validate_ticker(ticker)
        validate_dataframe(new_data, required_columns=['Open', 'High', 'Low', 'Close', 'Volume'])
        
        cache_file = get_cache_filepath(ticker)
        logger = get_logger()
        
        # Validate cache file exists and is writable
        validate_file_path(cache_file, check_exists=True, check_writable=True)
        
        try:
            # Append new data to the CSV file
            new_data.to_csv(cache_file, mode='a', header=False)
            logger.info(f"Appended {len(new_data)} new days to {ticker} cache")
            
        except Exception as e:
            raise CacheError(f"Failed to append to cache for {ticker}: {str(e)}")

def normalize_period(period: str) -> str:
    """
    Normalize period parameter to ensure compatibility with yfinance.
    Converts user-friendly periods to yfinance-compatible format.
    
    Args:
        period (str): User input period
        
    Returns:
        str: Normalized period compatible with yfinance
    """
    # Period mapping for common user inputs
    period_mapping = {
        '1yr': '12mo',
        '2yr': '24mo', 
        '3yr': '36mo',
        '5yr': '60mo',
        '10yr': '120mo',
        '1y': '12mo',
        '2y': '24mo',
        '5y': '60mo',
        '10y': '120mo'
    }
    
    normalized = period_mapping.get(period.lower(), period)
    print(f"📅 Period normalized: {period} → {normalized}")
    return normalized

def get_smart_data(ticker: str, period: str, force_refresh: bool = False) -> pd.DataFrame:
    """
    Smart data fetching with caching support.
    
    Args:
        ticker (str): Stock symbol
        period (str): Requested period (e.g., '6mo', '12mo')
        force_refresh (bool): If True, ignore cache and download fresh data
        
    Returns:
        pd.DataFrame: Stock data with OHLCV columns
        
    Raises:
        DataValidationError: If ticker or period is invalid
        DataDownloadError: If data cannot be downloaded from Yahoo Finance
        CacheError: If cache operations fail
    """
    with ErrorContext("smart data fetching", ticker=ticker, period=period, force_refresh=force_refresh):
        # Validate inputs
        validate_ticker(ticker)
        validate_period(period)
        
        logger = get_logger()
        
        # Normalize the period first
        period = normalize_period(period)
        
        # Convert period to days for calculations
        period_days = {
            '1d': 1, '5d': 5, '1mo': 30, '3mo': 90, '6mo': 180, 
            '12mo': 365, '24mo': 730, '36mo': 1095, '60mo': 1825, '120mo': 3650, 
            'ytd': 365, 'max': 7300
        }
        
        requested_days = period_days.get(period, 365)
        cutoff_date = datetime.now() - timedelta(days=requested_days)
        
        def download_and_validate_data(download_period=None, start_date=None):
            """Helper function to download and validate data from Yahoo Finance."""
            try:
                if start_date:
                    logger.info(f"Downloading data for {ticker} from {start_date}")
                    df = yf.download(ticker, start=start_date, interval='1d', auto_adjust=True)
                else:
                    logger.info(f"Downloading {download_period or period} data for {ticker}")
                    df = yf.download(ticker, period=download_period or period, interval='1d', auto_adjust=True)
                
                # Handle MultiIndex columns from yfinance
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(1)
                
                # Clean the data
                df.dropna(inplace=True)
                
                # Validate downloaded data
                if df.empty:
                    raise DataDownloadError(f"No data available for {ticker} (possibly delisted or invalid symbol)")
                
                # Validate required columns are present
                validate_dataframe(df, required_columns=['Open', 'High', 'Low', 'Close', 'Volume'])
                
                logger.info(f"Successfully downloaded {len(df)} days of data for {ticker}")
                return df
                
            except Exception as e:
                if "No data available" in str(e) or "possibly delisted" in str(e):
                    raise DataDownloadError(f"No data available for {ticker}: {str(e)}")
                else:
                    raise DataDownloadError(f"Failed to download data for {ticker}: {str(e)}")
        
        if force_refresh:
            logger.info(f"Force refresh enabled - downloading fresh data for {ticker}")
            df = download_and_validate_data()
            
            # Cache the downloaded data
            try:
                save_to_cache(ticker, df)
            except CacheError as e:
                # Log cache error but don't fail the operation
                logger.warning(f"Failed to cache data for {ticker}: {e}")
            
            return df
        
        # Try to load cached data
        try:
            cached_df = load_cached_data(ticker)
        except CacheError as e:
            # If cache is corrupted, proceed with fresh download
            logger.warning(f"Cache error for {ticker}: {e}. Proceeding with fresh download.")
            cached_df = None
        
        if cached_df is None:
            # No cache exists - download full period
            logger.info(f"No cache found for {ticker} - downloading {period} data from Yahoo Finance")
            df = download_and_validate_data()
            
            # Cache the downloaded data
            try:
                save_to_cache(ticker, df)
            except CacheError as e:
                # Log cache error but don't fail the operation
                logger.warning(f"Failed to cache data for {ticker}: {e}")
            
            return df
        
        # Check if cached data covers the requested period
        cache_start_date = cached_df.index[0]
        cache_end_date = cached_df.index[-1]
        
        # Check if we need to download more recent data
        today = datetime.now().date()
        last_cached_date = cache_end_date.date()
        days_behind = (today - last_cached_date).days
        
        # Check if cache goes back far enough to cover requested period
        if cache_start_date > cutoff_date:
            logger.warning(f"Cache only goes back to {cache_start_date.date()}, but need data from {cutoff_date.date()}")
            logger.info(f"Downloading full {period} period for {ticker}...")
            
            # Download full period
            df = download_and_validate_data()
            
            # Update cache with full period data
            try:
                save_to_cache(ticker, df)
            except CacheError as e:
                # Log cache error but don't fail the operation
                logger.warning(f"Failed to update cache for {ticker}: {e}")
            
            return df
        
        if days_behind <= 1:
            # Cache is up to date (within 1 day) and covers the full period
            logger.info(f"Cache is current for {ticker} - using cached data")
            # Filter cached data to requested period if needed
            filtered_df = cached_df[cached_df.index >= cutoff_date] if cutoff_date > cache_start_date else cached_df
            return filtered_df
        
        # Need to download recent data
        logger.info(f"Cache is {days_behind} days behind - downloading recent data for {ticker}")
        
        # Download from day after last cached date to today
        start_date = (cache_end_date + timedelta(days=1)).strftime('%Y-%m-%d')
        
        try:
            new_data = download_and_validate_data(start_date=start_date)
            
            # Append new data to cache
            try:
                append_to_cache(ticker, new_data)
                
                # Combine cached and new data
                combined_df = pd.concat([cached_df, new_data])
                combined_df = combined_df[~combined_df.index.duplicated(keep='last')]  # Remove any duplicates
                combined_df.sort_index(inplace=True)
                
                # Update the cache with the complete dataset
                save_to_cache(ticker, combined_df)
                
                # Filter to requested period
                filtered_df = combined_df[combined_df.index >= cutoff_date] if cutoff_date > combined_df.index[0] else combined_df
                return filtered_df
                
            except CacheError as e:
                # If cache operations fail, return combined data without caching
                logger.warning(f"Failed to update cache for {ticker}: {e}")
                combined_df = pd.concat([cached_df, new_data])
                combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                combined_df.sort_index(inplace=True)
                filtered_df = combined_df[combined_df.index >= cutoff_date] if cutoff_date > combined_df.index[0] else combined_df
                return filtered_df
                
        except DataDownloadError as e:
            logger.warning(f"No new data available for {ticker}: {e}")
            # Return existing cached data
            filtered_df = cached_df[cached_df.index >= cutoff_date] if cutoff_date > cache_start_date else cached_df
            return filtered_df

def clear_cache(ticker: str = None) -> None:
    """
    Clear cache for a specific ticker or all tickers.
    
    Args:
        ticker (str, optional): Specific ticker to clear cache for. If None, clears entire cache.
    """
    cache_dir = get_cache_directory()
    
    if ticker:
        # Clear specific ticker cache
        cache_file = get_cache_filepath(ticker)
        if os.path.exists(cache_file):
            os.remove(cache_file)
            print(f"🗑️  Cleared cache for {ticker}")
        else:
            print(f"ℹ️  No cache found for {ticker}")
    else:
        # Clear entire cache directory
        if os.path.exists(cache_dir):
            import shutil
            shutil.rmtree(cache_dir)
            print(f"🗑️  Cleared entire cache directory")
        else:
            print(f"ℹ️  No cache directory found")

def list_cache_info() -> None:
    """Display information about cached data."""
    cache_dir = get_cache_directory()
    
    if not os.path.exists(cache_dir):
        print("ℹ️  No cache directory found")
        return
    
    cache_files = [f for f in os.listdir(cache_dir) if f.endswith('_data.csv')]
    
    if not cache_files:
        print("ℹ️  No cached data found")
        return
    
    print(f"\n📁 CACHE INFORMATION ({len(cache_files)} tickers cached)")
    print("="*60)
    
    total_size = 0
    for cache_file in sorted(cache_files):
        ticker = cache_file.replace('_data.csv', '')
        cache_path = os.path.join(cache_dir, cache_file)
        
        try:
            # Get file info
            file_size = os.path.getsize(cache_path)
            total_size += file_size
            modified_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
            
            # Read first and last dates
            df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            start_date = df.index[0].strftime('%Y-%m-%d')
            end_date = df.index[-1].strftime('%Y-%m-%d')
            days_count = len(df)
            
            # Calculate days behind
            today = datetime.now().date()
            last_date = df.index[-1].date()
            days_behind = (today - last_date).days
            
            status = "🟢 Current" if days_behind <= 1 else f"🟡 {days_behind}d behind" if days_behind <= 7 else f"🔴 {days_behind}d behind"
            
            print(f"  {ticker:6s}: {days_count:4d} days ({start_date} to {end_date}) - {status}")
            print(f"          Size: {file_size/1024:.1f}KB, Modified: {modified_time.strftime('%Y-%m-%d %H:%M')}")
            
        except Exception as e:
            print(f"  {ticker:6s}: ❌ Error reading cache ({e})")
    
    print(f"\nTotal cache size: {total_size/1024:.1f}KB")


def generate_analysis_text(ticker: str, df: pd.DataFrame, period: str) -> str:
    """
    Generate text analysis report for a ticker.
    
    Args:
        ticker (str): Stock symbol
        df (pd.DataFrame): Analysis results dataframe
        period (str): Analysis period
        
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
                   force_refresh=False, show_chart=True, show_summary=True, debug=False,
                   chart_backend: str = 'matplotlib'):
    """
    Retrieve and analyze price-volume data for a given ticker symbol.
    
    Args:
        ticker (str): Stock symbol, e.g. 'AAPL' or 'MSFT'
        period (str): Data period, e.g. '12mo', '6mo', '36mo'
        save_to_file (bool): Whether to save analysis to file instead of printing
        output_dir (str): Directory to save output files
        save_chart (bool): Whether to save chart as PNG file
        force_refresh (bool): If True, ignore cache and download fresh data
        show_chart (bool): Whether to display chart interactively (default: True)
        show_summary (bool): Whether to print detailed summary output (default: True)
        debug (bool): Enable additional progress prints when saving artifacts
        chart_backend (str): Chart engine to use ('matplotlib' for PNG, 'plotly' for interactive HTML)
        
    Raises:
        DataValidationError: If ticker or period is invalid
        DataDownloadError: If data cannot be retrieved
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
        
        # --- Retrieve Data with Smart Caching ---
        try:
            df = get_smart_data(ticker, period, force_refresh=force_refresh)
            logger.info(f"Retrieved {len(df)} days of data for {ticker} ({period})")
        except (DataValidationError, DataDownloadError, CacheError) as e:
            # Re-raise specific error handling exceptions
            raise e
        except Exception as e:
            # Catch any other unexpected errors
            raise DataDownloadError(f"Failed to get data for {ticker}: {str(e)}")
    
    # --- CMF (Chaikin Money Flow) - Replaces OBV and A/D Line ---
    # Item #10: Volume Flow Simplification (now in volume_features module)
    df['CMF_20'] = volume_features.calculate_cmf(df, period=20)
    df['CMF_Z'] = volume_features.calculate_cmf_zscore(df, cmf_period=20, zscore_window=20)
    
    # --- Rolling correlation between price and volume ---
    df['PriceVolumeCorr'] = indicators.calculate_price_volume_correlation(df, window=20)
    
    # --- Enhanced Volume Flow Detection (using CMF) ---
    
    # 1. Price Trend Analysis (for divergence detection)
    df['Price_MA'] = df['Close'].rolling(window=10).mean()
    df['Price_Trend'] = df['Close'] > df['Price_MA']
    df['Price_Rising'] = df['Close'] > df['Close'].shift(5)
    
    # 2. CMF-based divergence signals
    # CMF positive indicates buying pressure, negative indicates selling pressure
    df['CMF_Positive'] = df['CMF_Z'] > 0
    df['CMF_Strong'] = df['CMF_Z'] > 1.0  # Strong buying pressure (>1 std dev)
    
    # --- Legacy columns for backward compatibility with exit signals ---
    # Compute actual OBV and A/D Line values for chart display and legacy logic
    price_delta = df['Close'].diff().fillna(0)
    obv_direction = np.sign(price_delta).fillna(0)
    df['OBV'] = (obv_direction * df['Volume']).fillna(0).cumsum()
    df['OBV_MA'] = df['OBV'].rolling(window=10).mean()
    df['OBV_Trend'] = (df['OBV'] > df['OBV_MA']).fillna(False)

    high_low_range = (df['High'] - df['Low']).replace(0, np.nan)
    money_flow_multiplier = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / high_low_range
    money_flow_multiplier = money_flow_multiplier.replace([np.inf, -np.inf], 0).fillna(0)
    money_flow_volume = money_flow_multiplier * df['Volume']
    df['AD_Line'] = money_flow_volume.cumsum()
    df['AD_MA'] = df['AD_Line'].rolling(window=10).mean()
    df['AD_Rising'] = df['AD_Line'].diff().fillna(0) > 0
    
    # 3. Volume Analysis (now using volume_features module)
    df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Spike'] = df['Volume'] > (df['Volume_MA'] * 1.5)  # 50% above average
    df['Relative_Volume'] = volume_features.calculate_volume_surprise(df, window=20)
    
    # 4. Smart Money Indicators (Anchored VWAP from meaningful pivots)
    df['VWAP'] = indicators.calculate_anchored_vwap(df)
    df['Above_VWAP'] = df['Close'] > df['VWAP']
    
    # 5. Swing-Based Support/Resistance Analysis (now using swing_structure module)
    df['Recent_Swing_Low'], df['Recent_Swing_High'] = swing_structure.calculate_swing_levels(df, lookback=3)
    df['Near_Support'], df['Lost_Support'], df['Near_Resistance'] = swing_structure.calculate_swing_proximity_signals(
        df, df['Recent_Swing_Low'], df['Recent_Swing_High'], atr_series=None, use_volatility_aware=False
    )
    
    # Maintain backward compatibility by creating Support_Level alias
    df['Support_Level'] = df['Recent_Swing_Low']
    
    # --- True Range and ATR for Event Day Detection (Item #3: News/Event Spike Filter) ---
    df['TR'], df['ATR20'] = indicators.calculate_atr(df, period=20)
    
    # --- Event Day Detection (News/Earnings Spikes) - now using volume_features module ---
    df['Event_Day'] = volume_features.detect_event_days(
        df, 
        atr_multiplier=2.5,  # ATR spike threshold 
        volume_threshold=2.0  # Volume spike threshold
    )
    
    # --- Feature Standardization (Item #12: Z-Score Normalization) ---
    # Convert features to z-scores for consistent weighting across stocks
    # This adds Volume_Z, CMF_Z, TR_Z, ATR_Z columns
    df = indicators.standardize_features(df, window=20)
    
    # --- Pre-Trade Quality Filters (Item #11) ---
    # Apply pre-filters to reject unfilterable signals:
    # - Insufficient liquidity (< $5M average daily dollar volume)
    # - Price too low (< $3.00)
    # - Within earnings window (T-3 to T+3 around earnings dates)
    df = indicators.apply_prefilters(
        ticker=ticker,
        df=df,
        min_dollar_volume=5_000_000,  # $5M minimum
        min_price=3.00,  # $3 minimum
        earnings_window_days=3  # T-3 to T+3
    )
    
    # --- Accumulation Signal Generation ---
    accumulation_conditions = [
        # Strong Accumulation: Multiple confirmations
        (df['AD_Rising'] & ~df['Price_Rising'] & df['Volume_Spike'] & df['Above_VWAP']),
        
        # Moderate Accumulation: OBV divergence with volume
        (df['OBV_Trend'] & ~df['Price_Trend'] & (df['Relative_Volume'] > 1.2)),
        
        # Support Accumulation: High volume near support
        (df['Near_Support'] & df['Volume_Spike'] & (df['Close'] > df['Close'].shift(1))),
        
        # Distribution: Price down with high volume
        ((df['Close'] < df['Close'].shift(1)) & df['Volume_Spike'] & ~df['AD_Rising'])
    ]
    
    accumulation_choices = ['Strong_Accumulation', 'Moderate_Accumulation', 'Support_Accumulation', 'Distribution']
    phase_categories = accumulation_choices + ['Neutral']
    phase_values = np.select(accumulation_conditions, accumulation_choices, default='Neutral')
    phase_categorical = pd.Categorical(phase_values, categories=phase_categories, ordered=False)
    df['Phase'] = pd.Series(phase_categorical, index=df.index)
    
    # --- Use Signal Generator for Scoring ---
    df['Accumulation_Score'] = signal_generator.calculate_accumulation_score(df)
    df['Exit_Score'] = signal_generator.calculate_exit_score(df)
    
    # --- Calculate Empirical Signal Scores (Item #8) ---
    df['Moderate_Buy_Score'] = signal_generator.calculate_moderate_buy_score(df)
    df['Profit_Taking_Score'] = signal_generator.calculate_profit_taking_score(df)
    df['Stealth_Accumulation_Score'] = signal_generator.calculate_stealth_accumulation_score(df)
    
    # --- Use Signal Generator for All Signal Detection ---
    
    # ENTRY SIGNALS - Generate all buy signals using signal_generator module
    df['Strong_Buy'] = signal_generator.generate_strong_buy_signals(df)
    df['Moderate_Buy'] = signal_generator.generate_moderate_buy_signals(df)
    df['Stealth_Accumulation'] = signal_generator.generate_stealth_accumulation_signals(df)
    df['Confluence_Signal'] = signal_generator.generate_confluence_signals(df)
    df['Volume_Breakout'] = signal_generator.generate_volume_breakout_signals(df)
    
    # --- Market/Sector Regime Filter (Item #6) ---
    # Apply regime filter to entry signals
    # Requires: SPY > 200DMA AND Sector ETF > 50DMA
    # This filter is applied AFTER all other signal generation
    # Original signals preserved in *_raw columns for analysis
    df = regime_filter.apply_regime_filter(df, ticker, verbose=show_summary)
    
    # EXIT SIGNALS - Generate all exit signals using signal_generator module
    df['Profit_Taking'] = signal_generator.generate_profit_taking_signals(df)
    df['Distribution_Warning'] = signal_generator.generate_distribution_warning_signals(df)
    df['Sell_Signal'] = signal_generator.generate_sell_signals(df)
    df['Momentum_Exhaustion'] = signal_generator.generate_momentum_exhaustion_signals(df)
    df['Stop_Loss'] = signal_generator.generate_stop_loss_signals(df)
    
    # --- Add Next-Day Reference Levels and Display Columns ---
    
    # Create reference levels for next-day decision making (documentation/clarity)
    df = indicators.create_next_day_reference_levels(df)
    
    # EXECUTION TIMING: Signals fire at close of day T, you act at open of day T+1
    # Create display versions of signals that show markers on the ACTION day (T+1)
    # This ensures chart markers appear when you would actually enter/exit
    signal_columns = [
        'Strong_Buy', 'Moderate_Buy', 'Stealth_Accumulation', 'Confluence_Signal', 
        'Volume_Breakout', 'Profit_Taking', 'Distribution_Warning', 'Sell_Signal', 
        'Momentum_Exhaustion', 'Stop_Loss'
    ]
    
    for col in signal_columns:
        # Shift signals by +1 day for chart display (marker shows on action day)
        df[f'{col}_display'] = df[col].shift(1)
    
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
                
                # Generate analysis text
                analysis_text = generate_analysis_text(ticker, df, period)
                
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
            print(f"  Market (SPY): {'✅' if regime_info['market_regime_ok'] else '❌'} ${regime_info.get('spy_close', 0):.2f} vs 200DMA ${regime_info.get('spy_200ma', 0):.2f}")
            print(f"  Sector ({regime_info.get('sector_etf', 'N/A')}): {'✅' if regime_info['sector_regime_ok'] else '❌'} ${regime_info.get('sector_close', 0):.2f} vs 50DMA ${regime_info.get('sector_50ma', 0):.2f}")
            if total_filtered > 0:
                print(f"  ⚠️  {total_filtered} signals filtered due to poor regime")
            
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
        '--chart-backend',
        choices=['matplotlib', 'plotly'],
        default='matplotlib',
        help='Select chart renderer: matplotlib (PNG) or plotly (interactive HTML in ../charts)'
    )
    
    parser.add_argument(
        '--multi',
        action='store_true',
        help='Run multi-timeframe analysis instead of single period (single ticker mode only)'
    )
    
    parser.add_argument(
        '--force-refresh',
        action='store_true',
        help='Force refresh - ignore cache and download fresh data'
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
        '--backtest',
        action='store_true',
        help='Run risk-managed backtest with full trade management (default mode - uses RiskManager for position sizing, stops, profit scaling)'
    )
    
    parser.add_argument(
        '--simple',
        action='store_true',
        help='Use simple entry-to-exit backtest instead of risk-managed (basic win rate analysis without position management)'
    )
    
    parser.add_argument(
        '--risk-managed',
        action='store_true',
        help='(Deprecated: now default) Run risk-managed backtest - kept for backward compatibility'
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
    
    args = parser.parse_args()

    # Configure logging verbosity based on debug flag
    log_level = "DEBUG" if args.debug else "WARNING"
    setup_logging(log_level=log_level)
    
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
                chart_backend=args.chart_backend,
                verbose=args.debug
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
                # Run single period analysis with force refresh option
                # Don't show chart or detailed summary if backtesting
                df = analyze_ticker(
                    ticker, 
                    period=args.period, 
                    force_refresh=args.force_refresh,
                    show_chart=not args.backtest,  # Hide chart when backtesting
                    show_summary=not args.backtest,  # Hide verbose summary when backtesting
                    debug=args.debug,
                    chart_backend=args.chart_backend
                )
                
                # Run backtest if requested (risk-managed is now default)
                if (args.backtest or args.risk_managed) and BACKTEST_AVAILABLE:
                    # Use simple backtest only if explicitly requested
                    if args.simple:
                        print(f"\n📊 Running simple entry-to-exit backtest for {ticker}...")
                        report = backtest.run_backtest(df, ticker, args.period, save_to_file=True)
                        print(report)
                    else:
                        # Default: Run risk-managed backtest with full trade management
                        print(f"\n🎯 Running risk-managed backtest for {ticker}...")
                        print("   (Use --simple flag for basic entry-to-exit analysis)")
                        try:
                            result = backtest.run_risk_managed_backtest(
                                df=df,
                                ticker=ticker,
                                account_value=100000,
                                risk_pct=0.75,
                                save_to_file=True
                            )
                        except ImportError as e:
                            print(f"\n⚠️  Error: {e}")
                            print("Make sure risk_manager.py is available in the current directory.")
                elif (args.backtest or args.risk_managed) and not BACKTEST_AVAILABLE:
                    print("\n⚠️  Warning: Backtest module not available. Skipping backtest analysis.")

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
