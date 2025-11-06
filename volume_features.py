"""
Volume analysis and flow detection module.

This module handles:
- Chaikin Money Flow (CMF) calculation and normalization
- Volume spike detection
- Event day identification (ATR/volume spikes)
- Volume surprise analysis
- Volume-price divergence detection

Part of Item #7: Refactor/Integration Plan
Includes Item #10: CMF Replacement for A/D + OBV
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional


def calculate_cmf(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    Calculate Chaikin Money Flow (CMF).
    
    CMF measures buying/selling pressure by comparing close position within 
    the bar's range, weighted by volume. Replaces A/D Line and OBV to eliminate
    redundant volume flow indicators.
    
    This is the core implementation of Item #10: Volume Flow Simplification.
    
    Formula:
    Money Flow Multiplier = ((Close - Low) - (High - Close)) / (High - Low)
    Money Flow Volume = Money Flow Multiplier × Volume
    CMF = Sum(Money Flow Volume, period) / Sum(Volume, period)
    
    Range: -1.0 to +1.0
    - Values near +1.0: Strong buying pressure
    - Values near -1.0: Strong selling pressure
    - Values near 0: Neutral or choppy
    
    Args:
        df (pd.DataFrame): DataFrame with OHLCV columns
        period (int): Rolling period for CMF calculation (default: 20)
        
    Returns:
        pd.Series: CMF values
        
    Example:
        >>> df['CMF_20'] = calculate_cmf(df, period=20)
        >>> # Use CMF for entry (positive) and exit (negative) signals
    """
    # Handle division by zero when High == Low
    high_low_diff = df['High'] - df['Low']
    
    # Calculate Money Flow Multiplier
    mf_multiplier = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / high_low_diff
    mf_multiplier = mf_multiplier.fillna(0)  # Replace NaN with 0
    mf_multiplier = mf_multiplier.replace([np.inf, -np.inf], 0)  # Replace inf values with 0
    
    # Calculate Money Flow Volume
    mf_volume = mf_multiplier * df['Volume']
    
    # Calculate CMF as ratio of sums
    cmf = mf_volume.rolling(period).sum() / df['Volume'].rolling(period).sum()
    
    return cmf


def calculate_cmf_zscore(df: pd.DataFrame, 
                         cmf_period: int = 20, 
                         zscore_window: int = 20) -> pd.Series:
    """
    Calculate CMF and convert to z-score for normalized cross-stock comparison.
    
    Z-score normalization allows consistent thresholds across stocks with
    different volatility characteristics. This is the primary volume flow
    indicator for the system.
    
    Combines Item #10 (CMF) with Item #12 (Z-Score Normalization).
    
    Args:
        df (pd.DataFrame): DataFrame with OHLCV columns
        cmf_period (int): Period for CMF calculation (default: 20)
        zscore_window (int): Rolling window for z-score calculation (default: 20)
        
    Returns:
        pd.Series: CMF z-score values
        
    Example:
        >>> df['CMF_Z'] = calculate_cmf_zscore(df, cmf_period=20, zscore_window=20)
        >>> # CMF_Z > 1.0 indicates strong buying pressure (> 1 std dev)
        >>> # CMF_Z < 0 indicates selling pressure (momentum failure)
    """
    # Calculate base CMF
    cmf = calculate_cmf(df, period=cmf_period)
    
    # Calculate rolling z-score with improved handling of low variance
    rolling_mean = cmf.rolling(zscore_window).mean()
    rolling_std = cmf.rolling(zscore_window).std()
    
    # Handle zero or very low std dev more gracefully
    # Use a small epsilon instead of NaN to prevent calculation failures
    # This ensures z-scores are calculated even in low-variance periods
    epsilon = 1e-10
    rolling_std = rolling_std.replace(0, epsilon)
    rolling_std = rolling_std.fillna(epsilon)
    
    # Calculate z-score
    cmf_zscore = (cmf - rolling_mean) / rolling_std
    
    # Handle any remaining inf values by clipping to reasonable range
    cmf_zscore = cmf_zscore.replace([np.inf, -np.inf], 0)
    
    return cmf_zscore


