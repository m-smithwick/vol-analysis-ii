"""
Regime Data Cache Module

Provides centralized caching of market and sector regime data to eliminate
redundant API calls across multiple script invocations.

Cache Structure:
- Single Parquet file: sector_cache/regime_data.parquet
- Contains: SPY + 11 sector ETFs + GLD + SLV
- Columns: {ticker}_close, {ticker}_{ma}ma, {ticker}_regime_ok
- Incremental updates: Only fetches missing dates

Author: Volume Analysis System
Last Updated: 2025-12-08
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

# Cache file location
CACHE_DIR = Path('sector_cache')
CACHE_FILE = CACHE_DIR / 'regime_data.parquet'

# Instruments to cache
# SPY: Market regime (200-day MA)
# Sector ETFs: 11 standard sectors (50-day MA)
# Special tickers: GLD, SLV use themselves as regime (50-day MA)
MARKET_TICKER = 'SPY'
MARKET_MA_PERIOD = 200

SECTOR_ETFS = ['XLK', 'XLF', 'XLV', 'XLE', 'XLY', 'XLP', 'XLI', 'XLU', 'XLRE', 'XLB', 'XLC']
SECTOR_MA_PERIOD = 50

SPECIAL_TICKERS = ['GLD', 'SLV']
SPECIAL_MA_PERIOD = 50


def fetch_ticker_data(ticker: str, start_date: pd.Timestamp, end_date: pd.Timestamp) -> Optional[pd.DataFrame]:
    """
    Fetch historical data for a ticker using data_manager.
    
    Args:
        ticker: Symbol to fetch
        start_date: Start date
        end_date: End date
        
    Returns:
        DataFrame with OHLCV data, or None if fetch fails
    """
    try:
        from data_manager import get_smart_data
        
        # Calculate period from date range
        days_diff = (end_date - start_date).days
        months = int(days_diff / 30)
        
        # Map to standard periods (add buffer for MA calculations)
        if months <= 1:
            fetch_period = '3mo'  # Extra buffer
        elif months <= 3:
            fetch_period = '6mo'
        elif months <= 6:
            fetch_period = '12mo'
        elif months <= 12:
            fetch_period = '24mo'
        elif months <= 24:
            fetch_period = '36mo'
        else:
            fetch_period = '60mo'
        
        # Get data from cache via data_manager
        df = get_smart_data(
            ticker=ticker,
            period=fetch_period,
            interval='1d',
            force_refresh=False,
            cache_only=False,  # Allow network fetch for regime data
            data_source='yfinance'
        )
        
        if df is None or df.empty:
            logger.warning(f"No data returned for {ticker}")
            return None
        
        # Filter to requested date range
        df = df[(df.index >= start_date) & (df.index <= end_date)]
        
        return df
        
    except Exception as e:
        logger.error(f"Failed to fetch {ticker} data: {e}")
        return None


def calculate_regime_columns(df: pd.DataFrame, ticker: str, ma_period: int) -> pd.DataFrame:
    """
    Calculate regime columns (price, MA, regime_ok) for a ticker.
    
    Args:
        df: DataFrame with Close prices
        ticker: Ticker symbol (for column naming)
        ma_period: Moving average period
        
    Returns:
        DataFrame with regime columns
    """
    result = pd.DataFrame(index=df.index)
    
    ticker_lower = ticker.lower()
    
    # Price
    result[f'{ticker_lower}_close'] = df['Close']
    
    # Moving average
    ma_col = f'{ticker_lower}_{ma_period}ma'
    result[ma_col] = df['Close'].rolling(ma_period, min_periods=ma_period).mean()
    
    # Regime flag (close > MA) - ensure bool dtype
    regime_col = f'{ticker_lower}_regime_ok'
    result[regime_col] = (df['Close'] > result[ma_col]).astype(bool)
    
    return result


def build_regime_cache(start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
    """
    Build complete regime cache from scratch.
    
    Fetches and computes regime data for:
    - SPY (market regime, 200-day MA)
    - 11 sector ETFs (50-day MA each)
    - GLD, SLV (special tickers, 50-day MA)
    
    Args:
        start_date: Start date for historical data
        end_date: End date for historical data
        
    Returns:
        DataFrame with all regime data
    """
    logger.info(f"Building regime cache from {start_date.date()} to {end_date.date()}...")
    
    # Add buffer for MA calculations
    buffer_start = start_date - pd.DateOffset(months=12)
    
    all_regime_data = []
    
    # Fetch SPY (market regime)
    logger.info(f"  Fetching {MARKET_TICKER} (market regime)...")
    spy_data = fetch_ticker_data(MARKET_TICKER, buffer_start, end_date)
    
    if spy_data is not None and len(spy_data) >= MARKET_MA_PERIOD:
        spy_regime = calculate_regime_columns(spy_data, MARKET_TICKER, MARKET_MA_PERIOD)
        all_regime_data.append(spy_regime)
    else:
        logger.error(f"Failed to fetch {MARKET_TICKER} data - cache incomplete")
        return pd.DataFrame()
    
    # Fetch sector ETFs
    logger.info(f"  Fetching {len(SECTOR_ETFS)} sector ETFs...")
    for etf in SECTOR_ETFS:
        etf_data = fetch_ticker_data(etf, buffer_start, end_date)
        
        if etf_data is not None and len(etf_data) >= SECTOR_MA_PERIOD:
            etf_regime = calculate_regime_columns(etf_data, etf, SECTOR_MA_PERIOD)
            all_regime_data.append(etf_regime)
            logger.debug(f"    ✓ {etf}")
        else:
            logger.warning(f"    ✗ {etf} - insufficient data")
    
    # Fetch special tickers (GLD, SLV)
    logger.info(f"  Fetching {len(SPECIAL_TICKERS)} special tickers (GLD, SLV)...")
    for ticker in SPECIAL_TICKERS:
        ticker_data = fetch_ticker_data(ticker, buffer_start, end_date)
        
        if ticker_data is not None and len(ticker_data) >= SPECIAL_MA_PERIOD:
            ticker_regime = calculate_regime_columns(ticker_data, ticker, SPECIAL_MA_PERIOD)
            all_regime_data.append(ticker_regime)
            logger.debug(f"    ✓ {ticker}")
        else:
            logger.warning(f"    ✗ {ticker} - insufficient data")
    
    # Combine all regime data
    if not all_regime_data:
        logger.error("No regime data fetched - cache build failed")
        return pd.DataFrame()
    
    # Join all DataFrames on date index
    combined_df = all_regime_data[0]
    for regime_df in all_regime_data[1:]:
        combined_df = combined_df.join(regime_df, how='outer')
    
    # Remove buffer period, keep only requested range
    combined_df = combined_df[combined_df.index >= start_date]
    
    # Sort by date
    combined_df = combined_df.sort_index()
    
    logger.info(f"  ✅ Cache built: {len(combined_df)} trading days, {len(combined_df.columns)} columns")
    
    return combined_df


def update_regime_cache(cached_df: pd.DataFrame, end_date: pd.Timestamp) -> pd.DataFrame:
    """
    Update existing cache with missing dates.
    
    Args:
        cached_df: Existing cached DataFrame
        end_date: Target end date
        
    Returns:
        Updated DataFrame with new data appended
    """
    last_cached_date = cached_df.index.max()
    
    if end_date <= last_cached_date:
        # Cache is up to date
        logger.info(f"  Cache up to date (last date: {last_cached_date.date()})")
        return cached_df
    
    # Calculate missing date range
    missing_start = last_cached_date + pd.Timedelta(days=1)
    
    logger.info(f"  Updating cache from {missing_start.date()} to {end_date.date()}...")
    
    # Fetch missing data (add small buffer for MA recalculation)
    buffer_start = missing_start - pd.DateOffset(months=1)
    new_data = build_regime_cache(buffer_start, end_date)
    
    if new_data.empty:
        logger.warning("  Failed to fetch new data - returning existing cache")
        return cached_df
    
    # Filter new data to only dates after last cached date
    new_data = new_data[new_data.index > last_cached_date]
    
    if new_data.empty:
        logger.info("  No new trading days to add")
        return cached_df
    
    # Append new data
    updated_df = pd.concat([cached_df, new_data])
    updated_df = updated_df.sort_index()
    
    # Remove duplicates (keep last)
    updated_df = updated_df[~updated_df.index.duplicated(keep='last')]
    
    logger.info(f"  ✅ Added {len(new_data)} new trading days")
    
    return updated_df


def save_regime_cache(df: pd.DataFrame) -> bool:
    """
    Save regime cache to Parquet file.
    
    Args:
        df: DataFrame to save
        
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        # Ensure cache directory exists
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Save to Parquet
        df.to_parquet(CACHE_FILE)
        
        file_size_kb = CACHE_FILE.stat().st_size / 1024
        logger.info(f"  💾 Cache saved: {CACHE_FILE} ({file_size_kb:.1f} KB)")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to save cache: {e}")
        return False


