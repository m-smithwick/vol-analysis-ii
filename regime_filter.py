"""
Market and Sector Regime Filter

Prevents entry signals when broad market or sector is in distribution.
From upgrade_spec.md Item #6 - Enhanced with specific MA thresholds from tweaks.txt.

Rules:
- SPY close > SPY 200-day MA (market regime)
- Sector ETF close > 50-day MA (sector regime)
- Both must be true to allow entry signals

Author: Volume Analysis System
Last Updated: 2025-11-05
"""

import pandas as pd
import yfinance as yf
import numpy as np
from typing import Dict, Optional
import logging
import csv
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

# PERFORMANCE OPTIMIZATION: Global session-level cache for regime data
# This cache persists across all tickers in a batch backtest session,
# dramatically reducing redundant Yahoo Finance API calls
_SECTOR_REGIME_CACHE = {}  # Format: {date_str: {xlk_regime_ok: bool, xlf_regime_ok: bool, ...}}
_MARKET_REGIME_CACHE = {}  # Format: {date_str: {market_regime_ok: bool, spy_close: float, ...}}

# Valid sector ETF symbols for validation
VALID_SECTOR_ETFS = {'XLK', 'XLF', 'XLV', 'XLE', 'XLY', 'XLP', 'XLI', 'XLU', 'XLRE', 'XLB', 'XLC', 'SPY'}


def load_sector_mappings(filepath: str = 'ticker_lists/sector_mappings.csv') -> Dict[str, str]:
    """
    Load sector ETF mappings from CSV configuration file.
    
    CSV Format:
        ticker,sector_etf,sector_name
        AAPL,XLK,Technology
        JPM,XLF,Financials
        ...
    
    Args:
        filepath: Path to sector mappings CSV file
        
    Returns:
        Dictionary mapping ticker symbols to sector ETF symbols
        Empty dict if file not found or error occurs
    """
    mappings = {}
    
    try:
        csv_path = Path(filepath)
        if not csv_path.exists():
            logger.warning(f"Sector mappings file not found: {filepath}")
            logger.warning("Using SPY as default for all unmapped tickers")
            return {}
        
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (after header)
                try:
                    ticker = row['ticker'].strip().upper()
                    sector_etf = row['sector_etf'].strip().upper()
                    
                    # Validate sector ETF
                    if sector_etf not in VALID_SECTOR_ETFS:
                        logger.warning(
                            f"Row {row_num}: Invalid sector ETF '{sector_etf}' for {ticker}. "
                            f"Must be one of: {', '.join(sorted(VALID_SECTOR_ETFS))}"
                        )
                        continue
                    
                    mappings[ticker] = sector_etf
                    
                except KeyError as e:
                    logger.error(f"Row {row_num}: Missing required column {e}")
                    continue
                except Exception as e:
                    logger.error(f"Row {row_num}: Error parsing row - {e}")
                    continue
        
        logger.info(f"Loaded {len(mappings)} sector mappings from {filepath}")
        
    except FileNotFoundError:
        logger.warning(f"Sector mappings file not found: {filepath}")
        logger.warning("Using SPY as default for all unmapped tickers")
    except Exception as e:
        logger.error(f"Error loading sector mappings from {filepath}: {e}")
        logger.warning("Using SPY as default for all unmapped tickers")
    
    return mappings


# Load sector mappings at module initialization
# Configuration file: ticker_lists/sector_mappings.csv
# Users can add/modify mappings without touching code
SECTOR_ETFS = load_sector_mappings()


def get_sector_etf(ticker: str) -> str:
    """
    Get the appropriate sector ETF for a ticker.
    
    Args:
        ticker: Stock symbol
        
    Returns:
        Sector ETF symbol (defaults to SPY if unknown)
    """
    return SECTOR_ETFS.get(ticker.upper(), 'SPY')


