"""
Data management module for stock data retrieval and caching.
"""

from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np
import os
import yfinance as yf
from datetime import datetime, timedelta

def get_cache_directory() -> str:
    """Get or create the data cache directory."""
    cache_dir = os.path.join(os.getcwd(), 'data_cache')
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
        print(f"📁 Created cache directory: {cache_dir}")
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
    cache_dir = get_cache_directory()
    return os.path.join(cache_dir, f"{ticker}_{interval}_data.csv")

def load_cached_data(ticker: str, interval: str = "1d") -> Optional[pd.DataFrame]:
    """
    Load cached data for a ticker if it exists and is valid.
    
    Args:
        ticker (str): Stock symbol
        interval (str): Data interval ('1d', '1h', '30m', etc.)
        
    Returns:
        Optional[pd.DataFrame]: DataFrame with cached data, or None if cache not valid
    """
    cache_file = get_cache_filepath(ticker, interval)
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        
        # Validate cached data
        if df.empty:
            print(f"⚠️  Empty cache file for {ticker} ({interval}) - will redownload")
            os.remove(cache_file)  # Remove invalid cache
            return None
        
        # Ensure index is timezone-naive for consistent handling
        if df.index.tzinfo is not None:
            df.index = df.index.tz_localize(None)
            
        print(f"📊 Loaded cached data for {ticker} ({interval}): {len(df)} periods ({df.index[0]} to {df.index[-1]})")
        return df
    except Exception as e:
        print(f"⚠️  Error loading cache for {ticker} ({interval}): {e}")
        # Remove corrupted cache file
        try:
            os.remove(cache_file)
            print(f"🗑️  Removed corrupted cache file for {ticker}")
        except:
            pass
        return None

def save_to_cache(ticker: str, df: pd.DataFrame, interval: str = "1d") -> None:
    """
    Save DataFrame to cache with interval support.
    
    Args:
        ticker (str): Stock symbol
        df (pd.DataFrame): Data to cache
        interval (str): Data interval ('1d', '1h', '30m', etc.)
    """
    cache_file = get_cache_filepath(ticker, interval)
    try:
        df.to_csv(cache_file)
        print(f"💾 Cached data for {ticker} ({interval}): {len(df)} periods saved to cache")
    except Exception as e:
        print(f"⚠️  Error saving cache for {ticker} ({interval}): {e}")

def append_to_cache(ticker: str, new_data: pd.DataFrame, interval: str = "1d") -> None:
    """
    Append new data to existing cache file.
    
    Args:
        ticker (str): Stock symbol
        new_data (pd.DataFrame): New data to append
        interval (str): Data interval ('1d', '1h', '30m', etc.)
    """
    cache_file = get_cache_filepath(ticker, interval)
    try:
        # Append new data to the CSV file
        new_data.to_csv(cache_file, mode='a', header=False)
        print(f"📈 Appended {len(new_data)} new periods to {ticker} ({interval}) cache")
    except Exception as e:
        print(f"⚠️  Error appending to cache for {ticker} ({interval}): {e}")

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

