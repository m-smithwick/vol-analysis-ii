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

# Configure logging
logger = logging.getLogger(__name__)

# PERFORMANCE OPTIMIZATION: Global session-level cache for regime data
# This cache persists across all tickers in a batch backtest session,
# dramatically reducing redundant Yahoo Finance API calls
_SECTOR_REGIME_CACHE = {}  # Format: {date_str: {xlk_regime_ok: bool, xlf_regime_ok: bool, ...}}
_MARKET_REGIME_CACHE = {}  # Format: {date_str: {market_regime_ok: bool, spy_close: float, ...}}

# Sector ETF mapping
SECTOR_ETFS = {
    # Technology
    'AAPL': 'XLK', 'MSFT': 'XLK', 'GOOGL': 'XLK', 'GOOG': 'XLK',
    'NVDA': 'XLK', 'META': 'XLK', 'TSLA': 'XLK', 'AMD': 'XLK',
    'INTC': 'XLK', 'CRM': 'XLK', 'ORCL': 'XLK', 'CSCO': 'XLK',
    'AVGO': 'XLK', 'ADBE': 'XLK', 'QCOM': 'XLK', 'TXN': 'XLK',
    
    # Financials
    'JPM': 'XLF', 'BAC': 'XLF', 'WFC': 'XLF', 'GS': 'XLF',
    'MS': 'XLF', 'C': 'XLF', 'BLK': 'XLF', 'SCHW': 'XLF',
    'AXP': 'XLF', 'USB': 'XLF', 'PNC': 'XLF', 'TFC': 'XLF',
    
    # Healthcare
    'JNJ': 'XLV', 'PFE': 'XLV', 'UNH': 'XLV', 'MRK': 'XLV',
    'ABBV': 'XLV', 'TMO': 'XLV', 'ABT': 'XLV', 'DHR': 'XLV',
    'LLY': 'XLV', 'BMY': 'XLV', 'AMGN': 'XLV', 'CVS': 'XLV',
    
    # Energy
    'XOM': 'XLE', 'CVX': 'XLE', 'COP': 'XLE', 'SLB': 'XLE',
    'EOG': 'XLE', 'PSX': 'XLE', 'MPC': 'XLE', 'VLO': 'XLE',
    
    # Consumer Discretionary
    'AMZN': 'XLY', 'HD': 'XLY', 'MCD': 'XLY', 'NKE': 'XLY',
    'SBUX': 'XLY', 'LOW': 'XLY', 'TGT': 'XLY', 'DIS': 'XLY',
    
    # Consumer Staples
    'WMT': 'XLP', 'PG': 'XLP', 'KO': 'XLP', 'PEP': 'XLP',
    'COST': 'XLP', 'PM': 'XLP', 'MO': 'XLP', 'CL': 'XLP',
    
    # Industrials
    'CAT': 'XLI', 'BA': 'XLI', 'HON': 'XLI', 'UNP': 'XLI',
    'UPS': 'XLI', 'RTX': 'XLI', 'LMT': 'XLI', 'GE': 'XLI',
    
    # Utilities
    'NEE': 'XLU', 'DUK': 'XLU', 'SO': 'XLU', 'D': 'XLU',
    
    # Real Estate
    'AMT': 'XLRE', 'PLD': 'XLRE', 'CCI': 'XLRE', 'EQIX': 'XLRE',
    
    # Materials
    'LIN': 'XLB', 'APD': 'XLB', 'ECL': 'XLB', 'DD': 'XLB',
    
    # Communication Services
    'NFLX': 'XLC', 'CMCSA': 'XLC', 'T': 'XLC', 'VZ': 'XLC',
    
    # Default fallback
    'DEFAULT': 'SPY'
}


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
                       end_date: Optional[pd.Timestamp] = None) -> Optional[pd.DataFrame]:
    """
    Load benchmark data (SPY or sector ETF) from cache via data_manager.
    
    Uses cached data to avoid Yahoo Finance API rate limits and weekend failures.
    
    Args:
        ticker: Benchmark symbol
        period: Data period (e.g., '12mo', '6mo') - ignored if start_date provided
        start_date: Explicit start date (overrides period)
        end_date: Optional end date for historical analysis
        
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
        
        # Align with DataFrame dates (handles weekends/holidays)
        market_regime = spy_data['Market_Regime_OK'].reindex(
            df_index_normalized, 
            method='ffill'  # Forward-fill for non-trading days
        ).infer_objects(copy=False).fillna(False)  # Conservative: missing data = regime FAIL
        
        # Restore original index (with timezone if it had one)
        market_regime.index = df.index
        
        sector_regime = sector_data['Sector_Regime_OK'].reindex(
            df_index_normalized,
            method='ffill'
        ).infer_objects(copy=False).fillna(False)
        
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
        
        df['spy_regime_ok'] = spy_data['spy_regime_ok'].reindex(df_index_norm, method='ffill').fillna(False)
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
            
            df[col_name] = etf_data[col_name].reindex(df_index_norm, method='ffill').fillna(False)
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