def load_benchmark_data(ticker: str, 
                       period: Optional[str] = '12mo',
                       start_date: Optional[pd.Timestamp] = None,
                       end_date: Optional[pd.Timestamp] = None,
                       cache_only: bool = True) -> Optional[pd.DataFrame]:
    """
    Load benchmark data (SPY or sector ETF) from cache via data_manager.
    
    Uses cached data to avoid Yahoo Finance API rate limits and weekend failures.
    
    Args:
        ticker: Benchmark symbol
        period: Data period (e.g., '12mo', '6mo') - ignored if start_date provided
        start_date: Explicit start date (overrides period)
        end_date: Optional end date for historical analysis
        cache_only: If True, only use cached data (default: True)
        
    Returns:
        DataFrame with OHLCV data, or None if fetch fails
    """
    try:
        # Import here to avoid circular dependency
        from data_manager import get_smart_data
        
        # Determine period to use
        if start_date is not None and end_date is not None:
            # Calculate period from date range
            days_diff = (end_date - start_date).days
            months = int(days_diff / 30)
            
            # Map to standard periods
            if months <= 1:
                fetch_period = '1mo'
            elif months <= 3:
                fetch_period = '3mo'
            elif months <= 6:
                fetch_period = '6mo'
            elif months <= 12:
                fetch_period = '12mo'
            elif months <= 24:
                fetch_period = '24mo'
            else:
                fetch_period = '60mo'  # 5 years max
        elif end_date is not None:
            # Use default period (usually need at least 12mo for 200-day MA)
            fetch_period = '12mo'
        else:
            # Use provided period
            fetch_period = period if period else '12mo'
        
        # Get data from cache via data_manager
        df = get_smart_data(
            ticker=ticker,
            period=fetch_period,
            interval='1d',
            force_refresh=False,
            cache_only=cache_only,
            data_source='yfinance'  # Uses yfinance cache format
        )
        
        # Filter to date range if specified
        if start_date is not None or end_date is not None:
            if start_date is not None:
                df = df[df.index >= start_date]
            if end_date is not None:
                df = df[df.index <= end_date]
        
        if df.empty:
            logger.warning(f"No data returned for {ticker}")
            return None
            
        return df
        
    except Exception as e:
        logger.error(f"Failed to fetch {ticker} data: {e}")
        return None