def get_smart_data(ticker: str, period: str, interval: str = "1d", force_refresh: bool = False) -> pd.DataFrame:
    """
    Smart data fetching with caching support.
    
    Args:
        ticker (str): Stock symbol
        period (str): Requested period (e.g., '6mo', '12mo')
        interval (str): Data interval ('1d', '1h', '30m', '15m', etc.)
        force_refresh (bool): If True, ignore cache and download fresh data
        
    Returns:
        pd.DataFrame: Stock data with OHLCV columns
        
    Raises:
        ValueError: If no valid data is available for the ticker
    """
    # Normalize the period first
    period = normalize_period(period)
    
    # Convert period to days for calculations (adjust for intraday data)
    if interval == "1d":
        period_days = {
            '1d': 1, '5d': 5, '1mo': 30, '3mo': 90, '6mo': 180, 
            '12mo': 365, '24mo': 730, '36mo': 1095, '60mo': 1825, '120mo': 3650, 
            'ytd': 365, 'max': 7300
        }
        requested_days = period_days.get(period, 365)
    else:
        # For intraday, Yahoo Finance has limitations on history
        # Typically only ~60 days for 1h, less for smaller intervals
        if interval == "1h":
            max_days = 60
        elif interval == "30m":
            max_days = 30
        elif interval == "15m":
            max_days = 10
        elif interval in ["5m", "1m"]:
            max_days = 5
        else:
            max_days = 30  # Default for unknown intraday intervals
        
        # Map period to days but cap at maximum available for interval
        period_days = {
            '1d': 1, '5d': 5, '1mo': 30, '3mo': 60, '6mo': 60, 
            '12mo': 60, '24mo': 60, '36mo': 60, '60mo': 60, 
            'ytd': min(datetime.now().timetuple().tm_yday, max_days), 
            'max': max_days
        }
        requested_days = min(period_days.get(period, 30), max_days)
    
    cutoff_date = datetime.now() - timedelta(days=requested_days)
    
    if force_refresh:
        print(f"🔄 Force refresh enabled - downloading fresh data for {ticker} ({interval})")
        df = yf.download(ticker, period=period, interval=interval, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        df.dropna(inplace=True)
        
        # Validate downloaded data
        if df.empty:
            raise ValueError(f"No data available for {ticker} (possibly delisted or invalid symbol)")
        
        save_to_cache(ticker, df, interval)
        return df
    
    # Try to load cached data
    cached_df = load_cached_data(ticker, interval)
    
    if cached_df is None:
        # No cache exists - download full period
        print(f"📥 No cache found for {ticker} ({interval}) - downloading {period} data from Yahoo Finance")
        df = yf.download(ticker, period=period, interval=interval, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        df.dropna(inplace=True)
        
        # Validate downloaded data
        if df.empty:
            raise ValueError(f"No data available for {ticker} (possibly delisted or invalid symbol)")
        
        save_to_cache(ticker, df, interval)
        return df
    
    # Check if cached data covers the requested period
    cache_start_date = cached_df.index[0]
    cache_end_date = cached_df.index[-1]
    
    # For intraday data, we need to be more careful about updates
    # Since Yahoo only provides limited history, we might need complete refreshes
    if interval != "1d":
        # Check if our cache is too old (more than 1 day old for intraday data)
        today = datetime.now().date()
        last_cached_date = cache_end_date.date()
        days_behind = (today - last_cached_date).days
        
        if days_behind > 1:
            # For intraday data more than a day old, simply refresh entirely
            print(f"🔄 Intraday cache outdated ({days_behind}d old) - downloading fresh data for {ticker} ({interval})")
            df = yf.download(ticker, period=period, interval=interval, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            df.dropna(inplace=True)
            
            if not df.empty:
                save_to_cache(ticker, df, interval)
                return df
            else:
                # If download fails, use cached data as fallback
                print(f"⚠️  Failed to download fresh data - using cached data as fallback")
                return cached_df
    
    # For daily data or current intraday data, handle incremental updates
    # Check if we need to download more recent data
    today = datetime.now().date()
    last_cached_date = cache_end_date.date()
    days_behind = (today - last_cached_date).days
    
    # For daily data, update if behind by 1+ days
    # For intraday, update if it's the same day (to get most recent bars)
    update_needed = (interval == "1d" and days_behind >= 1) or (interval != "1d" and today == last_cached_date)
    
    if not update_needed:
        # Cache is up to date
        print(f"✅ Cache is current for {ticker} ({interval}) - using cached data")
        # Filter cached data to requested period if needed
        filtered_df = cached_df[cached_df.index >= cutoff_date] if cutoff_date > cache_start_date else cached_df
        return filtered_df
    
    # Need to download recent data
    print(f"📥 Cache is {days_behind} days behind - downloading recent data for {ticker} ({interval})")
    
    try:
        # Try using period parameter instead of start/end dates to avoid timezone conflicts
        days_to_download = days_behind + 1  # +1 to include today
        period_param = f"{min(days_to_download, 60)}d"  # Cap at 60d for safety with intraday data
        print(f"Using period parameter: {period_param} instead of explicit dates to avoid timezone issues")
        
        new_data = yf.download(ticker, period=period_param, interval=interval, auto_adjust=True)
        
        # If nothing was returned or the download failed, try the old way as fallback
        if new_data.empty:
            print(f"Period-based download returned no data, trying date-based download as fallback")
            # Download from day after last cached date to today
            # Ensure we're using timezone-naive dates for Yahoo Finance API
            start_date = (cache_end_date + timedelta(days=1)).replace(tzinfo=None).strftime('%Y-%m-%d')
            new_data = yf.download(ticker, start=start_date, interval=interval, auto_adjust=True)
    except Exception as e:
        print(f"⚠️ Error downloading recent data: {str(e)}")
        print(f"Falling back to cached data")
        filtered_df = cached_df[cached_df.index >= cutoff_date] if cutoff_date > cache_start_date else cached_df
        return filtered_df
    
    if isinstance(new_data.columns, pd.MultiIndex):
        new_data.columns = new_data.columns.droplevel(1)
    new_data.dropna(inplace=True)
    
    if not new_data.empty:
        # Ensure both dataframes have timezone-naive index for consistent comparison
        if cached_df.index.tzinfo is not None:
            cached_df.index = cached_df.index.tz_localize(None)
        if new_data.index.tzinfo is not None:
            new_data.index = new_data.index.tz_localize(None)
            
        # Append new data to cache
        append_to_cache(ticker, new_data, interval)
        
        # Combine cached and new data
        combined_df = pd.concat([cached_df, new_data])
        combined_df = combined_df[~combined_df.index.duplicated(keep='last')]  # Remove any duplicates
        combined_df.sort_index(inplace=True)
        
        # Update the cache with the complete dataset
        save_to_cache(ticker, combined_df, interval)
        
        # Filter to requested period
        filtered_df = combined_df[combined_df.index >= cutoff_date] if cutoff_date > combined_df.index[0] else combined_df
        return filtered_df
    else:
        print(f"ℹ️  No new data available for {ticker}")
        filtered_df = cached_df[cached_df.index >= cutoff_date] if cutoff_date > cache_start_date else cached_df
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
    cache_dir = get_cache_directory()
    
    if ticker and interval:
        # Clear specific ticker and interval cache
        cache_file = get_cache_filepath(ticker, interval)
        if os.path.exists(cache_file):
            os.remove(cache_file)
            print(f"🗑️  Cleared cache for {ticker} ({interval})")
        else:
            print(f"ℹ️  No cache found for {ticker} ({interval})")
    
    elif ticker:
        # Clear all intervals for specific ticker
        files_removed = 0
        for file in os.listdir(cache_dir):
            if file.startswith(f"{ticker}_") and file.endswith("_data.csv"):
                os.remove(os.path.join(cache_dir, file))
                files_removed += 1
        
        if files_removed > 0:
            print(f"🗑️  Cleared {files_removed} cache files for {ticker}")
        else:
            print(f"ℹ️  No cache files found for {ticker}")
    
    else:
        # Clear entire cache directory
        if os.path.exists(cache_dir):
            import shutil
            shutil.rmtree(cache_dir)
            os.makedirs(cache_dir)
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

def read_ticker_file(filepath: str) -> List[str]:
    """
    Read ticker symbols from a text file (one ticker per line).
    
    Args:
        filepath (str): Path to the file containing ticker symbols
        
    Returns:
        List[str]: List of ticker symbols
    """
    tickers = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                ticker = line.strip().upper()
                if ticker and not ticker.startswith('#'):  # Skip empty lines and comments
                    tickers.append(ticker)
        return tickers
    except FileNotFoundError:
        print(f"❌ Error: File '{filepath}' not found.")
        raise
    except Exception as e:
        print(f"❌ Error reading file '{filepath}': {str(e)}")
        raise
