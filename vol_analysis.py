import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import argparse
import sys
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

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
    """Load cached data for a ticker if it exists and is valid."""
    cache_file = get_cache_filepath(ticker)
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        
        # Validate cached data
        if df.empty:
            print(f"⚠️  Empty cache file for {ticker} - will redownload")
            os.remove(cache_file)  # Remove invalid cache
            return None
            
        print(f"📊 Loaded cached data for {ticker}: {len(df)} days ({df.index[0].date()} to {df.index[-1].date()})")
        return df
    except Exception as e:
        print(f"⚠️  Error loading cache for {ticker}: {e}")
        # Remove corrupted cache file
        try:
            os.remove(cache_file)
            print(f"🗑️  Removed corrupted cache file for {ticker}")
        except:
            pass
        return None

def save_to_cache(ticker: str, df: pd.DataFrame) -> None:
    """Save DataFrame to cache."""
    cache_file = get_cache_filepath(ticker)
    try:
        df.to_csv(cache_file)
        print(f"💾 Cached data for {ticker}: {len(df)} days saved to cache")
    except Exception as e:
        print(f"⚠️  Error saving cache for {ticker}: {e}")

def append_to_cache(ticker: str, new_data: pd.DataFrame) -> None:
    """Append new data to existing cache file."""
    cache_file = get_cache_filepath(ticker)
    try:
        # Append new data to the CSV file
        new_data.to_csv(cache_file, mode='a', header=False)
        print(f"📈 Appended {len(new_data)} new days to {ticker} cache")
    except Exception as e:
        print(f"⚠️  Error appending to cache for {ticker}: {e}")

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
        ValueError: If no valid data is available for the ticker
    """
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
    
    if force_refresh:
        print(f"🔄 Force refresh enabled - downloading fresh data for {ticker}")
        df = yf.download(ticker, period=period, interval='1d', auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        df.dropna(inplace=True)
        
        # Validate downloaded data
        if df.empty:
            raise ValueError(f"No data available for {ticker} (possibly delisted or invalid symbol)")
        
        save_to_cache(ticker, df)
        return df
    
    # Try to load cached data
    cached_df = load_cached_data(ticker)
    
    if cached_df is None:
        # No cache exists - download full period
        print(f"📥 No cache found for {ticker} - downloading {period} data from Yahoo Finance")
        df = yf.download(ticker, period=period, interval='1d', auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        df.dropna(inplace=True)
        
        # Validate downloaded data
        if df.empty:
            raise ValueError(f"No data available for {ticker} (possibly delisted or invalid symbol)")
        
        save_to_cache(ticker, df)
        return df
    
    # Check if cached data covers the requested period
    cache_start_date = cached_df.index[0]
    cache_end_date = cached_df.index[-1]
    
    # Check if we need to download more recent data
    today = datetime.now().date()
    last_cached_date = cache_end_date.date()
    days_behind = (today - last_cached_date).days
    
    if days_behind <= 1:
        # Cache is up to date (within 1 day)
        print(f"✅ Cache is current for {ticker} - using cached data")
        # Filter cached data to requested period if needed
        filtered_df = cached_df[cached_df.index >= cutoff_date] if cutoff_date > cache_start_date else cached_df
        return filtered_df
    
    # Need to download recent data
    print(f"📥 Cache is {days_behind} days behind - downloading recent data for {ticker}")
    
    # Download from day after last cached date to today
    start_date = (cache_end_date + timedelta(days=1)).strftime('%Y-%m-%d')
    new_data = yf.download(ticker, start=start_date, interval='1d', auto_adjust=True)
    
    if isinstance(new_data.columns, pd.MultiIndex):
        new_data.columns = new_data.columns.droplevel(1)
    new_data.dropna(inplace=True)
    
    if not new_data.empty:
        # Append new data to cache
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
    else:
        print(f"ℹ️  No new data available for {ticker}")
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
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading file '{filepath}': {str(e)}")
        sys.exit(1)

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
    
    # Recent signals
    recent_df = df.tail(10)
    recent_signals = recent_df[recent_df['Phase'] != 'Neutral']
    
    output.append(f"\n🔍 RECENT SIGNALS (Last 10 days):")
    if not recent_signals.empty:
        for date, row in recent_signals.iterrows():
            score = row['Accumulation_Score']
            phase = row['Phase']
            price = row['Close']
            volume_ratio = row['Relative_Volume']
            
            signal_strength = "🔥 STRONG" if score >= 7 else "⚡ MODERATE" if score >= 4 else "💡 WEAK"
            output.append(f"  {date.strftime('%Y-%m-%d')}: {phase} - Score: {score:.1f}/10 {signal_strength}")
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
    entry_signals = {
        'Strong_Buy': df['Strong_Buy'].sum(),
        'Moderate_Buy': df['Moderate_Buy'].sum(), 
        'Stealth_Accumulation': df['Stealth_Accumulation'].sum(),
        'Confluence_Signal': df['Confluence_Signal'].sum(),
        'Volume_Breakout': df['Volume_Breakout'].sum()
    }
    
    exit_signals = {
        'Profit_Taking': df['Profit_Taking'].sum(),
        'Distribution_Warning': df['Distribution_Warning'].sum(),
        'Sell_Signal': df['Sell_Signal'].sum(),
        'Momentum_Exhaustion': df['Momentum_Exhaustion'].sum(),
        'Stop_Loss': df['Stop_Loss'].sum()
    }
    
    output.append(f"\n🎯 ENTRY SIGNAL SUMMARY:")
    output.append("  🟢 Strong Buy Signals: {} (Large green dots - Score ≥7, near support, above VWAP)".format(entry_signals['Strong_Buy']))
    output.append("  🟡 Moderate Buy Signals: {} (Medium yellow dots - Score 5-7, divergence signals)".format(entry_signals['Moderate_Buy']))
    output.append("  � Stealth Accumulation: {} (Cyan diamonds - High score, low volume)".format(entry_signals['Stealth_Accumulation']))
    output.append("  ⭐ Multi-Signal Confluence: {} (Magenta stars - All indicators aligned)".format(entry_signals['Confluence_Signal']))
    output.append("  � Volume Breakouts: {} (Orange triangles - 2.5x+ volume)".format(entry_signals['Volume_Breakout']))
    
    output.append(f"\n🚪 EXIT SIGNAL SUMMARY:")
    output.append("  🟠 Profit Taking: {} (Orange dots - New highs with waning accumulation)".format(exit_signals['Profit_Taking']))
    output.append("  ⚠️ Distribution Warning: {} (Gold squares - Early distribution signs)".format(exit_signals['Distribution_Warning']))
    output.append("  🔴 Sell Signals: {} (Red dots - Strong distribution below VWAP)".format(exit_signals['Sell_Signal']))
    output.append("  � Momentum Exhaustion: {} (Purple X's - Rising price, declining volume)".format(exit_signals['Momentum_Exhaustion']))
    output.append("  🛑 Stop Loss Triggers: {} (Dark red triangles - Support breakdown)".format(exit_signals['Stop_Loss']))
    
    output.append(f"\n📋 ANALYSIS PERIOD: {period}")
    output.append(f"📅 DATE RANGE: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
    output.append(f"📊 TOTAL TRADING DAYS: {len(df)}")
    
    return "\n".join(output)

def analyze_ticker(ticker: str, period='6mo', save_to_file=False, output_dir='.', save_chart=False, force_refresh=False):
    """
    Retrieve and analyze price-volume data for a given ticker symbol.
    
    Args:
        ticker (str): Stock symbol, e.g. 'AAPL' or 'MSFT'
        period (str): Data period, e.g. '12mo', '6mo', '36mo'
        save_to_file (bool): Whether to save analysis to file instead of printing
        output_dir (str): Directory to save output files
        save_chart (bool): Whether to save chart as PNG file
        force_refresh (bool): If True, ignore cache and download fresh data
        
    Raises:
        ValueError: If no valid data is available for the ticker
    """
    # --- Retrieve Data with Smart Caching ---
    try:
        df = get_smart_data(ticker, period, force_refresh=force_refresh)
    except ValueError as e:
        # Re-raise with more context
        raise ValueError(f"Failed to get data for {ticker}: {str(e)}")
    
    # --- OBV (On-Balance Volume) ---
    df['OBV'] = ( (df['Close'] > df['Close'].shift(1)) * df['Volume']
                - (df['Close'] < df['Close'].shift(1)) * df['Volume'] ).cumsum()
    
    # --- Accumulation/Distribution Line ---
    # Handle division by zero when High == Low
    high_low_diff = df['High'] - df['Low']
    
    # Calculate AD_Multiplier with proper handling of zero divisions
    ad_multiplier = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / high_low_diff
    ad_multiplier = ad_multiplier.fillna(0)  # Replace inf/NaN with 0
    ad_multiplier = ad_multiplier.replace([np.inf, -np.inf], 0)  # Replace inf values with 0
    
    df['AD_Multiplier'] = ad_multiplier
    df['AD_Line'] = (df['AD_Multiplier'] * df['Volume']).cumsum()
    
    # --- Rolling correlation between price and volume ---
    df['Return'] = df['Close'].pct_change()
    df['VolChange'] = df['Volume'].pct_change()
    df['PriceVolumeCorr'] = df['Return'].rolling(20).corr(df['VolChange'])
    
    # --- Enhanced Accumulation/Distribution Detection ---
    
    # 1. OBV Trend Analysis
    df['OBV_MA'] = df['OBV'].rolling(window=10).mean()
    df['OBV_Trend'] = df['OBV'] > df['OBV_MA']
    df['Price_MA'] = df['Close'].rolling(window=10).mean()
    df['Price_Trend'] = df['Close'] > df['Price_MA']
    
    # 2. A/D Line Divergence Detection
    df['AD_MA'] = df['AD_Line'].rolling(window=10).mean()
    df['AD_Rising'] = df['AD_Line'] > df['AD_MA']
    df['Price_Rising'] = df['Close'] > df['Close'].shift(5)
    
    # 3. Volume Analysis
    df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Spike'] = df['Volume'] > (df['Volume_MA'] * 1.5)  # 50% above average
    df['Relative_Volume'] = df['Volume'] / df['Volume_MA']
    
    # 4. Smart Money Indicators
    df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
    df['Above_VWAP'] = df['Close'] > df['VWAP']
    
    # 5. Support Level Analysis (using rolling lows)
    df['Support_Level'] = df['Low'].rolling(window=20).min()
    df['Near_Support'] = (df['Close'] - df['Support_Level']) / df['Support_Level'] < 0.05  # Within 5%
    
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
    df['Phase'] = pd.Series(pd.Categorical(np.select(accumulation_conditions, accumulation_choices, default='Neutral')))
    
    # --- Confidence Scoring ---
    df['Accumulation_Score'] = 0
    df.loc[df['AD_Rising'] & ~df['Price_Rising'], 'Accumulation_Score'] += 2  # A/D divergence
    df.loc[df['OBV_Trend'] & ~df['Price_Trend'], 'Accumulation_Score'] += 2  # OBV divergence
    df.loc[df['Volume_Spike'], 'Accumulation_Score'] += 1  # Volume spike
    df.loc[df['Above_VWAP'], 'Accumulation_Score'] += 1  # Above VWAP
    df.loc[df['Near_Support'], 'Accumulation_Score'] += 1  # Near support
    
    # Normalize score to 0-10 scale
    df['Accumulation_Score'] = np.clip(df['Accumulation_Score'] * 10 / 7, 0, 10)
    
    # --- ENHANCED EXIT SCORING SYSTEM (1-10 scale) ---
    df['Exit_Score'] = 0
    
    # Distribution and trend factors (0-4 points)
    df.loc[df['Phase'] == 'Distribution', 'Exit_Score'] += 2  # Distribution phase
    df.loc[~df['Above_VWAP'], 'Exit_Score'] += 1.5  # Below VWAP
    df.loc[df['Close'] < df['Support_Level'], 'Exit_Score'] += 2  # Below support
    df.loc[df['Close'] < df['Close'].rolling(10).mean(), 'Exit_Score'] += 0.5  # Below 10-day MA
    
    # Volume and momentum factors (0-3 points)
    df.loc[df['Relative_Volume'] > 2.5, 'Exit_Score'] += 1.5  # Very high volume
    df.loc[df['Relative_Volume'] > 1.8, 'Exit_Score'] += 1  # High volume
    df.loc[df['Volume'] < df['Volume'].shift(3), 'Exit_Score'] += 0.5  # Declining volume trend
    
    # Technical indicator factors (0-3 points)
    df.loc[df['AD_Line'] < df['AD_MA'], 'Exit_Score'] += 1  # A/D line declining
    df.loc[df['OBV'] < df['OBV_MA'], 'Exit_Score'] += 1  # OBV declining
    df.loc[df['Accumulation_Score'] < 2, 'Exit_Score'] += 1  # Very low accumulation
    
    # Normalize exit score to 1-10 scale (minimum 1 for any position)
    df['Exit_Score'] = np.clip(df['Exit_Score'] * 10 / 10, 1, 10)
    
    # --- Enhanced Signal Generation for Visual Markers ---
    
    # BUY SIGNALS (Green Dots)
    strong_buy_conditions = (
        (df['Accumulation_Score'] >= 7) & 
        df['Near_Support'] & 
        df['Above_VWAP'] & 
        (df['Relative_Volume'] >= 1.2) &
        (df['Relative_Volume'] <= 3.0)  # Not excessive volume
    )
    
    moderate_buy_conditions = (
        (df['Accumulation_Score'] >= 5) & 
        (df['Accumulation_Score'] < 7) &
        (df['AD_Rising'] | df['OBV_Trend']) &
        df['Above_VWAP']
    )
    
    # === ENHANCED EXIT SIGNALS ===
    
    # 1. PROFIT TAKING SIGNALS (Orange Dots) - Take profits on strength
    profit_taking_conditions = (
        (df['Close'] > df['Close'].rolling(20).max().shift(1)) &  # New highs
        (df['Relative_Volume'] > 1.8) &  # High volume
        df['Above_VWAP'] &  # Still above VWAP
        (df['Accumulation_Score'] < 4) &  # But accumulation waning
        (df['Close'] > df['Close'].shift(1))  # Price up on the day
    )
    
    # 2. DISTRIBUTION WARNING (Gold Squares) - Early warning signs
    distribution_warning_conditions = (
        (df['Phase'] == 'Distribution') &
        (df['Close'] < df['VWAP']) &  # Below VWAP
        (df['Relative_Volume'] > 1.3) &  # Above average volume
        (df['Close'] < df['Close'].shift(3)) &  # Price declining over 3 days
        (df['AD_Line'] < df['AD_MA'])  # A/D line declining
    )
    
    # 3. ENHANCED SELL SIGNALS (Red Dots) - Strong exit signals
    sell_conditions = (
        (df['Phase'] == 'Distribution') &
        ~df['Above_VWAP'] &
        (df['Relative_Volume'] > 1.5) &
        (df['Close'] < df['Support_Level'] * 1.02) &  # Breaking support
        (df['AD_Line'] < df['AD_MA']) &  # A/D line declining
        (df['OBV'] < df['OBV_MA'])  # OBV also declining
    )
    
    # 4. MOMENTUM EXHAUSTION (Purple X's) - Volume/price divergence
    momentum_exhaustion_conditions = (
        (df['Close'] > df['Close'].shift(5)) &  # Price still rising
        (df['Relative_Volume'] < 0.8) &  # But volume declining
        (df['Accumulation_Score'] < 3) &  # Low accumulation
        (df['Close'] > df['Close'].rolling(10).mean() * 1.03) &  # Extended above MA
        (df['Volume'] < df['Volume'].shift(3))  # Volume declining trend
    )
    
    # 5. STOP LOSS TRIGGERS (Dark Red Triangles) - Urgent exit signals
    stop_loss_conditions = (
        (df['Close'] < df['Support_Level']) &  # Below support
        (df['Relative_Volume'] > 1.8) &  # High volume breakdown
        ~df['Above_VWAP'] &  # Below VWAP
        (df['Close'] < df['Close'].rolling(5).mean() * 0.97) &  # 3% below 5-day MA
        (df['Close'] < df['Close'].shift(1))  # Price declining
    )
    
    # SPECIAL SIGNALS
    stealth_accumulation = (
        (df['Accumulation_Score'] >= 6) &
        (df['Relative_Volume'] < 1.3) &  # Low/normal volume
        (df['AD_Rising'] & ~df['Price_Rising'])  # A/D divergence
    )
    
    confluence_signals = (
        (df['Accumulation_Score'] >= 6) &
        df['Near_Support'] &
        df['Volume_Spike'] &
        df['Above_VWAP'] &
        (df['AD_Rising'] & df['OBV_Trend'])  # Multiple indicators aligned
    )
    
    volume_breakout = (
        (df['Accumulation_Score'] >= 5) &
        (df['Relative_Volume'] > 2.5) &
        (df['Close'] > df['Close'].shift(1)) &
        df['Above_VWAP']
    )
    
    # Create signal flags
    df['Strong_Buy'] = strong_buy_conditions
    df['Moderate_Buy'] = moderate_buy_conditions & ~strong_buy_conditions
    df['Sell_Signal'] = sell_conditions
    df['Stealth_Accumulation'] = stealth_accumulation & ~strong_buy_conditions & ~moderate_buy_conditions
    df['Confluence_Signal'] = confluence_signals
    df['Volume_Breakout'] = volume_breakout & ~strong_buy_conditions
    
    # EXIT SIGNAL FLAGS
    df['Profit_Taking'] = profit_taking_conditions
    df['Distribution_Warning'] = distribution_warning_conditions & ~sell_conditions
    df['Momentum_Exhaustion'] = momentum_exhaustion_conditions
    df['Stop_Loss'] = stop_loss_conditions
    
    # --- Enhanced Visualization with Accumulation Signals (Optimized for 16" Mac) ---
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
    
    # Top plot: Price with enhanced signal markers
    ax1.plot(df.index, df['Close'], label='Close Price', color='black', linewidth=1.5)
    ax1.plot(df.index, df['VWAP'], label='VWAP', color='purple', alpha=0.7, linestyle='--')
    ax1.plot(df.index, df['Support_Level'], label='Support Level', color='gray', alpha=0.5, linestyle=':')
    
    # --- ENHANCED BUY/SELL SIGNAL MARKERS ---
    
    # STRONG BUY SIGNALS (Large Green Dots)
    strong_buys = df[df['Strong_Buy']]
    if not strong_buys.empty:
        ax1.scatter(strong_buys.index, strong_buys['Close'], color='lime', marker='o', 
                   s=150, label='Strong Buy', zorder=10, edgecolors='darkgreen', linewidth=2)
    
    # MODERATE BUY SIGNALS (Medium Yellow Dots)  
    moderate_buys = df[df['Moderate_Buy']]
    if not moderate_buys.empty:
        ax1.scatter(moderate_buys.index, moderate_buys['Close'], color='gold', marker='o', 
                   s=100, label='Moderate Buy', zorder=9, edgecolors='orange', linewidth=1.5)
    
    # === EXIT SIGNALS ===
    
    # PROFIT TAKING (Orange Dots)
    profit_takes = df[df['Profit_Taking']]
    if not profit_takes.empty:
        ax1.scatter(profit_takes.index, profit_takes['Close'], color='orange', marker='o', 
                   s=120, label='Profit Taking', zorder=10, edgecolors='darkorange', linewidth=2)
    
    # DISTRIBUTION WARNING (Gold Squares)
    dist_warnings = df[df['Distribution_Warning']]
    if not dist_warnings.empty:
        ax1.scatter(dist_warnings.index, dist_warnings['Close'], color='gold', marker='s', 
                   s=100, label='Distribution Warning', zorder=9, edgecolors='darkgoldenrod', linewidth=2)
    
    # SELL SIGNALS (Red Dots)
    sells = df[df['Sell_Signal']]
    if not sells.empty:
        ax1.scatter(sells.index, sells['Close'], color='red', marker='o', 
                   s=120, label='Sell Signal', zorder=10, edgecolors='darkred', linewidth=2)
    
    # MOMENTUM EXHAUSTION (Purple X's)
    momentum_exhausts = df[df['Momentum_Exhaustion']]
    if not momentum_exhausts.empty:
        ax1.scatter(momentum_exhausts.index, momentum_exhausts['Close'], color='purple', marker='x', 
                   s=120, label='Momentum Exhaustion', zorder=9, linewidth=3)
    
    # STOP LOSS TRIGGERS (Dark Red Triangles Down)
    stop_losses = df[df['Stop_Loss']]
    if not stop_losses.empty:
        ax1.scatter(stop_losses.index, stop_losses['Close'], color='darkred', marker='v', 
                   s=130, label='Stop Loss Trigger', zorder=11, edgecolors='black', linewidth=2)
    
    # STEALTH ACCUMULATION (Diamond Symbols)
    stealth = df[df['Stealth_Accumulation']]
    if not stealth.empty:
        ax1.scatter(stealth.index, stealth['Close'], color='cyan', marker='D', 
                   s=80, label='Stealth Accumulation', zorder=8, alpha=0.8)
    
    # CONFLUENCE SIGNALS (Star Symbols)
    confluence = df[df['Confluence_Signal']]
    if not confluence.empty:
        ax1.scatter(confluence.index, confluence['Close'], color='magenta', marker='*', 
                   s=200, label='Multi-Signal Confluence', zorder=11)
    
    # VOLUME BREAKOUT (Triangle Symbols)
    breakouts = df[df['Volume_Breakout']]
    if not breakouts.empty:
        ax1.scatter(breakouts.index, breakouts['Close'], color='orangered', marker='^', 
                   s=120, label='Volume Breakout', zorder=9, edgecolors='darkred')
    
    ax1.set_ylabel('Price ($)')
    ax1.legend(loc='upper left')
    ax1.set_title(f'{ticker} — Accumulation/Distribution Analysis ({period})')
    ax1.grid(True, alpha=0.3)
    
    # Middle plot: Volume indicators with divergence markers
    ax2.plot(df.index, df['OBV'], label='OBV', color='blue', alpha=0.8)
    ax2.plot(df.index, df['AD_Line'], label='A/D Line', color='orange', alpha=0.8)
    ax2.plot(df.index, df['OBV_MA'], label='OBV MA', color='lightblue', linestyle='--', alpha=0.6)
    ax2.plot(df.index, df['AD_MA'], label='A/D MA', color='moccasin', linestyle='--', alpha=0.6)
    
    # Add divergence markers to volume indicators panel
    if not stealth.empty:
        # Mark stealth accumulation on A/D Line
        ax2.scatter(stealth.index, stealth.index.map(lambda x: df.loc[x, 'AD_Line']), 
                   color='cyan', marker='D', s=60, alpha=0.8, zorder=8)
    
    if not strong_buys.empty:
        # Mark strong buys on OBV
        ax2.scatter(strong_buys.index, strong_buys.index.map(lambda x: df.loc[x, 'OBV']), 
                   color='lime', marker='o', s=80, zorder=9, edgecolors='darkgreen')
    
    ax2.set_ylabel('Volume Indicators')
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    
    # Bottom plot: Volume and Accumulation Score with threshold markers
    ax3_twin = ax3.twinx()
    
    # Volume bars with color coding
    volume_colors = ['red' if phase == 'Distribution' 
                     else 'darkgreen' if phase == 'Strong_Accumulation'
                     else 'lightgreen' if phase == 'Moderate_Accumulation'
                     else 'yellow' if phase == 'Support_Accumulation'
                     else 'lightgray' for phase in df['Phase']]
    
    ax3.bar(df.index, df['Volume'], color=volume_colors, alpha=0.6, width=1)
    ax3.plot(df.index, df['Volume_MA'], label='Volume MA', color='black', linestyle='-', alpha=0.8)
    
    # Add volume breakout markers
    if not breakouts.empty:
        ax3.scatter(breakouts.index, breakouts.index.map(lambda x: df.loc[x, 'Volume']), 
                   color='orangered', marker='^', s=100, zorder=9, edgecolors='darkred')
    
    # Add exit signal markers to volume panel
    if not profit_takes.empty:
        ax3.scatter(profit_takes.index, profit_takes.index.map(lambda x: df.loc[x, 'Volume']), 
                   color='orange', marker='o', s=80, zorder=9, edgecolors='darkorange')
    
    if not stop_losses.empty:
        ax3.scatter(stop_losses.index, stop_losses.index.map(lambda x: df.loc[x, 'Volume']), 
                   color='darkred', marker='v', s=100, zorder=10, edgecolors='black')
    
    ax3.set_ylabel('Volume')
    ax3.legend(loc='upper left')
    
    # Dual scoring system: Accumulation and Exit scores
    ax3_twin.plot(df.index, df['Accumulation_Score'], label='Accumulation Score', 
                  color='green', linewidth=2, alpha=0.8)
    ax3_twin.plot(df.index, df['Exit_Score'], label='Exit Score', 
                  color='red', linewidth=2, alpha=0.8)
    
    # Add horizontal threshold lines for both entry and exit scores
    ax3_twin.axhline(y=8, color='darkred', linestyle=':', alpha=0.8, label='Urgent Exit (8)')
    ax3_twin.axhline(y=7, color='lime', linestyle=':', alpha=0.7, label='Strong Entry (7)')
    ax3_twin.axhline(y=6, color='orange', linestyle=':', alpha=0.7, label='High Exit Risk (6)')
    ax3_twin.axhline(y=4, color='gold', linestyle=':', alpha=0.6, label='Moderate Risk (4)')
    ax3_twin.axhline(y=2, color='lightcoral', linestyle=':', alpha=0.5, label='Low Risk (2)')
    
    # Mark actual Strong Buy signal occurrences (not just score thresholds)
    actual_strong_buys = df[df['Strong_Buy'] == True]
    if not actual_strong_buys.empty:
        ax3_twin.scatter(actual_strong_buys.index, actual_strong_buys['Accumulation_Score'], 
                        color='lime', marker='o', s=50, zorder=10, alpha=0.8, 
                        label='Strong Buy Signals')
    
    high_exit_points = df[df['Exit_Score'] >= 6]
    if not high_exit_points.empty:
        ax3_twin.scatter(high_exit_points.index, high_exit_points['Exit_Score'], 
                        color='red', marker='s', s=40, zorder=10, alpha=0.8)
    
    urgent_exit_points = df[df['Exit_Score'] >= 8]
    if not urgent_exit_points.empty:
        ax3_twin.scatter(urgent_exit_points.index, urgent_exit_points['Exit_Score'], 
                        color='darkred', marker='X', s=60, zorder=11, alpha=0.9)
    
    ax3_twin.set_ylabel('Entry/Exit Scores (0-10)')
    ax3_twin.legend(loc='upper left')
    ax3_twin.set_ylim(0, 10)
    
    ax3.grid(True, alpha=0.3)
    plt.xlabel('Date')
    plt.tight_layout()
    
    # Handle chart display/saving
    if save_chart:
        # Create filename with date range
        start_date = df.index[0].strftime('%Y%m%d')
        end_date = df.index[-1].strftime('%Y%m%d')
        chart_filename = f"{ticker}_{period}_{start_date}_{end_date}_chart.png"
        chart_filepath = os.path.join(output_dir, chart_filename)
        plt.savefig(chart_filepath, dpi=150, bbox_inches='tight')
        print(f"📊 Chart saved: {chart_filename}")
        plt.close()  # Close the figure to free memory
    else:
        plt.show()
    
    # Handle text output
    if save_to_file:
        # Generate filename with date range
        start_date = df.index[0].strftime('%Y%m%d')
        end_date = df.index[-1].strftime('%Y%m%d')
        filename = f"{ticker}_{period}_{start_date}_{end_date}_analysis.txt"
        filepath = os.path.join(output_dir, filename)
        
        # Generate analysis text
        analysis_text = generate_analysis_text(ticker, df, period)
        
        # Write to file
        with open(filepath, 'w') as f:
            f.write(analysis_text)
        
        return df, filepath
    else:
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
        
        # Recent accumulation signals (last 10 trading days)
        recent_df = df.tail(10)
        recent_signals = recent_df[recent_df['Phase'] != 'Neutral']
        
        print(f"\n🔍 RECENT SIGNALS (Last 10 days):")
        if not recent_signals.empty:
            for date, row in recent_signals.iterrows():
                score = row['Accumulation_Score']
                phase = row['Phase']
                price = row['Close']
                volume_ratio = row['Relative_Volume']
                
                signal_strength = "🔥 STRONG" if score >= 7 else "⚡ MODERATE" if score >= 4 else "💡 WEAK"
                print(f"  {date.strftime('%Y-%m-%d')}: {phase} - Score: {score:.1f}/10 {signal_strength}")
                print(f"    Price: ${price:.2f}, Volume: {volume_ratio:.1f}x average")
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
        
        # Enhanced signal counts - Entry and Exit
        entry_signals = {
            'Strong_Buy': df['Strong_Buy'].sum(),
            'Moderate_Buy': df['Moderate_Buy'].sum(), 
            'Stealth_Accumulation': df['Stealth_Accumulation'].sum(),
            'Confluence_Signal': df['Confluence_Signal'].sum(),
            'Volume_Breakout': df['Volume_Breakout'].sum()
        }
        
        exit_signals = {
            'Profit_Taking': df['Profit_Taking'].sum(),
            'Distribution_Warning': df['Distribution_Warning'].sum(),
            'Sell_Signal': df['Sell_Signal'].sum(),
            'Momentum_Exhaustion': df['Momentum_Exhaustion'].sum(),
            'Stop_Loss': df['Stop_Loss'].sum()
        }
        
        print(f"\n🎯 ENTRY SIGNAL SUMMARY:")
        print("  🟢 Strong Buy Signals: {} (Large green dots - Score ≥7, near support, above VWAP)".format(entry_signals['Strong_Buy']))
        print("  🟡 Moderate Buy Signals: {} (Medium yellow dots - Score 5-7, divergence signals)".format(entry_signals['Moderate_Buy']))
        print("  💎 Stealth Accumulation: {} (Cyan diamonds - High score, low volume)".format(entry_signals['Stealth_Accumulation']))
        print("  ⭐ Multi-Signal Confluence: {} (Magenta stars - All indicators aligned)".format(entry_signals['Confluence_Signal']))
        print("  🔥 Volume Breakouts: {} (Orange triangles - 2.5x+ volume)".format(entry_signals['Volume_Breakout']))
        
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
        
        return df

def multi_timeframe_analysis(ticker: str, periods=['1mo', '3mo', '6mo', '12mo']):
    """
    Analyze accumulation signals across multiple timeframes for stronger confirmation.
    """
    print(f"\n🔍 MULTI-TIMEFRAME ACCUMULATION ANALYSIS FOR {ticker.upper()}")
    print("="*70)
    
    results = {}
    for period in periods:
        print(f"\n📅 Analyzing {period} timeframe...")
        df_temp = analyze_ticker(ticker, period=period)
        
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

def calculate_recent_stealth_score(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate recent stealth buying activity score focusing on recent signals.
    
    Args:
        df (pd.DataFrame): Analysis results dataframe
        
    Returns:
        Dict[str, float]: Dictionary with stealth metrics
    """
    # Focus on recent 10 days for stealth activity
    recent_df = df.tail(10)
    
    # 1. Recent Stealth Signal Count (0-4 points)
    recent_stealth_count = recent_df['Stealth_Accumulation'].sum()
    stealth_recency_score = min(recent_stealth_count * 2, 4)  # Max 4 points
    
    # 2. Days since last stealth signal (0-3 points)
    stealth_signals = df[df['Stealth_Accumulation'] == True]
    if not stealth_signals.empty:
        last_stealth_date = stealth_signals.index[-1]
        days_since_stealth = (df.index[-1] - last_stealth_date).days
        # More recent = higher score
        recency_score = max(3 - (days_since_stealth / 3), 0)  # Max 3 points
    else:
        recency_score = 0
    
    # 3. Price containment during stealth period (0-3 points)
    if not stealth_signals.empty:
        # Get price change from first stealth signal to now
        first_stealth_price = stealth_signals['Close'].iloc[0] if len(stealth_signals) > 1 else stealth_signals['Close'].iloc[-1]
        current_price = df['Close'].iloc[-1]
        price_change_pct = ((current_price - first_stealth_price) / first_stealth_price) * 100
        
        # Lower price appreciation = higher score (what user wants)
        if price_change_pct <= 2:  # Less than 2% gain
            containment_score = 3
        elif price_change_pct <= 5:  # Less than 5% gain
            containment_score = 2
        elif price_change_pct <= 10:  # Less than 10% gain
            containment_score = 1
        else:
            containment_score = 0
    else:
        containment_score = 0
    
    # Total stealth score (0-10 scale)
    total_stealth_score = stealth_recency_score + recency_score + containment_score
    
    return {
        'stealth_score': min(total_stealth_score, 10),
        'recent_stealth_count': recent_stealth_count,
        'days_since_stealth': days_since_stealth if not stealth_signals.empty else 999,
        'price_change_pct': price_change_pct if not stealth_signals.empty else 0
    }