def load_regime_cache() -> Optional[pd.DataFrame]:
    """
    Load regime cache from Parquet file.
    
    Returns:
        Cached DataFrame, or None if cache doesn't exist
    """
    if not CACHE_FILE.exists():
        logger.info("  No existing cache found")
        return None
    
    try:
        df = pd.read_parquet(CACHE_FILE)
        
        logger.info(f"  ✅ Loaded cache: {len(df)} trading days from {df.index.min().date()} to {df.index.max().date()}")
        
        return df
        
    except Exception as e:
        logger.error(f"Failed to load cache: {e}")
        return None


def get_regime_data(start_date: pd.Timestamp, end_date: pd.Timestamp, 
                   force_rebuild: bool = False) -> pd.DataFrame:
    """
    Get regime data for specified date range.
    
    Main entry point for regime data retrieval. Handles cache loading,
    updating, and building as needed.
    
    Args:
        start_date: Start date for data
        end_date: End date for data
        force_rebuild: If True, rebuild cache from scratch
        
    Returns:
        DataFrame with regime data for requested date range
    """
    if force_rebuild:
        logger.info("Force rebuild requested - building cache from scratch...")
        df = build_regime_cache(start_date, end_date)
        if not df.empty:
            save_regime_cache(df)
        return df
    
    # Try to load existing cache
    cached_df = load_regime_cache()
    
    if cached_df is None:
        # No cache exists - build from scratch
        logger.info("Building regime cache for the first time...")
        df = build_regime_cache(start_date, end_date)
        if not df.empty:
            save_regime_cache(df)
        return df
    
    # Cache exists - check if it covers requested range
    cache_start = cached_df.index.min()
    cache_end = cached_df.index.max()
    
    needs_update = False
    
    # Check if we need earlier data
    if start_date < cache_start:
        logger.info(f"Cache starts at {cache_start.date()}, but need data from {start_date.date()}")
        needs_update = True
    
    # Check if we need later data
    if end_date > cache_end:
        logger.info(f"Cache ends at {cache_end.date()}, but need data until {end_date.date()}")
        needs_update = True
    
    if needs_update:
        # Expand cache to cover full range
        new_start = min(start_date, cache_start)
        new_end = max(end_date, cache_end)
        
        if start_date < cache_start:
            # Need to prepend historical data - rebuild entire cache
            logger.info("Need historical data - rebuilding cache...")
            df = build_regime_cache(new_start, new_end)
        else:
            # Just need to append recent data - incremental update
            df = update_regime_cache(cached_df, new_end)
        
        if not df.empty:
            save_regime_cache(df)
        
        cached_df = df
    
    # Return data for requested range
    result = cached_df[(cached_df.index >= start_date) & (cached_df.index <= end_date)]
    
    return result


