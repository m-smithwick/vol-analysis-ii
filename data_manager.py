"""
Data management module for stock data retrieval and caching.
"""

from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from pathlib import Path

# Import error handling framework
from error_handler import (
    ErrorContext, VolumeAnalysisError, DataValidationError, CacheError, FileOperationError,
    validate_ticker, validate_file_path, validate_dataframe, safe_operation, 
    setup_logging, logger
)

# Import schema management
from schema_manager import schema_manager

# Configure logging for this module
setup_logging()

def get_cache_directory() -> Path:
    """Get or create the data cache directory."""
    with ErrorContext("creating cache directory"):
        cache_dir = Path.cwd() / 'data_cache'
        if not cache_dir.exists():
            try:
                cache_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created cache directory: {cache_dir}")
            except OSError as e:
                raise FileOperationError(f"Failed to create cache directory {cache_dir}: {e}")
        return cache_dir

def get_cache_filepath(ticker: str, interval: str = "1d") -> str:
    """
    Get the cache file path for a given ticker and interval.
    
    Args:
        ticker (str): Stock symbol
        interval (str): Data interval ('1d', '1h', '30m', etc.)
        
    Returns:
        str: Path to the cache file
    """
    with ErrorContext("generating cache filepath", ticker=ticker, interval=interval):
        validate_ticker(ticker)
        cache_dir = get_cache_directory()
        return os.path.join(cache_dir, f"{ticker}_{interval}_data.csv")

def load_cached_data(ticker: str, interval: str = "1d") -> Optional[pd.DataFrame]:
    """
    Load cached data for a ticker if it exists and is valid with schema validation.
    
    Args:
        ticker (str): Stock symbol
        interval (str): Data interval ('1d', '1h', '30m', etc.)
        
    Returns:
        Optional[pd.DataFrame]: DataFrame with cached data, or None if cache not valid
    """
    with ErrorContext("loading cached data", ticker=ticker, interval=interval):
        validate_ticker(ticker)
        cache_file = get_cache_filepath(ticker, interval)
        
        if not os.path.exists(cache_file):
            return None
        
        def _load_cache():
            try:
                # Check for schema metadata first
                metadata = schema_manager.read_metadata_from_csv(cache_file)
                
                # Read the actual data (skip comment lines with metadata)
                df = pd.read_csv(cache_file, index_col=0, parse_dates=True, comment='#')
                
                # Validate cached data
                if df.empty:
                    logger.warning(f"Empty cache file for {ticker} ({interval}) - will redownload")
                    safe_operation("removing empty cache file", lambda: os.remove(cache_file))
                    return None
                
                # Check if file has invalid schema version that cannot be migrated
                if metadata and not schema_manager.is_valid_schema_version(metadata.get("schema_version")):
                    logger.warning(f"Invalid schema version in {ticker} ({interval}) cache - will redownload")
                    safe_operation("removing invalid cache file", lambda: os.remove(cache_file))
                    return None
                
                # Check if migration is needed
                if schema_manager.needs_migration(metadata):
                    logger.info(f"Cache file for {ticker} ({interval}) needs schema migration")
                    
                    # Attempt migration
                    if schema_manager.migrate_legacy_file(cache_file, ticker, interval):
                        # Reload after successful migration
                        metadata = schema_manager.read_metadata_from_csv(cache_file)
                        df = pd.read_csv(cache_file, index_col=0, parse_dates=True, comment='#')
                        logger.info(f"Successfully migrated and reloaded {ticker} ({interval}) cache")
                    else:
                        logger.warning(f"Migration failed for {ticker} ({interval}) - will redownload")
                        safe_operation("removing unmigrated cache file", lambda: os.remove(cache_file))
                        return None
                
                # Validate schema if metadata exists
                if metadata and not schema_manager.validate_schema(df, metadata):
                    logger.warning(f"Schema validation failed for {ticker} ({interval}) - will redownload")
                    safe_operation("removing invalid cache file", lambda: os.remove(cache_file))
                    return None
                
                validate_dataframe(df, schema_manager.schema_definitions[schema_manager.current_version]["required_columns"])
                
                # Ensure index is timezone-naive for consistent handling
                if df.index.tzinfo is not None:
                    df.index = df.index.tz_localize(None)
                
                # Log schema version if available
                schema_version = metadata.get('schema_version', 'legacy') if metadata else 'legacy'
                logger.info(f"Loaded cached data for {ticker} ({interval}): {len(df)} periods, schema v{schema_version}")
                return df
                
            except Exception as e:
                logger.warning(f"Error loading cache for {ticker} ({interval}): {e}")
                # Remove corrupted cache file
                safe_operation(f"removing corrupted cache file for {ticker}", lambda: os.remove(cache_file))
                return None
        
        return _load_cache()

