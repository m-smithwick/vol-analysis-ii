"""
Swing structure analysis module for pivot detection and support/resistance levels.

This module handles:
- Pivot high/low detection
- Swing-based support/resistance calculation
- Proximity analysis to swing levels
- Volatility-aware distance measurements

Part of Item #7: Refactor/Integration Plan
"""

import pandas as pd
import numpy as np
from typing import Tuple


def find_pivots(df: pd.DataFrame, lookback: int = 3) -> Tuple[pd.Series, pd.Series]:
    """
    Detect swing pivot highs and lows in price data.
    
    A pivot low at index i is where Low[i] is lower than the previous N lows 
    and the next N lows. A pivot high is the inverse for highs.
    
    Args:
        df (pd.DataFrame): DataFrame with High and Low columns
        lookback (int): Number of bars to look back/forward for confirmation
        
    Returns:
        Tuple[pd.Series, pd.Series]: (pivot_lows, pivot_highs) boolean series
        
    Example:
        >>> pivot_lows, pivot_highs = find_pivots(df, lookback=3)
        >>> # Use pivots to anchor VWAP or calculate swing levels
    """
    pivot_lows = pd.Series(False, index=df.index)
    pivot_highs = pd.Series(False, index=df.index)
    
    # Need at least 2*lookback+1 bars to identify a pivot
    if len(df) < (2 * lookback + 1):
        return pivot_lows, pivot_highs
    
    # Check each potential pivot point (skip first and last 'lookback' bars)
    for i in range(lookback, len(df) - lookback):
        current_low = df['Low'].iloc[i]
        current_high = df['High'].iloc[i]
        
        # Check for pivot low: current bar's low is lower than lookback bars before and after
        prev_lows = df['Low'].iloc[i-lookback:i]
        next_lows = df['Low'].iloc[i+1:i+lookback+1]
        
        if (current_low < prev_lows.min()) and (current_low < next_lows.min()):
            pivot_lows.iloc[i] = True
        
        # Check for pivot high: current bar's high is higher than lookback bars before and after
        prev_highs = df['High'].iloc[i-lookback:i]
        next_highs = df['High'].iloc[i+1:i+lookback+1]
        
        if (current_high > prev_highs.max()) and (current_high > next_highs.max()):
            pivot_highs.iloc[i] = True
    
    return pivot_lows, pivot_highs