def calculate_recent_entry_score(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate recent strong entry signal activity score focusing on momentum signals.
    
    Args:
        df (pd.DataFrame): Analysis results dataframe
        
    Returns:
        Dict[str, float]: Dictionary with entry signal metrics
    """
    # Focus on recent 10 days for entry activity
    recent_df = df.tail(10)
    
    # Count different types of entry signals in recent period
    recent_strong_buy = recent_df['Strong_Buy'].sum()
    recent_confluence = recent_df['Confluence_Signal'].sum()
    recent_volume_breakout = recent_df['Volume_Breakout'].sum()
    
    # 1. Signal diversity and strength (0-4 points)
    signal_strength_score = 0
    if recent_strong_buy > 0:
        signal_strength_score += min(recent_strong_buy * 1.5, 2)  # Strong buy signals worth more
    if recent_confluence > 0:
        signal_strength_score += min(recent_confluence * 2, 2)  # Confluence signals are premium
    if recent_volume_breakout > 0:
        signal_strength_score += min(recent_volume_breakout * 1, 1)  # Volume breakouts
    signal_strength_score = min(signal_strength_score, 4)
    
    # 2. Days since last strong entry signal (0-3 points)
    entry_signals = df[(df['Strong_Buy'] == True) | (df['Confluence_Signal'] == True) | (df['Volume_Breakout'] == True)]
    if not entry_signals.empty:
        last_entry_date = entry_signals.index[-1]
        days_since_entry = (df.index[-1] - last_entry_date).days
        # More recent = higher score
        recency_score = max(3 - (days_since_entry / 2), 0)  # Max 3 points, faster decay than stealth
    else:
        recency_score = 0
        days_since_entry = 999
    
    # 3. Signal momentum - are signals increasing or decreasing? (0-3 points)
    # Compare recent 5 days vs previous 5 days
    if len(df) >= 10:
        recent_5 = df.tail(5)
        previous_5 = df.tail(10).head(5)
        
        recent_total = (recent_5['Strong_Buy'].sum() + 
                       recent_5['Confluence_Signal'].sum() + 
                       recent_5['Volume_Breakout'].sum())
        previous_total = (previous_5['Strong_Buy'].sum() + 
                         previous_5['Confluence_Signal'].sum() + 
                         previous_5['Volume_Breakout'].sum())
        
        if recent_total > previous_total:
            momentum_score = 3  # Increasing momentum
            momentum_direction = "up"
        elif recent_total == previous_total and recent_total > 0:
            momentum_score = 2  # Steady momentum
            momentum_direction = "steady"
        elif recent_total > 0:
            momentum_score = 1  # Some activity but declining
            momentum_direction = "down"
        else:
            momentum_score = 0  # No activity
            momentum_direction = "none"
    else:
        momentum_score = 0
        momentum_direction = "none"
    
    # Total entry score (0-10 scale)
    total_entry_score = signal_strength_score + recency_score + momentum_score
    
    return {
        'entry_score': min(total_entry_score, 10),
        'recent_strong_buy': recent_strong_buy,
        'recent_confluence': recent_confluence,
        'recent_volume_breakout': recent_volume_breakout,
        'days_since_entry': days_since_entry,
        'momentum_direction': momentum_direction,
        'total_recent_signals': recent_strong_buy + recent_confluence + recent_volume_breakout
    }

def generate_html_summary(results: List[Dict], errors: List[Dict], period: str, 
                         output_dir: str, timestamp: str) -> str:
    """
    Generate interactive HTML summary with clickable charts.
    
    Args:
        results (List[Dict]): Processed ticker results
        errors (List[Dict]): Processing errors  
        period (str): Analysis period
        output_dir (str): Output directory path
        timestamp (str): Timestamp for filename
        
    Returns:
        str: HTML filename
    """
    # Sort results for both rankings
    sorted_stealth_results = sorted(results, key=lambda x: x['stealth_score'], reverse=True)
    sorted_entry_results = sorted(results, key=lambda x: x['entry_score'], reverse=True)
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Volume Analysis Batch Summary - {period}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            margin: 20px;
            background-color: #f8f9fa;
            color: #333;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 3px solid #007acc;
        }}
        
        .header h1 {{
            color: #007acc;
            margin: 0;
            font-size: 2.2em;
        }}
        
        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        
        .stat-card h3 {{
            margin: 0 0 10px 0;
            font-size: 2em;
        }}
        
        .rankings {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 40px;
            margin-bottom: 40px;
        }}
        
        .ranking-section h2 {{
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }}
        
        .ticker-row {{
            display: grid;
            grid-template-columns: 40px 80px 1fr;
            gap: 15px;
            padding: 12px;
            margin-bottom: 8px;
            background: #f8f9fa;
            border-radius: 6px;
            border-left: 4px solid #007acc;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        
        .ticker-row:hover {{
            background: #e3f2fd;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        
        .rank {{
            font-weight: bold;
            color: #007acc;
            text-align: center;
        }}
        
        .ticker-symbol {{
            font-weight: bold;
            font-size: 1.1em;
            color: #333;
        }}
        
        .ticker-details {{
            font-size: 0.9em;
            color: #666;
        }}
        
        .chart-container {{
            margin-top: 15px;
            padding: 20px;
            background: white;
            border-radius: 8px;
            border: 1px solid #ddd;
            display: none;
        }}
        
        .chart-container.active {{
            display: block;
            animation: slideDown 0.3s ease;
        }}
        
        @keyframes slideDown {{
            from {{ opacity: 0; transform: translateY(-20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .chart-image {{
            max-width: 100%;
            height: auto;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .chart-controls {{
            margin-bottom: 15px;
            text-align: center;
        }}
        
        .btn {{
            background: #007acc;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            margin: 0 5px;
            font-size: 0.9em;
            transition: background 0.2s ease;
        }}
        
        .btn:hover {{
            background: #005fa3;
        }}
        
        .error-section {{
            margin-top: 40px;
            padding: 20px;
            background: #fff3cd;
            border-radius: 6px;
            border-left: 4px solid #f39c12;
        }}
        
        .emoji {{
            font-size: 1.2em;
            margin-right: 5px;
        }}
        
        .timestamp {{
            text-align: center;
            color: #666;
            margin-top: 30px;
            font-size: 0.9em;
        }}
        
        @media (max-width: 768px) {{
            .rankings {{
                grid-template-columns: 1fr;
            }}
            .summary-stats {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Volume Analysis Batch Summary</h1>
            <p>Interactive Report for {period} Analysis Period</p>
        </div>
        
        <div class="summary-stats">
            <div class="stat-card">
                <h3>{len(results)}</h3>
                <p>Tickers Processed</p>
            </div>
            <div class="stat-card">
                <h3>{len([r for r in results if r['stealth_score'] >= 5])}</h3>
                <p>Strong Stealth Candidates</p>
            </div>
            <div class="stat-card">
                <h3>{len([r for r in results if r['entry_score'] >= 5])}</h3>
                <p>Strong Entry Candidates</p>
            </div>
            <div class="stat-card">
                <h3>{len(errors)}</h3>
                <p>Processing Errors</p>
            </div>
        </div>
        
        <div class="rankings">
            <div class="ranking-section">
                <h2>🎯 Top Stealth Accumulation Candidates</h2>"""
    
    # Add stealth candidates
    for i, result in enumerate(sorted_stealth_results[:15], 1):
        stealth_score = result['stealth_score']
        recent_count = result['recent_stealth_count']
        days_since = result['days_since_stealth']
        price_change = result['price_change_pct']
        
        score_emoji = "🎯" if stealth_score >= 7 else "💎" if stealth_score >= 5 else "👁️" if stealth_score >= 3 else "💤"
        recency_text = "Recent" if days_since <= 2 else f"{days_since}d ago" if days_since < 999 else "None"
        
        # Check if chart exists
        chart_filename = f"{result['ticker']}_{period}_{result['filename'].split('_')[2]}_{result['filename'].split('_')[3]}_chart.png"
        chart_exists = os.path.exists(os.path.join(output_dir, chart_filename))
        
        html_content += f"""
                <div class="ticker-row" onclick="toggleChart('stealth_{result['ticker']}')">
                    <div class="rank">#{i}</div>
                    <div class="ticker-symbol">{result['ticker']}</div>
                    <div class="ticker-details">
                        <div><span class="emoji">{score_emoji}</span>Stealth Score: <strong>{stealth_score:.1f}/10</strong></div>
                        <div>Last Signal: {recency_text} | Recent Count: {recent_count} | Price Change: {price_change:+.1f}%</div>
                    </div>
                </div>"""
        
        if chart_exists:
            html_content += f"""
                <div id="stealth_{result['ticker']}" class="chart-container">
                    <div class="chart-controls">
                        <button class="btn" onclick="openChart('{chart_filename}')">📊 Open Full Size</button>
                        <button class="btn" onclick="openAnalysis('{result['filename']}')">📋 View Analysis</button>
                    </div>
                    <img src="{chart_filename}" alt="{result['ticker']} Chart" class="chart-image">
                </div>"""
    
    html_content += """
            </div>
            
            <div class="ranking-section">
                <h2>🚀 Top Recent Strong Entry Candidates</h2>"""
    
    # Add entry candidates
    for i, result in enumerate(sorted_entry_results[:15], 1):
        entry_score = result['entry_score']
        recent_strong = result['recent_strong_buy']
        recent_confluence = result['recent_confluence']
        recent_volume = result['recent_volume_breakout']
        momentum = result['momentum_direction']
        
        score_emoji = "🔥" if entry_score >= 9 else "⚡" if entry_score >= 7 else "💪" if entry_score >= 5 else "👁️"
        momentum_arrow = "↗️" if momentum == "up" else "→" if momentum == "steady" else "↘️" if momentum == "down" else "💤"
        
        # Check if chart exists
        chart_filename = f"{result['ticker']}_{period}_{result['filename'].split('_')[2]}_{result['filename'].split('_')[3]}_chart.png"
        chart_exists = os.path.exists(os.path.join(output_dir, chart_filename))
        
        html_content += f"""
                <div class="ticker-row" onclick="toggleChart('entry_{result['ticker']}')">
                    <div class="rank">#{i}</div>
                    <div class="ticker-symbol">{result['ticker']}</div>
                    <div class="ticker-details">
                        <div><span class="emoji">{score_emoji}</span>Entry Score: <strong>{entry_score:.1f}/10</strong></div>
                        <div>Strong: {recent_strong} | Confluence: {recent_confluence} | Volume: {recent_volume} | Momentum: {momentum_arrow}</div>
                    </div>
                </div>"""
        
        if chart_exists:
            html_content += f"""
                <div id="entry_{result['ticker']}" class="chart-container">
                    <div class="chart-controls">
                        <button class="btn" onclick="openChart('{chart_filename}')">📊 Open Full Size</button>
                        <button class="btn" onclick="openAnalysis('{result['filename']}')">📋 View Analysis</button>
                    </div>
                    <img src="{chart_filename}" alt="{result['ticker']} Chart" class="chart-image">
                </div>"""
    
    html_content += """
            </div>
        </div>"""
    
    # Add errors section if there are any
    if errors:
        html_content += f"""
        <div class="error-section">
            <h3>⚠️ Processing Errors ({len(errors)})</h3>
            <ul>"""
        for error in errors:
            html_content += f"<li><strong>{error['ticker']}</strong>: {error['error']}</li>"
        html_content += """
            </ul>
        </div>"""
    
    # Add footer and JavaScript
    html_content += f"""
        <div class="timestamp">
            Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}
        </div>
    </div>
    
    <script>
        function toggleChart(elementId) {{
            const chart = document.getElementById(elementId);
            if (chart) {{
                chart.classList.toggle('active');
            }}
        }}
        
        function openChart(filename) {{
            // This will attempt to open the chart image in VS Code
            const fullPath = window.location.href.replace(/[^/]*$/, '') + filename;
            window.open(fullPath, '_blank');
        }}
        
        function openAnalysis(filename) {{
            // This will attempt to open the analysis text file
            const fullPath = window.location.href.replace(/[^/]*$/, '') + filename;
            window.open(fullPath, '_blank');
        }}
        
        // Add keyboard shortcuts
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') {{
                // Close all open charts
                document.querySelectorAll('.chart-container.active').forEach(chart => {{
                    chart.classList.remove('active');
                }});
            }}
        }});
    </script>
</body>
</html>"""
    
    # Save HTML file
    html_filename = f"batch_summary_{period}_{timestamp}.html"
    html_filepath = os.path.join(output_dir, html_filename)
    
    with open(html_filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return html_filename

def batch_process_tickers(ticker_file: str, period='12mo', output_dir='results_volume', 
                         save_charts=False, generate_html=True):
    """
    Process multiple tickers from a file and save individual analysis reports.
    
    Args:
        ticker_file (str): Path to file containing ticker symbols
        period (str): Analysis period
        output_dir (str): Directory to save output files
        save_charts (bool): Whether to save chart images
        generate_html (bool): Whether to generate interactive HTML summary
    """
    # Read tickers from file
    tickers = read_ticker_file(ticker_file)
    
    if not tickers:
        print("❌ No valid tickers found in file.")
        return
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📁 Created output directory: {output_dir}")
    
    print(f"\n🚀 BATCH PROCESSING {len(tickers)} TICKERS")
    print("="*50)
    print(f"📁 Output directory: {output_dir}")
    print(f"📅 Period: {period}")
    print(f"📊 Save charts: {'Yes' if save_charts else 'No'}")
    print("="*50)
    
    # Track results for summary
    results = []
    errors = []
    
    for i, ticker in enumerate(tickers, 1):
        print(f"\n[{i}/{len(tickers)}] Processing {ticker}...")
        
        try:
            # Analyze ticker with file output
            result = analyze_ticker(
                ticker=ticker,
                period=period,
                save_to_file=True,
                output_dir=output_dir,
                save_chart=save_charts
            )
            
            if isinstance(result, tuple):
                df, filepath = result
                filename = os.path.basename(filepath)
                print(f"✅ {ticker}: Analysis saved to {filename}")
                
                # Collect summary data using both stealth and entry scoring
                phase_counts = df['Phase'].value_counts()
                stealth_metrics = calculate_recent_stealth_score(df)
                entry_metrics = calculate_recent_entry_score(df)
                
                results.append({
                    'ticker': ticker,
                    'filename': filename,
                    'stealth_score': stealth_metrics['stealth_score'],
                    'recent_stealth_count': stealth_metrics['recent_stealth_count'],
                    'days_since_stealth': stealth_metrics['days_since_stealth'],
                    'price_change_pct': stealth_metrics['price_change_pct'],
                    'entry_score': entry_metrics['entry_score'],
                    'recent_strong_buy': entry_metrics['recent_strong_buy'],
                    'recent_confluence': entry_metrics['recent_confluence'],
                    'recent_volume_breakout': entry_metrics['recent_volume_breakout'],
                    'days_since_entry': entry_metrics['days_since_entry'],
                    'momentum_direction': entry_metrics['momentum_direction'],
                    'total_recent_entry_signals': entry_metrics['total_recent_signals'],
                    'total_days': len(df),
                    'strong_signals': df['Strong_Buy'].sum(),
                    'moderate_signals': df['Moderate_Buy'].sum(),
                    'total_stealth_signals': df['Stealth_Accumulation'].sum(),
                    'latest_phase': df['Phase'].iloc[-1],
                    'exit_score': df['Exit_Score'].iloc[-1],
                    'profit_taking_signals': df['Profit_Taking'].sum(),
                    'sell_signals': df['Sell_Signal'].sum(),
                    'stop_loss_signals': df['Stop_Loss'].sum()
                })
            
        except ValueError as e:
            # Handle data availability errors more gracefully
            if "No data available" in str(e) or "possibly delisted" in str(e):
                print(f"⚠️  {ticker}: No data available (possibly delisted or invalid symbol)")
                errors.append({'ticker': ticker, 'error': 'No data available (possibly delisted)'})
            else:
                print(f"❌ {ticker}: {str(e)}")
                errors.append({'ticker': ticker, 'error': str(e)})
            continue
        except Exception as e:
            error_msg = f"Error processing {ticker}: {str(e)}"
            print(f"❌ {error_msg}")
            errors.append({'ticker': ticker, 'error': str(e)})
            continue
    
    # Generate summary report
    if results:
        print(f"\n📋 BATCH PROCESSING SUMMARY")
        print("="*60)
        print(f"✅ Successfully processed: {len(results)}/{len(tickers)} tickers")
        
        if errors:
            print(f"❌ Errors: {len(errors)}")
            for error in errors:
                print(f"   • {error['ticker']}: {error['error']}")
        
        print(f"\n🎯 TOP STEALTH ACCUMULATION CANDIDATES (by recent activity):")
        sorted_stealth_results = sorted(results, key=lambda x: x['stealth_score'], reverse=True)
        
        for i, result in enumerate(sorted_stealth_results[:10], 1):  # Top 10
            stealth_score = result['stealth_score']
            recent_count = result['recent_stealth_count']
            days_since = result['days_since_stealth']
            price_change = result['price_change_pct']
            total_stealth = result['total_stealth_signals']
            
            score_emoji = "🎯" if stealth_score >= 7 else "💎" if stealth_score >= 5 else "👁️" if stealth_score >= 3 else "💤"
            
            # Display days since or "Recent" if very recent
            recency_text = "Recent" if days_since <= 2 else f"{days_since}d ago" if days_since < 999 else "None"
            
            print(f"  {i:2d}. {result['ticker']:5s} - Stealth: {stealth_score:4.1f}/10 {score_emoji} "
                  f"(Last: {recency_text}, Recent: {recent_count}, Price: {price_change:+4.1f}%, Total: {total_stealth})")

        print(f"\n🚀 TOP RECENT STRONG ENTRY CANDIDATES (by signal strength):")
        sorted_entry_results = sorted(results, key=lambda x: x['entry_score'], reverse=True)
        
        for i, result in enumerate(sorted_entry_results[:10], 1):  # Top 10
            entry_score = result['entry_score']
            recent_strong = result['recent_strong_buy']
            recent_confluence = result['recent_confluence']
            recent_volume = result['recent_volume_breakout']
            days_since = result['days_since_entry']
            momentum = result['momentum_direction']
            
            score_emoji = "🔥" if entry_score >= 9 else "⚡" if entry_score >= 7 else "💪" if entry_score >= 5 else "👁️"
            
            # Display days since or "Recent" if very recent
            recency_text = "Recent" if days_since <= 2 else f"{days_since}d ago" if days_since < 999 else "None"
            
            # Momentum arrow
            momentum_arrow = "↗️" if momentum == "up" else "→" if momentum == "steady" else "↘️" if momentum == "down" else "💤"
            
            print(f"  {i:2d}. {result['ticker']:5s} - Entry: {entry_score:5.1f}/10 {score_emoji} "
                  f"(Last: {recency_text:7s}, Strong: {recent_strong}, Conf: {recent_confluence}, Vol: {recent_volume}, Momentum: {momentum_arrow})")
        
        # Generate consolidated summary file
        summary_filename = f"batch_summary_{period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        summary_filepath = os.path.join(output_dir, summary_filename)
        
        with open(summary_filepath, 'w') as f:
            f.write("BATCH PROCESSING SUMMARY\n")
            f.write("="*60 + "\n\n")
            f.write(f"Processing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Period: {period}\n")
            f.write(f"Total Tickers: {len(tickers)}\n")
            f.write(f"Successfully Processed: {len(results)}\n")
            f.write(f"Errors: {len(errors)}\n\n")
            
            if errors:
                f.write("ERRORS:\n")
                for error in errors:
                    f.write(f"  • {error['ticker']}: {error['error']}\n")
                f.write("\n")
            
            f.write("RESULTS RANKED BY STEALTH ACCUMULATION SCORE:\n")
            f.write("-" * 90 + "\n")
            f.write(f"{'Rank':<4} {'Ticker':<6} {'Stealth':<7} {'Recent':<6} {'DaysAgo':<7} {'Price%':<7} {'Total':<5} {'File'}\n")
            f.write("-" * 90 + "\n")
            
            for i, result in enumerate(sorted_stealth_results, 1):
                days_text = "Recent" if result['days_since_stealth'] <= 2 else f"{result['days_since_stealth']}d" if result['days_since_stealth'] < 999 else "None"
                f.write(f"{i:<4} {result['ticker']:<6} {result['stealth_score']:<7.1f} "
                       f"{result['recent_stealth_count']:<6} {days_text:<7} {result['price_change_pct']:<+7.1f} "
                       f"{result['total_stealth_signals']:<5} {result['filename']}\n")

            f.write("\n\nRESULTS RANKED BY RECENT STRONG ENTRY SCORE:\n")
            f.write("-" * 100 + "\n")
            f.write(f"{'Rank':<4} {'Ticker':<6} {'Entry':<6} {'Strong':<6} {'Conf':<4} {'Vol':<3} {'DaysAgo':<7} {'Momentum':<8} {'File'}\n")
            f.write("-" * 100 + "\n")
            
            for i, result in enumerate(sorted_entry_results, 1):
                days_text = "Recent" if result['days_since_entry'] <= 2 else f"{result['days_since_entry']}d" if result['days_since_entry'] < 999 else "None"
                momentum_text = "Up" if result['momentum_direction'] == "up" else "Steady" if result['momentum_direction'] == "steady" else "Down" if result['momentum_direction'] == "down" else "None"
                f.write(f"{i:<4} {result['ticker']:<6} {result['entry_score']:<6.1f} "
                       f"{result['recent_strong_buy']:<6} {result['recent_confluence']:<4} {result['recent_volume_breakout']:<3} "
                       f"{days_text:<7} {momentum_text:<8} {result['filename']}\n")
        
        # Generate interactive HTML summary if requested and charts exist
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if generate_html:
            # Force chart generation if HTML is requested but charts weren't generated
            if not save_charts:
                print(f"\n📊 HTML requested - generating charts for interactive summary...")
                # Re-process with chart generation for HTML
                for i, ticker in enumerate([r['ticker'] for r in results[:5]], 1):  # Top 5 for charts
                    print(f"  Generating chart {i}/5: {ticker}...")
                    try:
                        analyze_ticker(
                            ticker=ticker,
                            period=period,
                            save_to_file=False,  # Don't overwrite analysis files
                            output_dir=output_dir,
                            save_chart=True,  # Force chart generation
                            force_refresh=False
                        )
                    except Exception as e:
                        print(f"    ⚠️ Chart generation failed for {ticker}: {str(e)}")
            
            # Generate HTML summary
            html_filename = generate_html_summary(results, errors, period, output_dir, timestamp)
            print(f"\n🌐 Interactive HTML summary generated: {html_filename}")
            print(f"   📂 Open in VS Code for clickable charts and analysis links")
        
        print(f"\n📄 Summary report saved: {summary_filename}")
        print(f"📁 All files saved to: {os.path.abspath(output_dir)}")
    
    else:
        print(f"\n❌ No tickers were successfully processed.")

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
        help='Save chart images as PNG files (batch mode only)'
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
    
    args = parser.parse_args()
    
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
            # Batch processing mode
            print(f"🚀 Starting batch processing from file: {args.file}")
            batch_process_tickers(
                ticker_file=args.file,
                period=args.period,
                output_dir=args.output_dir,
                save_charts=args.save_charts
            )
            print(f"\n✅ Batch processing complete!")
        else:
            # Single ticker mode
            ticker = args.ticker.upper()
            print(f"🚀 Starting analysis for {ticker}...")
            
            if args.multi:
                # Run multi-timeframe analysis
                results = multi_timeframe_analysis(ticker)
            else:
                # Run single period analysis with force refresh option
                df = analyze_ticker(ticker, period=args.period, force_refresh=args.force_refresh)
                
            print(f"\n✅ Analysis complete for {ticker}!")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("Please check your inputs and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