def calculate_volume_surprise(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    Calculate volume surprise (ratio of current volume to average).
    
    Also known as "relative volume" - measures how unusual current volume is
    compared to recent average.
    
    Args:
        df (pd.DataFrame): DataFrame with Volume column
        window (int): Rolling window size (default: 20)
        
    Returns:
        pd.Series: Volume surprise ratio
        
    Example:
        >>> df['Relative_Volume'] = calculate_volume_surprise(df, window=20)
        >>> # Relative_Volume > 2.0 indicates significant volume spike
    """
    avg_volume = df['Volume'].rolling(window=window).mean()
    volume_surprise = df['Volume'] / avg_volume
    
    return volume_surprise


def detect_event_days(df: pd.DataFrame, 
                     atr_multiplier: float = 2.5, 
                     volume_threshold: float = 2.0) -> pd.Series:
    """
    Detect event-driven spike days (earnings, news, macro shocks).
    
    Event days are characterized by:
    - Range Spike: TR > atr_multiplier * ATR20
    - Volume Spike: Relative_Volume > volume_threshold
    
    This filter prevents false accumulation signals during extreme volatility
    events like earnings announcements or macro shock days.
    
    This is the core implementation of Item #3: News/Event Spike Filter.
    
    Args:
        df (pd.DataFrame): DataFrame with TR, ATR20, Relative_Volume columns
        atr_multiplier (float): Multiplier for ATR threshold (default: 2.5)
        volume_threshold (float): Volume multiplier threshold (default: 2.0)
        
    Returns:
        pd.Series: Boolean series indicating event days
        
    Example:
        >>> df['Event_Day'] = detect_event_days(df, atr_multiplier=2.5, volume_threshold=2.0)
        >>> # Filter entry signals: df['Strong_Buy'] & ~df['Event_Day']
    """
    # Require both conditions for an event day
    range_spike = df['TR'] > (atr_multiplier * df['ATR20'])
    volume_spike = df['Relative_Volume'] > volume_threshold
    
    # Event day = both range spike AND volume spike
    event_day = range_spike & volume_spike
    
    return event_day


def calculate_volume_trend(df: pd.DataFrame, 
                          short_window: int = 5,
                          long_window: int = 20) -> pd.Series:
    """
    Calculate volume trend using dual moving averages.
    
    Positive trend indicates increasing volume (accumulation phase),
    negative trend indicates decreasing volume (distribution or exhaustion).
    
    Args:
        df (pd.DataFrame): DataFrame with Volume column
        short_window (int): Short MA period (default: 5)
        long_window (int): Long MA period (default: 20)
        
    Returns:
        pd.Series: Volume trend (-1 to +1, normalized)
        
    Example:
        >>> df['Volume_Trend'] = calculate_volume_trend(df, short_window=5, long_window=20)
        >>> # Positive trend with rising price = healthy accumulation
    """
    short_ma = df['Volume'].rolling(short_window).mean()
    long_ma = df['Volume'].rolling(long_window).mean()
    
    # Calculate ratio and normalize to -1 to +1 range
    ratio = (short_ma / long_ma) - 1.0
    volume_trend = np.clip(ratio * 2, -1, 1)  # Scale and clip
    
    return volume_trend


def detect_volume_divergence(df: pd.DataFrame, 
                             price_window: int = 10,
                             volume_window: int = 10) -> Tuple[pd.Series, pd.Series]:
    """
    Detect bullish and bearish volume-price divergences.
    
    Bullish divergence: Price declining but volume flow (CMF) rising
    Bearish divergence: Price rising but volume flow (CMF) declining
    
    Args:
        df (pd.DataFrame): DataFrame with Close, CMF_20 columns
        price_window (int): Window for price trend detection
        volume_window (int): Window for volume flow trend detection
        
    Returns:
        Tuple[pd.Series, pd.Series]: (bullish_divergence, bearish_divergence) boolean series
        
    Example:
        >>> bull_div, bear_div = detect_volume_divergence(df)
        >>> # Bullish divergence at support = strong buy signal
    """
    # Calculate price trend
    price_ma = df['Close'].rolling(price_window).mean()
    price_rising = df['Close'] > df['Close'].shift(price_window)
    price_falling = df['Close'] < df['Close'].shift(price_window)
    
    # Calculate CMF trend (volume flow)
    cmf_rising = df['CMF_20'] > df['CMF_20'].shift(volume_window)
    cmf_falling = df['CMF_20'] < df['CMF_20'].shift(volume_window)
    
    # Bullish divergence: Price falling but volume flow rising
    bullish_divergence = price_falling & cmf_rising
    
    # Bearish divergence: Price rising but volume flow falling
    bearish_divergence = price_rising & cmf_falling
    
    return bullish_divergence, bearish_divergence


def calculate_volume_profile(df: pd.DataFrame, 
                             price_bins: int = 20,
                             lookback: int = 60) -> pd.DataFrame:
    """
    Calculate volume profile (volume distribution across price levels).
    
    Identifies price levels with highest trading activity, which often
    act as support/resistance.
    
    Args:
        df (pd.DataFrame): DataFrame with Close and Volume columns
        price_bins (int): Number of price bins (default: 20)
        lookback (int): Lookback period in bars (default: 60)
        
    Returns:
        pd.DataFrame: Volume profile with columns [price_level, volume, volume_pct]
        
    Example:
        >>> profile = calculate_volume_profile(df, price_bins=20, lookback=60)
        >>> # Find price levels with highest volume (POC - Point of Control)
        >>> poc_price = profile.loc[profile['volume'].idxmax(), 'price_level']
    """
    # Get recent data
    recent_df = df.tail(lookback)
    
    # Create price bins
    price_min = recent_df['Close'].min()
    price_max = recent_df['Close'].max()
    bins = np.linspace(price_min, price_max, price_bins + 1)
    
    # Assign each bar to a price bin and sum volume
    recent_df = recent_df.copy()
    recent_df['price_bin'] = pd.cut(recent_df['Close'], bins=bins, labels=False)
    
    # Calculate volume per bin
    volume_per_bin = recent_df.groupby('price_bin')['Volume'].sum()
    
    # Create result dataframe
    bin_centers = (bins[:-1] + bins[1:]) / 2
    
    profile = pd.DataFrame({
        'price_level': bin_centers,
        'volume': volume_per_bin.values,
        'volume_pct': (volume_per_bin.values / volume_per_bin.sum()) * 100
    })
    
    return profile


def calculate_volume_weighted_momentum(df: pd.DataFrame, 
                                       period: int = 10) -> pd.Series:
    """
    Calculate momentum indicator weighted by volume.
    
    Gives more weight to price moves that occur on high volume,
    making it more reliable than simple price momentum.
    
    Args:
        df (pd.DataFrame): DataFrame with Close and Volume columns
        period (int): Lookback period (default: 10)
        
    Returns:
        pd.Series: Volume-weighted momentum values
        
    Example:
        >>> df['VW_Momentum'] = calculate_volume_weighted_momentum(df, period=10)
        >>> # Positive VW_Momentum with high volume = strong trend
    """
    # Calculate price changes
    price_change = df['Close'].pct_change()
    
    # Weight by normalized volume
    avg_volume = df['Volume'].rolling(period).mean()
    volume_weight = df['Volume'] / avg_volume
    
    # Volume-weighted price change
    weighted_change = price_change * volume_weight
    
    # Rolling sum for momentum
    vw_momentum = weighted_change.rolling(period).sum()
    
    return vw_momentum


def detect_climax_volume(df: pd.DataFrame,
                        volume_threshold: float = 3.0,
                        price_threshold: float = 0.02) -> Tuple[pd.Series, pd.Series]:
    """
    Detect buying and selling climax events.
    
    Climax volume occurs when very high volume accompanies a sharp price move,
    often marking temporary exhaustion of trend.
    
    Args:
        df (pd.DataFrame): DataFrame with Close, Volume, and Relative_Volume columns
        volume_threshold (float): Volume multiplier for climax (default: 3.0x)
        price_threshold (float): Minimum price change percentage (default: 2%)
        
    Returns:
        Tuple[pd.Series, pd.Series]: (buying_climax, selling_climax) boolean series
        
    Example:
        >>> buy_climax, sell_climax = detect_climax_volume(df)
        >>> # Buying climax often marks short-term top
        >>> # Selling climax often marks short-term bottom
    """
    # Calculate price change
    price_change_pct = df['Close'].pct_change()
    
    # Climax conditions
    high_volume = df['Relative_Volume'] > volume_threshold
    
    buying_climax = high_volume & (price_change_pct > price_threshold)
    selling_climax = high_volume & (price_change_pct < -price_threshold)
    
    return buying_climax, selling_climax


def calculate_volume_efficiency(df: pd.DataFrame, 
                                period: int = 20) -> pd.Series:
    """
    Calculate volume efficiency ratio.
    
    Measures how much price movement is achieved per unit of volume.
    Higher efficiency = stronger directional conviction.
    
    Args:
        df (pd.DataFrame): DataFrame with Close and Volume columns
        period (int): Rolling period (default: 20)
        
    Returns:
        pd.Series: Volume efficiency values
        
    Example:
        >>> df['Volume_Efficiency'] = calculate_volume_efficiency(df, period=20)
        >>> # High efficiency = price moving easily in one direction
        >>> # Low efficiency = choppy, indecisive trading
    """
    # Calculate price movement
    price_movement = abs(df['Close'] - df['Close'].shift(period))
    
    # Calculate total volume
    total_volume = df['Volume'].rolling(period).sum()
    
    # Efficiency = price movement per unit volume
    efficiency = price_movement / total_volume
    
    # Normalize by current price for cross-stock comparison
    efficiency_normalized = (efficiency / df['Close']) * 1000000  # Scale up for readability
    
    return efficiency_normalized