def get_ticker_regime_status(ticker: str, date: pd.Timestamp, regime_df: pd.DataFrame) -> Dict:
    """
    Extract regime status for a specific ticker and date from cached data.
    
    Args:
        ticker: Stock symbol (determines which sector/regime to check)
        date: Date to check regime status
        regime_df: Cached regime DataFrame
        
    Returns:
        Dict with regime status information
    """
    from regime_filter import get_sector_etf
    
    # Determine which regime to check
    sector_etf = get_sector_etf(ticker)
    
    # Normalize to cached column names (lowercase)
    sector_lower = sector_etf.lower()
    
    try:
        # Get regime status for this date
        if date not in regime_df.index:
            # Find nearest date (forward fill for non-trading days)
            valid_dates = regime_df.index[regime_df.index <= date]
            if len(valid_dates) == 0:
                logger.warning(f"No regime data available for {date.date()}")
                return {
                    'ticker': ticker,
                    'date': date,
                    'market_regime_ok': False,
                    'sector_regime_ok': False,
                    'overall_regime_ok': False,
                    'sector_etf': sector_etf
                }
            date = valid_dates[-1]  # Use most recent available date
        
        # Extract regime flags for this date
        market_ok = bool(regime_df.loc[date, 'spy_regime_ok'])
        sector_ok = bool(regime_df.loc[date, f'{sector_lower}_regime_ok'])
        
        return {
            'ticker': ticker,
            'date': date,
            'market_regime_ok': market_ok,
            'sector_regime_ok': sector_ok,
            'overall_regime_ok': market_ok and sector_ok,
            'sector_etf': sector_etf,
            'spy_close': regime_df.loc[date, 'spy_close'],
            'spy_200ma': regime_df.loc[date, 'spy_200ma'],
            f'{sector_lower}_close': regime_df.loc[date, f'{sector_lower}_close'],
            f'{sector_lower}_50ma': regime_df.loc[date, f'{sector_lower}_50ma']
        }
        
    except KeyError as e:
        logger.error(f"Missing regime column for {ticker}/{sector_etf}: {e}")
        return {
            'ticker': ticker,
            'date': date,
            'market_regime_ok': False,
            'sector_regime_ok': False,
            'overall_regime_ok': False,
            'sector_etf': sector_etf
        }