def calculate_historical_regime_series(ticker: str, df: pd.DataFrame) -> tuple:
    """
    Calculate historical regime status for each bar in DataFrame.
    
    This function eliminates lookahead bias by checking regime status 
    for each date in the backtest period, not just current regime.
    
    Args:
        ticker: Stock symbol (determines sector ETF)
        df: DataFrame with DatetimeIndex
        
    Returns:
        Tuple of (market_regime_ok, sector_regime_ok, overall_regime_ok)
        Each is a boolean Series aligned with df.index
    """
    try:
        # Get date range from DataFrame with buffer for MA calculations
        start_date = df.index.min() - pd.DateOffset(months=12)  # Extra buffer for 200-day MA
        end_date = df.index.max()
        
        logger.info(f"Fetching historical regime data for {ticker} from {start_date.date()} to {end_date.date()}")
        
        # Fetch SPY historical data
        spy_data = load_benchmark_data('SPY', period=None, 
                                       start_date=start_date, 
                                       end_date=end_date)
        
        if spy_data is None or len(spy_data) < 200:
            logger.warning(f"Insufficient SPY data for historical regime calculation")
            # Return all False (conservative - no signals allowed)
            return (
                pd.Series(False, index=df.index),
                pd.Series(False, index=df.index),
                pd.Series(False, index=df.index)
            )
        
        # Fetch sector ETF historical data
        sector_etf = get_sector_etf(ticker)
        sector_data = load_benchmark_data(sector_etf, period=None,
                                         start_date=start_date,
                                         end_date=end_date)
        
        if sector_data is None or len(sector_data) < 50:
            logger.warning(f"Insufficient {sector_etf} data for historical regime calculation")
            # Return all False (conservative)
            return (
                pd.Series(False, index=df.index),
                pd.Series(False, index=df.index),
                pd.Series(False, index=df.index)
            )
        
        # Calculate SPY 200-day MA
        spy_data['MA200'] = spy_data['Close'].rolling(200, min_periods=200).mean()
        spy_data['Market_Regime_OK'] = spy_data['Close'] > spy_data['MA200']
        
        # Calculate Sector 50-day MA
        sector_data['MA50'] = sector_data['Close'].rolling(50, min_periods=50).mean()
        sector_data['Sector_Regime_OK'] = sector_data['Close'] > sector_data['MA50']
        
        # Normalize timezones - convert all to timezone-naive for comparison
        if spy_data.index.tz is not None:
            spy_data.index = spy_data.index.tz_localize(None)
        if sector_data.index.tz is not None:
            sector_data.index = sector_data.index.tz_localize(None)
        
        # Also normalize the target DataFrame index
        df_index_normalized = df.index
        if df_index_normalized.tz is not None:
            df_index_normalized = df_index_normalized.tz_localize(None)
        
        # Remove any duplicate dates from df_index_normalized before reindexing
        df_index_normalized_unique = df_index_normalized[~df_index_normalized.duplicated(keep='first')]
        
        # Align with DataFrame dates (handles weekends/holidays)
        # Convert to bool BEFORE reindex to avoid pandas downcasting warning
        market_regime_aligned = spy_data['Market_Regime_OK'].astype(bool).reindex(
            df_index_normalized_unique, 
            method='ffill',  # Forward-fill for non-trading days
            fill_value=False  # Conservative: missing data = regime FAIL
        )
        
        # If we had duplicates, expand back to match original index
        if len(df_index_normalized_unique) != len(df_index_normalized):
            # Create a mapping from unique dates back to all dates
            market_regime = pd.Series(index=df_index_normalized, dtype=bool)
            for date in df_index_normalized:
                market_regime.loc[date] = market_regime_aligned.get(date, False)
        else:
            market_regime = market_regime_aligned
        
        # Restore original index (with timezone if it had one)
        market_regime.index = df.index
        
        # Same process for sector regime
        # Convert to bool BEFORE reindex to avoid pandas downcasting warning
        sector_regime_aligned = sector_data['Sector_Regime_OK'].astype(bool).reindex(
            df_index_normalized_unique,
            method='ffill',
            fill_value=False
        )
        
        if len(df_index_normalized_unique) != len(df_index_normalized):
            sector_regime = pd.Series(index=df_index_normalized, dtype=bool)
            for date in df_index_normalized:
                sector_regime.loc[date] = sector_regime_aligned.get(date, False)
        else:
            sector_regime = sector_regime_aligned
            
        # Restore original index
        sector_regime.index = df.index
        
        # Overall regime = both must be True
        overall_regime = market_regime & sector_regime
        
        # Log summary
        market_pass = market_regime.sum()
        sector_pass = sector_regime.sum()
        overall_pass = overall_regime.sum()
        total_days = len(df)
        
        logger.info(f"Historical regime for {ticker}:")
        logger.info(f"  Market (SPY): {market_pass}/{total_days} days PASS ({market_pass/total_days*100:.1f}%)")
        logger.info(f"  Sector ({sector_etf}): {sector_pass}/{total_days} days PASS ({sector_pass/total_days*100:.1f}%)")
        logger.info(f"  Overall: {overall_pass}/{total_days} days PASS ({overall_pass/total_days*100:.1f}%)")
        
        return market_regime, sector_regime, overall_regime
        
    except Exception as e:
        logger.error(f"Failed to calculate historical regime series for {ticker}: {e}")
        # Return all False on error (conservative)
        return (
            pd.Series(False, index=df.index),
            pd.Series(False, index=df.index),
            pd.Series(False, index=df.index)
        )