def calculate_swing_levels(df: pd.DataFrame, lookback: int = 3) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate support and resistance levels based on swing structure.
    
    Uses actual pivot lows and highs to define meaningful support/resistance levels
    instead of rolling min/max which can give false signals during crashes or trends.
    
    This is the core implementation of Item #2: Support/Resistance From Swing Structure.
    
    Args:
        df (pd.DataFrame): DataFrame with High and Low columns
        lookback (int): Lookback period for pivot detection
        
    Returns:
        Tuple[pd.Series, pd.Series]: (Recent_Swing_Low, Recent_Swing_High) forward-filled series
        
    Example:
        >>> swing_low, swing_high = calculate_swing_levels(df, lookback=3)
        >>> df['Recent_Swing_Low'] = swing_low
        >>> df['Recent_Swing_High'] = swing_high
    """
    # Find pivot points
    pivot_lows, pivot_highs = find_pivots(df, lookback=lookback)
    
    # Initialize result series
    recent_swing_low = pd.Series(np.nan, index=df.index)
    recent_swing_high = pd.Series(np.nan, index=df.index)
    
    # Forward fill swing levels from each pivot point
    for i in range(len(df)):
        if pivot_lows.iloc[i]:
            # New swing low found - update from this point forward
            recent_swing_low.iloc[i:] = df['Low'].iloc[i]
        
        if pivot_highs.iloc[i]:
            # New swing high found - update from this point forward  
            recent_swing_high.iloc[i:] = df['High'].iloc[i]
    
    # Forward fill any remaining NaN values
    recent_swing_low = recent_swing_low.ffill()
    recent_swing_high = recent_swing_high.ffill()
    
    # If still NaN at the beginning (no pivots found in early data), 
    # use the actual lows/highs from the early period
    if recent_swing_low.isna().any():
        first_valid_low = df['Low'].iloc[0]
        recent_swing_low = recent_swing_low.fillna(first_valid_low)
    
    if recent_swing_high.isna().any():
        first_valid_high = df['High'].iloc[0] 
        recent_swing_high = recent_swing_high.fillna(first_valid_high)
    
    return recent_swing_low, recent_swing_high


def calculate_swing_proximity_signals(df: pd.DataFrame, 
                                      recent_swing_low: pd.Series, 
                                      recent_swing_high: pd.Series,
                                      atr_series: pd.Series = None,
                                      use_volatility_aware: bool = True) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate swing-based proximity and breakdown signals.
    
    Enhanced with volatility-aware proximity from Item #2 (tweaks.txt integration).
    Uses ATR-normalized distance for adaptive thresholds across different volatility regimes.
    
    Args:
        df (pd.DataFrame): DataFrame with Close column
        recent_swing_low (pd.Series): Recent swing low levels
        recent_swing_high (pd.Series): Recent swing high levels
        atr_series (pd.Series, optional): ATR values for volatility-aware proximity
        use_volatility_aware (bool): Whether to use ATR-based proximity (default: True)
        
    Returns:
        Tuple[pd.Series, pd.Series, pd.Series]: (Near_Support, Lost_Support, Near_Resistance)
        
    Example:
        >>> near_sup, lost_sup, near_res = calculate_swing_proximity_signals(
        ...     df, swing_low, swing_high, df['ATR20'], use_volatility_aware=True
        ... )
    """
    if use_volatility_aware and atr_series is not None:
        # Volatility-aware proximity using ATR normalization
        # From tweaks.txt: Within 1 ATR of support = "near support"
        support_proximity = (df['Close'] - recent_swing_low) / atr_series
        resistance_proximity = (recent_swing_high - df['Close']) / atr_series
        
        # Near support: within 1 ATR above swing low
        near_support = support_proximity <= 1.0
        
        # Lost support: broke below swing low by more than 0.5 ATR
        lost_support = support_proximity < -0.5
        
        # Near resistance: within 1 ATR below swing high
        near_resistance = resistance_proximity <= 1.0
        
        # Add proximity scores to DataFrame for graduated scoring (optional)
        if 'Support_Proximity' not in df.columns:
            df['Support_Proximity'] = support_proximity
        if 'Resistance_Proximity' not in df.columns:
            df['Resistance_Proximity'] = resistance_proximity
        
    else:
        # Legacy fixed percentage proximity (5%)
        near_support = df['Close'] <= recent_swing_low * 1.05
        lost_support = df['Close'] < recent_swing_low
        near_resistance = df['Close'] >= recent_swing_high * 0.95
    
    return near_support, lost_support, near_resistance


def calculate_support_proximity_score(df: pd.DataFrame, 
                                      recent_swing_low: pd.Series,
                                      atr_series: pd.Series) -> pd.Series:
    """
    Calculate normalized support proximity score for use in signal generation.
    
    Returns a graduated score based on how close price is to support level,
    normalized by ATR for cross-stock consistency.
    
    Args:
        df (pd.DataFrame): DataFrame with Close column
        recent_swing_low (pd.Series): Recent swing low levels
        atr_series (pd.Series): ATR values for normalization
        
    Returns:
        pd.Series: Support proximity score (higher = closer to support)
        
    Example:
        >>> prox_score = calculate_support_proximity_score(df, swing_low, df['ATR20'])
        >>> # Use in scoring: score += (prox_score <= 1.0) * weight
    """
    support_proximity = (df['Close'] - recent_swing_low) / atr_series
    return support_proximity