if __name__ == '__main__':
    # Test cache functionality
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    print("Testing Regime Cache Module")
    print("=" * 60)
    
    # Test date range
    end_date = pd.Timestamp.now()
    start_date = end_date - pd.DateOffset(months=12)
    
    print(f"Fetching regime data for {start_date.date()} to {end_date.date()}")
    print()
    
    # Get regime data (will build cache if needed)
    regime_df = get_regime_data(start_date, end_date)
    
    if not regime_df.empty:
        print()
        print("Cache Statistics:")
        print(f"  Date Range: {regime_df.index.min().date()} to {regime_df.index.max().date()}")
        print(f"  Trading Days: {len(regime_df)}")
        print(f"  Columns: {len(regime_df.columns)}")
        print()
        print("Sample Data (last 5 days):")
        print(regime_df.tail())
        print()
        
        # Test ticker regime lookup
        test_ticker = 'AAPL'
        test_date = regime_df.index[-1]
        regime_status = get_ticker_regime_status(test_ticker, test_date, regime_df)
        
        print(f"Regime Status for {test_ticker} on {test_date.date()}:")
        print(f"  Sector ETF: {regime_status['sector_etf']}")
        print(f"  Market Regime OK: {regime_status['market_regime_ok']}")
        print(f"  Sector Regime OK: {regime_status['sector_regime_ok']}")
        print(f"  Overall OK: {regime_status['overall_regime_ok']}")
    else:
        print("❌ Failed to build cache")
        sys.exit(1)