def check_market_regime(date: Optional[pd.Timestamp] = None) -> Dict:
    """
    Check if SPY is above its 200-day moving average.
    
    Uses global cache to avoid redundant API calls across tickers.
    
    Args:
        date: Optional date for historical regime check (None = current)
        
    Returns:
        Dict with regime status and details
    """
    # Check cache first (use current date if none specified)
    cache_date = date if date is not None else pd.Timestamp.now()
    date_key = cache_date.strftime('%Y-%m-%d')
    
    if date_key in _MARKET_REGIME_CACHE:
        return _MARKET_REGIME_CACHE[date_key]
    
    # Cache miss - fetch data
    spy_data = load_benchmark_data('SPY', period='12mo', end_date=date)
    
    if spy_data is None or len(spy_data) < 200:
        logger.warning("Insufficient SPY data for regime check")
        return {
            'market_regime_ok': False,
            'reason': 'Insufficient data',
            'spy_close': None,
            'spy_200ma': None
        }
    
    # Calculate 200-day MA
    spy_data['MA200'] = spy_data['Close'].rolling(200).mean()
    
    # Get most recent valid data point
    latest = spy_data.dropna(subset=['MA200']).iloc[-1]
    
    spy_close = latest['Close']
    spy_200ma = latest['MA200']
    regime_ok = spy_close > spy_200ma
    
    result = {
        'market_regime_ok': regime_ok,
        'spy_close': spy_close,
        'spy_200ma': spy_200ma,
        'pct_above_ma': ((spy_close / spy_200ma - 1) * 100) if spy_200ma > 0 else 0,
        'date': latest.name
    }
    
    # Cache the result
    _MARKET_REGIME_CACHE[date_key] = result
    
    return result


def check_sector_regime(ticker: str, date: Optional[pd.Timestamp] = None) -> Dict:
    """
    Check if sector ETF is above its 50-day moving average.
    
    Args:
        ticker: Stock symbol to determine sector
        date: Optional date for historical regime check (None = current)
        
    Returns:
        Dict with regime status and details
    """
    sector_etf = get_sector_etf(ticker)
    sector_data = load_benchmark_data(sector_etf, period='6mo', end_date=date)
    
    if sector_data is None or len(sector_data) < 50:
        logger.warning(f"Insufficient {sector_etf} data for regime check")
        return {
            'sector_regime_ok': False,
            'reason': 'Insufficient data',
            'sector_etf': sector_etf,
            'sector_close': None,
            'sector_50ma': None
        }
    
    # Calculate 50-day MA
    sector_data['MA50'] = sector_data['Close'].rolling(50).mean()
    
    # Get most recent valid data point
    latest = sector_data.dropna(subset=['MA50']).iloc[-1]
    
    sector_close = latest['Close']
    sector_50ma = latest['MA50']
    regime_ok = sector_close > sector_50ma
    
    return {
        'sector_regime_ok': regime_ok,
        'sector_etf': sector_etf,
        'sector_close': sector_close,
        'sector_50ma': sector_50ma,
        'pct_above_ma': ((sector_close / sector_50ma - 1) * 100) if sector_50ma > 0 else 0,
        'date': latest.name
    }


def _safe_format(value, fmt='.2f', default='N/A'):
    """
    Safely format numeric values, handling None gracefully.
    
    Args:
        value: Value to format (can be None)
        fmt: Format string (default: '.2f')
        default: Default string for None values (default: 'N/A')
        
    Returns:
        Formatted string
    """
    if value is None:
        return default
    try:
        return f"{value:{fmt}}"
    except (ValueError, TypeError):
        return default


def get_all_sector_regimes(date: Optional[pd.Timestamp] = None) -> Dict:
    """
    Get regime status for ALL sector ETFs.
    
    Returns the regime status (above/below 50-day MA) for all 11 sector ETFs
    to provide complete market landscape context.
    
    Uses global cache to avoid redundant API calls across tickers in batch runs.
    
    Args:
        date: Optional date for historical regime check (None = current)
        
    Returns:
        Dict with regime status for each sector ETF
    """
    # Check cache first
    cache_date = date if date is not None else pd.Timestamp.now()
    date_key = cache_date.strftime('%Y-%m-%d')
    
    if date_key in _SECTOR_REGIME_CACHE:
        logger.debug(f"✓ Sector regime cache HIT for {date_key}")
        return _SECTOR_REGIME_CACHE[date_key]
    
    # Cache miss - fetch all sector data
    logger.info(f"⚠ Sector regime cache MISS for {date_key} - fetching 11 sector ETFs...")
    # All 11 sector ETFs
    sector_etfs = {
        'XLK': 'Technology',
        'XLF': 'Financials', 
        'XLV': 'Healthcare',
        'XLE': 'Energy',
        'XLY': 'Consumer Discretionary',
        'XLP': 'Consumer Staples',
        'XLI': 'Industrials',
        'XLU': 'Utilities',
        'XLRE': 'Real Estate',
        'XLB': 'Materials',
        'XLC': 'Communication Services'
    }
    
    result = {}
    
    for etf_symbol, sector_name in sector_etfs.items():
        etf_data = load_benchmark_data(etf_symbol, period='6mo', end_date=date)
        
        if etf_data is None or len(etf_data) < 50:
            # Insufficient data - mark as False (conservative)
            result[f'{etf_symbol.lower()}_regime_ok'] = False
            continue
        
        # Calculate 50-day MA
        etf_data['MA50'] = etf_data['Close'].rolling(50).mean()
        latest = etf_data.dropna(subset=['MA50']).iloc[-1]
        
        # Check if above 50-day MA
        regime_ok = latest['Close'] > latest['MA50']
        result[f'{etf_symbol.lower()}_regime_ok'] = regime_ok
    
    # Cache the complete result
    _SECTOR_REGIME_CACHE[date_key] = result
    logger.info(f"✓ Cached sector regimes for {date_key} (cache size: {len(_SECTOR_REGIME_CACHE)})")
    
    return result