def save_to_cache(ticker: str, df: pd.DataFrame, interval: str = "1d", auto_adjust: bool = True) -> None:
    """
    Save DataFrame to cache with schema versioning and metadata headers.
    
    Args:
        ticker (str): Stock symbol
        df (pd.DataFrame): Data to cache
        interval (str): Data interval ('1d', '1h', '30m', etc.)
        auto_adjust (bool): Whether auto-adjust was used in the download
    """
    with ErrorContext("saving data to cache", ticker=ticker, interval=interval):
        validate_ticker(ticker)
        validate_dataframe(df, schema_manager.schema_definitions[schema_manager.current_version]["required_columns"])
        cache_file = get_cache_filepath(ticker, interval)
        
        def _save_cache():
            # Standardize DataFrame before saving
            standardized_df = schema_manager._standardize_dataframe(df.copy(), ticker)
            
            # Create metadata header
            metadata = schema_manager.create_metadata_header(
                ticker=ticker,
                df=standardized_df,
                interval=interval,
                auto_adjust=auto_adjust,
                data_source="yfinance"
            )
            
            # Write file with metadata header
            with open(cache_file, 'w', newline='') as f:
                # Write metadata as comments
                f.write("# Volume Analysis System - Cache File\n")
                f.write(f"# Generated: {datetime.now().isoformat()}\n")
                f.write("# Metadata (JSON format):\n")
                
                import json
                metadata_json = json.dumps(metadata, indent=2)
                for line in metadata_json.split('\n'):
                    f.write(f"# {line}\n")
                f.write("#\n")
                
                # Write CSV data
                standardized_df.to_csv(f, index=True)
            
            logger.info(f"Cached data for {ticker} ({interval}): {len(standardized_df)} periods saved with schema v{metadata['schema_version']}")
        
        safe_operation(f"saving cache for {ticker} ({interval})", _save_cache)

def append_to_cache(ticker: str, new_data: pd.DataFrame, interval: str = "1d") -> None:
    """
    Append new data to existing cache file with schema validation.
    
    Args:
        ticker (str): Stock symbol
        new_data (pd.DataFrame): New data to append
        interval (str): Data interval ('1d', '1h', '30m', etc.)
    """
    with ErrorContext("appending data to cache", ticker=ticker, interval=interval):
        validate_ticker(ticker)
        validate_dataframe(new_data, schema_manager.schema_definitions[schema_manager.current_version]["required_columns"])
        cache_file = get_cache_filepath(ticker, interval)
        
        def _append_cache():
            # For schema-versioned files, we need to read existing data, combine, and rewrite
            # This ensures metadata integrity and proper data formatting
            existing_df = load_cached_data(ticker, interval)
            
            if existing_df is not None:
                # Combine existing and new data
                combined_df = pd.concat([existing_df, new_data])
                combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                combined_df.sort_index(inplace=True)
                
                # Save the combined data with updated metadata
                save_to_cache(ticker, combined_df, interval)
                logger.info(f"Appended {len(new_data)} new periods to {ticker} ({interval}) cache with schema update")
            else:
                # No existing cache, just save new data
                save_to_cache(ticker, new_data, interval)
                logger.info(f"Created new cache file for {ticker} ({interval}) with {len(new_data)} periods")
        
        safe_operation(f"appending to cache for {ticker} ({interval})", _append_cache)

def normalize_period(period: str) -> str:
    """
    Normalize period parameter to ensure compatibility.
    Converts user-friendly periods to standard format.
    
    Args:
        period (str): User input period
        
    Returns:
        str: Normalized period
    """
    with ErrorContext("normalizing period", period=period):
        if not isinstance(period, str) or not period.strip():
            raise DataValidationError("Period must be a non-empty string")
            
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
        logger.debug(f"Period normalized: {period} → {normalized}")
        return normalized