def identify_swing_failure_patterns(df: pd.DataFrame,
                                    recent_swing_low: pd.Series,
                                    recent_swing_high: pd.Series,
                                    lookback: int = 5) -> Tuple[pd.Series, pd.Series]:
    """
    Identify swing failure patterns (failed breakouts/breakdowns).
    
    A swing failure occurs when price briefly breaks a level but quickly reverses,
    suggesting the level is being defended by strong hands.
    
    Args:
        df (pd.DataFrame): DataFrame with OHLC columns
        recent_swing_low (pd.Series): Recent swing low levels
        recent_swing_high (pd.Series): Recent swing high levels
        lookback (int): Bars to look back for failure pattern
        
    Returns:
        Tuple[pd.Series, pd.Series]: (failed_breakdown, failed_breakout) boolean series
        
    Example:
        >>> failed_bd, failed_bo = identify_swing_failure_patterns(df, swing_low, swing_high)
        >>> # Use as bullish signal when breakdown fails at support
    """
    failed_breakdown = pd.Series(False, index=df.index)
    failed_breakout = pd.Series(False, index=df.index)
    
    for i in range(lookback, len(df)):
        # Check for failed breakdown (bullish reversal)
        # Price went below support in last N bars but is now back above
        recent_lows = df['Low'].iloc[i-lookback:i]
        recent_closes = df['Close'].iloc[i-lookback:i]
        support_level = recent_swing_low.iloc[i]
        
        if (recent_lows.min() < support_level and 
            df['Close'].iloc[i] > support_level):
            failed_breakdown.iloc[i] = True
        
        # Check for failed breakout (bearish reversal)
        # Price went above resistance in last N bars but is now back below
        recent_highs = df['High'].iloc[i-lookback:i]
        resistance_level = recent_swing_high.iloc[i]
        
        if (recent_highs.max() > resistance_level and 
            df['Close'].iloc[i] < resistance_level):
            failed_breakout.iloc[i] = True
    
    return failed_breakdown, failed_breakout


def calculate_swing_strength(pivot_lows: pd.Series, 
                             pivot_highs: pd.Series,
                             df: pd.DataFrame,
                             volume_threshold: float = 1.5) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate strength of swing pivots based on volume and price action.
    
    Stronger pivots (with high volume) are more likely to act as significant
    support/resistance levels in the future.
    
    Args:
        pivot_lows (pd.Series): Boolean series of pivot lows
        pivot_highs (pd.Series): Boolean series of pivot highs
        df (pd.DataFrame): DataFrame with Volume and Close columns
        volume_threshold (float): Volume multiplier threshold for "strong" pivots
        
    Returns:
        Tuple[pd.Series, pd.Series]: (low_strength, high_strength) scores (0-1 scale)
        
    Example:
        >>> pivot_lows, pivot_highs = find_pivots(df)
        >>> low_str, high_str = calculate_swing_strength(pivot_lows, pivot_highs, df)
        >>> # Use strongest pivots for key support/resistance levels
    """
    avg_volume = df['Volume'].rolling(20).mean()
    relative_volume = df['Volume'] / avg_volume
    
    low_strength = pd.Series(0.0, index=df.index)
    high_strength = pd.Series(0.0, index=df.index)
    
    # Calculate strength at each pivot
    for i in range(len(df)):
        if pivot_lows.iloc[i]:
            # Strength based on volume and price range
            vol_score = min(relative_volume.iloc[i] / volume_threshold, 1.0)
            
            # Look at reversal magnitude
            if i >= 3:
                prior_low = df['Low'].iloc[i-3:i].min()
                reversal_pct = (df['Close'].iloc[i] - prior_low) / prior_low
                reversal_score = min(abs(reversal_pct) * 10, 1.0)
            else:
                reversal_score = 0.5
            
            low_strength.iloc[i] = (vol_score + reversal_score) / 2
        
        if pivot_highs.iloc[i]:
            # Similar calculation for highs
            vol_score = min(relative_volume.iloc[i] / volume_threshold, 1.0)
            
            if i >= 3:
                prior_high = df['High'].iloc[i-3:i].max()
                reversal_pct = (prior_high - df['Close'].iloc[i]) / prior_high
                reversal_score = min(abs(reversal_pct) * 10, 1.0)
            else:
                reversal_score = 0.5
            
            high_strength.iloc[i] = (vol_score + reversal_score) / 2
    
    return low_strength, high_strength