def get_regime_status(ticker: str, date: Optional[pd.Timestamp] = None) -> Dict:
    """
    Get complete regime status for a ticker.
    
    Checks both market (SPY > 200DMA) and sector (ETF > 50DMA) conditions.
    Entry signals only allowed when BOTH conditions are met.
    
    PERFORMANCE OPTIMIZED: Gets all sectors once, extracts stock's specific sector.
    
    Args:
        ticker: Stock symbol
        date: Optional date for historical regime check (None = current)
        
    Returns:
        Dict with complete regime analysis including all sector ETF regimes
    """
    # Get market regime (cached)
    market = check_market_regime(date)
    
    # Get ALL sector regimes at once (cached globally)
    all_sectors = get_all_sector_regimes(date)
    
    # Extract this ticker's specific sector from the all-sectors result
    sector_etf = get_sector_etf(ticker)
    sector_key = f'{sector_etf.lower()}_regime_ok'
    sector_regime_ok = all_sectors.get(sector_key, False)
    
    overall_ok = market['market_regime_ok'] and sector_regime_ok
    
    result = {
        'ticker': ticker,
        'overall_regime_ok': overall_ok,
        'market_regime_ok': market['market_regime_ok'],
        'sector_regime_ok': sector_regime_ok,
        'spy_close': market.get('spy_close'),
        'spy_200ma': market.get('spy_200ma'),
        'spy_pct_above': market.get('pct_above_ma'),
        'sector_etf': sector_etf,
        'sector_close': None,  # Not individually fetched anymore
        'sector_50ma': None,   # Not individually fetched anymore
        'sector_pct_above': None,  # Not individually fetched anymore
        'check_date': date if date else pd.Timestamp.now()
    }
    
    # Add all sector ETF regime flags (already fetched above)
    result.update(all_sectors)
    
    # Add failure reasons if regime not ok
    if not overall_ok:
        reasons = []
        if not market['market_regime_ok']:
            spy_close_str = _safe_format(market.get('spy_close'))
            spy_200ma_str = _safe_format(market.get('spy_200ma'))
            reasons.append(f"SPY below 200DMA ({spy_close_str} < {spy_200ma_str})")
        if not sector_regime_ok:
            reasons.append(f"{sector_etf} below 50DMA")
        result['failure_reasons'] = reasons
    
    return result