def get_smart_data(ticker: str, period: str, interval: str = "1d", force_refresh: bool = False, data_source: str = "yfinance") -> pd.DataFrame:
    """
    Cache-only data fetching with clear error messages when data is missing.
    
    This function ONLY returns cached data. For batch operations, this prevents
    yfinance API failures from breaking regime filters and other calculations.
    
    Args:
        ticker (str): Stock symbol
        period (str): Requested period (e.g., '6mo', '12mo') 
        interval (str): Data interval ('1d', '1h', '30m', '15m', etc.)
        force_refresh (bool): DEPRECATED - Use populate_cache.py to refresh data
        data_source (str): Data source preference ('yfinance' or 'massive')
        
    Returns:
        pd.DataFrame: Stock data with OHLCV columns from cache
        
    Raises:
        DataValidationError: If cache is missing or insufficient for the request
    """
    with ErrorContext("smart data retrieval", ticker=ticker, period=period, interval=interval, data_source=data_source):
        validate_ticker(ticker)
        
        if force_refresh:
            raise DataValidationError(
                f"\n{'='*70}\n"
                f"ERROR: force_refresh=True not supported in cache-only mode\n"
                f"{'='*70}\n"
                f"To refresh data for {ticker}, use:\n"
                f"  python populate_cache.py {ticker} --period {period} --force\n"
                f"\nFor batch refresh:\n"
                f"  echo \"{ticker}\" > refresh.txt\n"
                f"  python populate_cache_bulk.py --file refresh.txt --force\n"
                f"{'='*70}"
            )
    
    # Handle Massive.com data source
    if data_source == "massive":
        if interval != "1d":
            raise DataValidationError(f"Massive.com only supports daily data. Interval '{interval}' not supported")
        else:
            try:
                from massive_data_provider import get_massive_daily_data
                logger.info(f"Using Massive.com as data source for {ticker}")
                df = get_massive_daily_data(ticker, period)
                if not df.empty:
                    # Save to cache with same format as yfinance
                    save_to_cache(ticker, df, interval)
                    return df
                else:
                    raise DataValidationError(f"No data available from Massive.com for {ticker}")
            except Exception as e:
                raise DataValidationError(f"Error fetching from Massive.com for {ticker}: {e}")
    
    # CACHE-ONLY MODE: Only return data from cache
    # Normalize the period first
    period = normalize_period(period)
    
    # Try to load cached data
    cached_df = load_cached_data(ticker, interval)
    
    if cached_df is None:
        # No cache exists - provide clear error with populate instructions
        raise DataValidationError(
            f"\n{'='*70}\n"
            f"ERROR: No cache data found for {ticker}\n"
            f"{'='*70}\n"
            f"Requested: {period} of {interval} data\n"
            f"Cache location: data_cache/{ticker}_{interval}_data.csv\n\n"
            f"To fix this, populate the cache:\n"
            f"  python populate_cache.py {ticker} --period {period}\n"
            f"\nFor batch population:\n"
            f"  echo \"{ticker}\" > missing_data.txt\n"
            f"  python populate_cache_bulk.py --file missing_data.txt --months {period.replace('mo', '')}\n\n"
            f"Or use Massive.com data source:\n"
            f"  python populate_cache.py {ticker} --period {period} --data-source massive\n"
            f"{'='*70}"
        )
    
    # Calculate requested date range
    period_days = {
        '1d': 1, '5d': 5, '1mo': 30, '3mo': 90, '6mo': 180, 
        '12mo': 365, '24mo': 730, '36mo': 1095, '60mo': 1825, '120mo': 3650, 
        'ytd': 365, 'max': 7300
    }
    requested_days = period_days.get(period, 365)
    cutoff_date = datetime.now() - timedelta(days=requested_days)
    
    # Check if cached data covers the requested period
    cache_start_date = cached_df.index[0]
    cache_end_date = cached_df.index[-1]
    
    # Filter cached data to requested period
    if cutoff_date > cache_start_date:
        filtered_df = cached_df[cached_df.index >= cutoff_date]
    else:
        filtered_df = cached_df
    
    if filtered_df.empty:
        raise DataValidationError(
            f"\n{'='*70}\n"
            f"ERROR: Insufficient cache data for {ticker}\n"
            f"{'='*70}\n"
            f"Requested: {period} ({requested_days} days) of {interval} data\n"
            f"Cache contains: {len(cached_df)} periods from {cache_start_date.date()} to {cache_end_date.date()}\n"
            f"Cache location: data_cache/{ticker}_{interval}_data.csv\n\n"
            f"To fix this, populate more historical data:\n"
            f"  python populate_cache.py {ticker} --period {period}\n"
            f"\nFor batch population:\n"
            f"  echo \"{ticker}\" > extend_data.txt\n" 
            f"  python populate_cache_bulk.py --file extend_data.txt --months {period.replace('mo', '')}\n"
            f"{'='*70}"
        )
    
    logger.info(f"Retrieved {len(filtered_df)} periods from cache for {ticker} ({period}) - using cache-only mode")
    return filtered_df