def apply_regime_filter(df: pd.DataFrame, ticker: str, verbose: bool = False) -> pd.DataFrame:
    """
    Apply regime filter to signal DataFrame.
    
    ⚠️ DEPRECATED: This function uses current regime for all historical data.
    Use calculate_historical_regime_series() instead for backtesting.
    
    This function is kept for backward compatibility and live trading where 
    current regime is appropriate, but should NOT be used for historical backtesting
    as it creates lookahead bias.
    
    Creates regime status columns and filters entry signals when regime is not ok.
    Original signals preserved in *_raw columns for analysis.
    
    Args:
        df: DataFrame with signals
        ticker: Stock symbol
        verbose: Print regime status details
        
    Returns:
        DataFrame with regime-filtered signals
    """
    import warnings
    warnings.warn(
        "apply_regime_filter() uses current regime for all dates. "
        "For backtesting, use calculate_historical_regime_series() instead to avoid lookahead bias.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Get regime status (uses most recent data)
    regime = get_regime_status(ticker)
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"REGIME FILTER - {ticker}")
        print(f"{'='*60}")
        print(f"Market (SPY): {'✅ PASS' if regime['market_regime_ok'] else '❌ FAIL'}")
        if regime.get('spy_close') is not None and regime.get('spy_200ma') is not None:
            spy_close_str = _safe_format(regime['spy_close'])
            spy_200ma_str = _safe_format(regime['spy_200ma'])
            spy_pct_str = _safe_format(regime.get('spy_pct_above', 0), '+.2f', 'N/A')
            print(f"  SPY: ${spy_close_str} vs 200DMA: ${spy_200ma_str} ({spy_pct_str}%)")
        else:
            print(f"  SPY: Data unavailable (network connectivity issue)")
        
        print(f"\nSector ({regime.get('sector_etf', 'N/A')}): {'✅ PASS' if regime['sector_regime_ok'] else '❌ FAIL'}")
        if regime.get('sector_close') is not None and regime.get('sector_50ma') is not None:
            sector_close_str = _safe_format(regime['sector_close'])
            sector_50ma_str = _safe_format(regime['sector_50ma'])
            sector_pct_str = _safe_format(regime.get('sector_pct_above', 0), '+.2f', 'N/A')
            print(f"  {regime.get('sector_etf', 'N/A')}: ${sector_close_str} vs 50DMA: ${sector_50ma_str} ({sector_pct_str}%)")
        else:
            print(f"  {regime.get('sector_etf', 'N/A')}: Data unavailable (network connectivity issue)")
        
        print(f"\nOVERALL: {'✅ SIGNALS ALLOWED' if regime['overall_regime_ok'] else '❌ SIGNALS BLOCKED'}")
        
        if not regime['overall_regime_ok'] and 'failure_reasons' in regime:
            print("\nFailure Reasons:")
            for reason in regime['failure_reasons']:
                print(f"  • {reason}")
        print(f"{'='*60}\n")
    
    # Add regime status columns to DataFrame
    df['Market_Regime_OK'] = regime['market_regime_ok']
    df['Sector_Regime_OK'] = regime['sector_regime_ok']
    df['Overall_Regime_OK'] = regime['overall_regime_ok']
    
    # Identify entry signal columns
    entry_signals = [
        col for col in df.columns
        if any(x in col for x in ['Buy', 'Accumulation', 'Breakout', 'Confluence'])
        and 'Score' not in col  # Skip numeric score columns (e.g., Accumulation_Score)
    ]
    
    # Preserve raw signals and apply filter
    for signal_col in entry_signals:
        if signal_col.endswith('_raw') or signal_col.endswith('_display'):
            continue  # Skip already processed columns
            
        # Create raw signal column
        raw_col = f"{signal_col}_raw"
        if raw_col not in df.columns:
            df[raw_col] = df[signal_col].copy()
        
        # Apply regime filter to entry signals
        signal_bool = df[raw_col].fillna(False).astype(bool)
        filtered = np.logical_and(signal_bool.to_numpy(dtype=bool), bool(regime['overall_regime_ok']))
        df[signal_col] = pd.Series(filtered, index=df.index)
    
    return df