def get_intraday_data(ticker: str, days: int = 5, interval: str = "1h", force_refresh: bool = False) -> pd.DataFrame:
    """
    Get intraday data for specific number of days.
    
    Args:
        ticker (str): Stock symbol
        days (int): Number of days to retrieve
        interval (str): Intraday interval ('1h', '30m', '15m', '5m', '1m')
        force_refresh (bool): If True, ignore cache and download fresh data
        
    Returns:
        pd.DataFrame: Intraday stock data
    """
    # Convert days to a period parameter for yfinance
    if days <= 5:
        period = f"{days}d"
    elif days <= 30:
        period = "1mo"
    else:
        period = "2mo"  # Maximum reasonable period for intraday data
    
    # Get the data
    df = get_smart_data(ticker=ticker, period=period, interval=interval, force_refresh=force_refresh)
    
    # Ensure index is timezone-naive for consistent comparisons across the codebase
    if df.index.tzinfo is not None:
        df.index = df.index.tz_localize(None)
    
    return df

def normalize_datetime(dt):
    """
    Ensure datetime object is timezone-naive.
    
    Args:
        dt: datetime object to normalize
        
    Returns:
        datetime: A timezone-naive datetime object
    """
    if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt

def clear_cache(ticker: str = None, interval: str = None) -> None:
    """
    Clear cache for a specific ticker and interval or all cache.
    
    Args:
        ticker (str, optional): Specific ticker to clear cache for. If None, clears for all tickers.
        interval (str, optional): Specific interval to clear cache for. If None, clears for all intervals.
    """
    with ErrorContext("clearing cache", ticker=ticker, interval=interval):
        cache_dir = get_cache_directory()
        
        if ticker and interval:
            # Clear specific ticker and interval cache
            validate_ticker(ticker)
            cache_file = get_cache_filepath(ticker, interval)
            if os.path.exists(cache_file):
                safe_operation(f"removing cache file {cache_file}", lambda: os.remove(cache_file))
                logger.info(f"Cleared cache for {ticker} ({interval})")
            else:
                logger.info(f"No cache found for {ticker} ({interval})")
        
        elif ticker:
            # Clear all intervals for specific ticker
            validate_ticker(ticker)
            files_removed = 0
            for file in os.listdir(cache_dir):
                if file.startswith(f"{ticker}_") and file.endswith("_data.csv"):
                    safe_operation(f"removing cache file {file}", lambda: os.remove(os.path.join(cache_dir, file)))
                    files_removed += 1
            
            if files_removed > 0:
                logger.info(f"Cleared {files_removed} cache files for {ticker}")
            else:
                logger.info(f"No cache files found for {ticker}")
        
        else:
            # Clear entire cache directory
            if os.path.exists(cache_dir):
                def _clear_cache_dir():
                    import shutil
                    shutil.rmtree(cache_dir)
                    os.makedirs(cache_dir)
                
                safe_operation("clearing entire cache directory", _clear_cache_dir)
                logger.info(f"Cleared entire cache directory")
            else:
                logger.info(f"No cache directory found")

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
    
    print(f"\n📁 CACHE INFORMATION ({len(cache_files)} files cached)")
    print("="*60)
    
    total_size = 0
    
    # Group by ticker
    ticker_files = {}
    for cache_file in cache_files:
        parts = cache_file.split('_')
        ticker = parts[0]
        interval = '_'.join(parts[1:-1])  # Handle multi-part intervals like '1h_data.csv'
        
        if ticker not in ticker_files:
            ticker_files[ticker] = []
        
        ticker_files[ticker].append((interval, cache_file))
    
    # Display info by ticker
    for ticker, files in sorted(ticker_files.items()):
        print(f"\n📊 {ticker}:")
        
        for interval, cache_file in sorted(files):
            cache_path = os.path.join(cache_dir, cache_file)
            
            try:
                # Get file info
                file_size = os.path.getsize(cache_path)
                total_size += file_size
                modified_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
                
                # Read first and last dates
                df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
                start_date = df.index[0].strftime('%Y-%m-%d %H:%M') if not df.empty else "N/A"
                end_date = df.index[-1].strftime('%Y-%m-%d %H:%M') if not df.empty else "N/A"
                days_count = len(df)
                
                # Calculate days behind
                today = datetime.now()
                last_date = df.index[-1] if not df.empty else today
                
                if interval == "1d":
                    days_behind = (today.date() - last_date.date()).days
                    status = "🟢 Current" if days_behind <= 1 else f"🟡 {days_behind}d behind" if days_behind <= 7 else f"🔴 {days_behind}d behind"
                else:
                    # For intraday, show hours behind
                    hours_behind = (today - last_date).total_seconds() / 3600
                    if hours_behind < 24:
                        status = f"🟢 {hours_behind:.1f}h behind"
                    else:
                        days = int(hours_behind / 24)
                        status = f"🟡 {days}d behind" if days <= 3 else f"🔴 {days}d behind"
                
                print(f"  {interval:4s}: {days_count:6d} periods ({start_date} to {end_date}) - {status}")
                print(f"          Size: {file_size/1024:.1f}KB, Modified: {modified_time.strftime('%Y-%m-%d %H:%M')}")
                
            except Exception as e:
                print(f"  {interval:4s}: ❌ Error reading cache ({e})")
    
    print(f"\nTotal cache size: {total_size/1024:.1f}KB")