def add_all_sector_regime_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all 11 sector ETF regime columns to DataFrame for historical analysis.
    
    This function is optimized for historical bar-by-bar regime analysis.
    It loads each sector ETF ONCE for the full date range and calculates
    regime status for all dates, avoiding the cache miss issues in get_all_sector_regimes().
    
    Args:
        df: DataFrame with DatetimeIndex
        
    Returns:
        DataFrame with added sector regime columns:
        - xlk_regime_ok through xlc_regime_ok: All 11 sector ETF regimes
    """
    logger.info(f"  📊 Computing historical sector regimes for {len(df)} trading days...")
    
    # Get date range from DataFrame with buffer for MA calculations  
    start_date = df.index.min() - pd.DateOffset(months=3)  # Buffer for 50-day MA
    end_date = df.index.max()
    
    # All 11 sector ETFs
    sector_etfs = ['XLK', 'XLF', 'XLV', 'XLE', 'XLY', 'XLP', 'XLI', 'XLU', 'XLRE', 'XLB', 'XLC']
    
    for etf_symbol in sector_etfs:
        col_name = f'{etf_symbol.lower()}_regime_ok'
        
        try:
            # Load full historical data for this ETF
            etf_data = load_benchmark_data(etf_symbol, period=None, 
                                         start_date=start_date, end_date=end_date)
            
            if etf_data is not None and len(etf_data) >= 50:
                # Calculate 50-day MA
                etf_data['MA50'] = etf_data['Close'].rolling(50, min_periods=50).mean()
                etf_data[col_name] = etf_data['Close'] > etf_data['MA50']
                
                # Normalize timezone and align with df
                if etf_data.index.tz is not None:
                    etf_data.index = etf_data.index.tz_localize(None)
                df_index_norm = df.index.tz_localize(None) if df.index.tz is not None else df.index
                
                # Remove duplicates from df_index_norm to avoid reindex issues
                df_index_norm_unique = df_index_norm[~df_index_norm.duplicated(keep='first')]
                
                # Align with DataFrame dates - convert to bool BEFORE reindex to avoid pandas downcasting warning
                regime_aligned = etf_data[col_name].astype(bool).reindex(df_index_norm_unique, method='ffill', fill_value=False)
                
                # Handle duplicates if they existed
                if len(df_index_norm_unique) != len(df_index_norm):
                    regime_series = pd.Series(index=df_index_norm, dtype=bool)
                    for date in df_index_norm:
                        regime_series.loc[date] = regime_aligned.get(date, False)
                else:
                    regime_series = regime_aligned
                
                # Restore original index
                regime_series.index = df.index
                df[col_name] = regime_series
                
                logger.debug(f"    ✓ {etf_symbol}: {regime_series.sum()}/{len(regime_series)} days PASS")
            else:
                # Insufficient data - mark all as False (conservative)
                df[col_name] = False
                logger.warning(f"    ❌ {etf_symbol}: Insufficient data, marking all regime checks as FAIL")
                
        except Exception as e:
            # Error loading data - mark all as False (conservative)
            df[col_name] = False
            logger.error(f"    ❌ {etf_symbol}: Error loading data ({e}), marking all regime checks as FAIL")
    
    logger.info(f"  ✓ All sector regime columns added")
    return df


def add_regime_columns_to_df(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """
    Pre-compute and add regime status columns to DataFrame.
    
    This function fetches regime data ONCE for the entire date range and adds
    boolean columns to the DataFrame, eliminating API calls during backtest loop.
    
    PERFORMANCE CRITICAL: Call this BEFORE starting backtest loop!
    OPTIMIZED: Fetches each ETF once with full date range, not date-by-date.
    
    Args:
        df: DataFrame with DatetimeIndex
        ticker: Stock symbol (determines primary sector)
        
    Returns:
        DataFrame with added regime columns:
        - spy_regime_ok: SPY > 200-day MA
        - xlk_regime_ok through xlc_regime_ok: Sector ETF regimes
        - sector_etf: Stock's assigned sector ETF
        - primary_sector_regime_ok: That sector's regime status
    """
    print(f"  📊 Pre-computing regime data for {ticker}...")
    
    # Get date range from DataFrame with buffer for MA calculations
    start_date = df.index.min() - pd.DateOffset(months=7)  # Buffer for 200-day MA
    end_date = df.index.max()
    
    # Fetch SPY data ONCE for entire range
    spy_data = load_benchmark_data('SPY', period=None, start_date=start_date, end_date=end_date)
    
    if spy_data is not None and len(spy_data) >= 200:
        # Calculate 200-day MA
        spy_data['MA200'] = spy_data['Close'].rolling(200, min_periods=200).mean()
        spy_data['spy_regime_ok'] = spy_data['Close'] > spy_data['MA200']
        
        # Normalize timezone and align with df
        if spy_data.index.tz is not None:
            spy_data.index = spy_data.index.tz_localize(None)
        df_index_norm = df.index.tz_localize(None) if df.index.tz is not None else df.index
        
        df['spy_regime_ok'] = spy_data['spy_regime_ok'].astype(bool).reindex(df_index_norm, method='ffill').fillna(False)
        df['spy_regime_ok'].index = df.index  # Restore original index
    else:
        df['spy_regime_ok'] = False
    
    # Fetch all 11 sector ETFs ONCE each for entire range
    sector_etfs = ['XLK', 'XLF', 'XLV', 'XLE', 'XLY', 'XLP', 'XLI', 'XLU', 'XLRE', 'XLB', 'XLC']
    
    for etf_symbol in sector_etfs:
        col_name = f'{etf_symbol.lower()}_regime_ok'
        
        etf_data = load_benchmark_data(etf_symbol, period=None, start_date=start_date, end_date=end_date)
        
        if etf_data is not None and len(etf_data) >= 50:
            # Calculate 50-day MA
            etf_data['MA50'] = etf_data['Close'].rolling(50, min_periods=50).mean()
            etf_data[col_name] = etf_data['Close'] > etf_data['MA50']
            
            # Normalize timezone and align
            if etf_data.index.tz is not None:
                etf_data.index = etf_data.index.tz_localize(None)
            df_index_norm = df.index.tz_localize(None) if df.index.tz is not None else df.index
            
            df[col_name] = etf_data[col_name].astype(bool).reindex(df_index_norm, method='ffill').fillna(False)
            df[col_name].index = df.index  # Restore original index
        else:
            df[col_name] = False
    
    # Add stock's primary sector for reference
    primary_sector = get_sector_etf(ticker)
    df['sector_etf'] = primary_sector
    df['primary_sector_regime_ok'] = df[f'{primary_sector.lower()}_regime_ok']
    
    print(f"  ✓ Regime columns added")
    
    return df


def create_regime_summary(ticker: str) -> str:
    """
    Create human-readable regime summary for reports.
    
    Args:
        ticker: Stock symbol
        
    Returns:
        Formatted regime summary string
    """
    regime = get_regime_status(ticker)
    
    summary = []
    summary.append(f"Regime Filter Status for {ticker}:")
    summary.append(f"  Overall: {'✅ PASS' if regime['overall_regime_ok'] else '❌ FAIL'}")
    
    if regime.get('spy_close') is not None and regime.get('spy_200ma') is not None:
        spy_status = '✅' if regime['market_regime_ok'] else '❌'
        spy_close_str = _safe_format(regime['spy_close'])
        spy_200ma_str = _safe_format(regime['spy_200ma'])
        summary.append(f"  Market (SPY): {spy_status} ${spy_close_str} vs 200DMA ${spy_200ma_str}")
    else:
        spy_status = '✅' if regime['market_regime_ok'] else '❌'
        summary.append(f"  Market (SPY): {spy_status} Data unavailable")
    
    if regime.get('sector_close') is not None and regime.get('sector_50ma') is not None:
        sector_status = '✅' if regime['sector_regime_ok'] else '❌'
        sector_close_str = _safe_format(regime['sector_close'])
        sector_50ma_str = _safe_format(regime['sector_50ma'])
        summary.append(f"  Sector ({regime.get('sector_etf', 'N/A')}): {sector_status} ${sector_close_str} vs 50DMA ${sector_50ma_str}")
    else:
        sector_status = '✅' if regime['sector_regime_ok'] else '❌'
        summary.append(f"  Sector ({regime.get('sector_etf', 'N/A')}): {sector_status} Data unavailable")
    
    if not regime['overall_regime_ok'] and 'failure_reasons' in regime:
        summary.append("  Failure Reasons:")
        for reason in regime['failure_reasons']:
            summary.append(f"    • {reason}")
    
    return '\n'.join(summary)


if __name__ == '__main__':
    # Test regime filter with sample tickers
    test_tickers = ['AAPL', 'JPM', 'XOM', 'TSLA']
    
    print("\n" + "="*80)
    print("REGIME FILTER TEST")
    print("="*80)
    
    for ticker in test_tickers:
        print(f"\n{create_regime_summary(ticker)}")
        print("-" * 80)