def query_cache_by_date_range(
    ticker: str,
    start_date: datetime,
    end_date: datetime,
    interval: str = "1d"
) -> Optional[pd.DataFrame]:
    """
    Query cached data for a specific date range.
    
    Args:
        ticker (str): Stock symbol
        start_date (datetime): Start date (inclusive)
        end_date (datetime): End date (inclusive)
        interval (str): Data interval ('1d', '1h', '30m', etc.)
        
    Returns:
        Optional[pd.DataFrame]: DataFrame filtered to date range, or None if not in cache
    """
    with ErrorContext("querying cache by date range", ticker=ticker, start_date=start_date, end_date=end_date, interval=interval):
        validate_ticker(ticker)
        
        # Load full cached data
        cached_df = load_cached_data(ticker, interval)
        
        if cached_df is None:
            logger.debug(f"No cached data found for {ticker} ({interval})")
            return None
        
        # Ensure dates are timezone-naive for comparison
        start_date = normalize_datetime(start_date)
        end_date = normalize_datetime(end_date)
        
        # Filter to requested date range
        mask = (cached_df.index >= start_date) & (cached_df.index <= end_date)
        filtered_df = cached_df[mask]
        
        if filtered_df.empty:
            logger.debug(f"No data in cache for {ticker} in range {start_date.date()} to {end_date.date()}")
            return None
        
        logger.info(f"Retrieved {len(filtered_df)} periods from cache for {ticker} ({start_date.date()} to {end_date.date()})")
        return filtered_df

def get_cache_date_range(ticker: str, interval: str = "1d") -> Optional[tuple]:
    """
    Get the date range covered by cached data.
    
    Args:
        ticker (str): Stock symbol
        interval (str): Data interval ('1d', '1h', '30m', etc.)
        
    Returns:
        Optional[tuple]: Tuple of (start_date, end_date) or None if no cache
    """
    with ErrorContext("getting cache date range", ticker=ticker, interval=interval):
        validate_ticker(ticker)
        
        cached_df = load_cached_data(ticker, interval)
        
        if cached_df is None or cached_df.empty:
            return None
        
        return (cached_df.index[0], cached_df.index[-1])

def cache_covers_date_range(
    ticker: str,
    start_date: datetime,
    end_date: datetime,
    interval: str = "1d"
) -> bool:
    """
    Check if cache fully covers the requested date range.
    
    Args:
        ticker (str): Stock symbol
        start_date (datetime): Start date
        end_date (datetime): End date
        interval (str): Data interval
        
    Returns:
        bool: True if cache has all data for the range
    """
    with ErrorContext("checking cache coverage", ticker=ticker, start_date=start_date, end_date=end_date, interval=interval):
        validate_ticker(ticker)
        
        cache_range = get_cache_date_range(ticker, interval)
        
        if cache_range is None:
            return False
        
        cache_start, cache_end = cache_range
        
        # Ensure dates are timezone-naive for comparison
        start_date = normalize_datetime(start_date)
        end_date = normalize_datetime(end_date)
        cache_start = normalize_datetime(cache_start)
        cache_end = normalize_datetime(cache_end)
        
        # Check if cache covers the requested range
        return cache_start <= start_date and cache_end >= end_date

def read_ticker_file(filepath: str) -> List[str]:
    """
    Read ticker symbols from a text file (one ticker per line).
    
    Args:
        filepath (str): Path to the file containing ticker symbols
        
    Returns:
        List[str]: List of ticker symbols
    """
    with ErrorContext("reading ticker file", filepath=filepath):
        validate_file_path(filepath, check_exists=True, check_readable=True)
        tickers = []
        
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    ticker = line.strip().upper()
                    if ticker and not ticker.startswith('#'):  # Skip empty lines and comments
                        validate_ticker(ticker)
                        tickers.append(ticker)
            
            logger.info(f"Read {len(tickers)} tickers from {filepath}")
            return tickers
            
        except FileNotFoundError:
            raise FileOperationError(f"File '{filepath}' not found")
        except Exception as e:
            raise FileOperationError(f"Error reading file '{filepath}': {str(e)}")
