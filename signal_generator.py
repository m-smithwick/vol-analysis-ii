"""
Signal Generation Module for Volume Analysis

This module contains all buy/sell signal detection logic, including:
- Accumulation scoring
- Exit scoring  
- Entry signal detection (Strong Buy, Moderate Buy, Stealth, etc.)
- Exit signal detection (Profit Taking, Distribution Warning, Sell, etc.)

All functions operate on pandas DataFrames with OHLCV data and technical indicators.
"""

import pandas as pd
import numpy as np
from typing import Tuple


def calculate_accumulation_score(df: pd.DataFrame) -> pd.Series:
    """
    Calculate accumulation confidence score (0-10 scale).
    
    Analyzes multiple factors to determine accumulation strength:
    - A/D divergence (price down, A/D up)
    - OBV divergence (price down, OBV up)
    - Volume spikes
    - Price position relative to VWAP
    - Proximity to support levels
    
    Args:
        df: DataFrame with required columns: AD_Rising, Price_Rising, OBV_Trend,
            Price_Trend, Volume_Spike, Above_VWAP, Near_Support
            
    Returns:
        Series with accumulation scores (0-10 scale)
    """
    score = pd.Series(0, index=df.index)
    
    # A/D divergence: A/D rising while price not rising (2 points)
    score = score + (df['AD_Rising'] & ~df['Price_Rising']).astype(int) * 2
    
    # OBV divergence: OBV trending up while price not trending up (2 points)
    score = score + (df['OBV_Trend'] & ~df['Price_Trend']).astype(int) * 2
    
    # Volume spike present (1 point)
    score = score + df['Volume_Spike'].astype(int) * 1
    
    # Price above VWAP (1 point)
    score = score + df['Above_VWAP'].astype(int) * 1
    
    # Price near support level (1 point)
    score = score + df['Near_Support'].astype(int) * 1
    
    # Normalize to 0-10 scale (max raw score is 7)
    score = np.clip(score * 10 / 7, 0, 10)
    
    return score


def calculate_exit_score(df: pd.DataFrame) -> pd.Series:
    """
    Calculate exit urgency score (1-10 scale).
    
    Analyzes multiple risk factors to determine exit urgency:
    - Distribution phase and trend factors (0-4 points)
    - Volume and momentum factors (0-3 points)
    - Technical indicator factors (0-3 points)
    
    Args:
        df: DataFrame with required columns: Phase, Above_VWAP, Close, Support_Level,
            Relative_Volume, Volume, AD_Line, AD_MA, OBV, OBV_MA, Accumulation_Score
            
    Returns:
        Series with exit scores (1-10 scale, minimum 1)
    """
    score = pd.Series(0.0, index=df.index)
    
    # Distribution and trend factors (0-4 points)
    score = score + (df['Phase'] == 'Distribution').astype(float) * 2  # Distribution phase
    score = score + (~df['Above_VWAP']).astype(float) * 1.5  # Below VWAP
    score = score + (df['Close'] < df['Support_Level']).astype(float) * 2  # Below support
    score = score + (df['Close'] < df['Close'].rolling(10).mean()).astype(float) * 0.5  # Below 10-day MA
    
    # Volume and momentum factors (0-3 points)
    score = score + (df['Relative_Volume'] > 2.5).astype(float) * 1.5  # Very high volume
    score = score + (df['Relative_Volume'] > 1.8).astype(float) * 1  # High volume
    score = score + (df['Volume'] < df['Volume'].shift(3)).astype(float) * 0.5  # Declining volume trend
    
    # Technical indicator factors (0-3 points)
    score = score + (df['AD_Line'] < df['AD_MA']).astype(float) * 1  # A/D line declining
    score = score + (df['OBV'] < df['OBV_MA']).astype(float) * 1  # OBV declining
    score = score + (df['Accumulation_Score'] < 2).astype(float) * 1  # Very low accumulation
    
    # Normalize to 1-10 scale (minimum 1 for any position)
    score = np.clip(score * 10 / 10, 1, 10)
    
    return score


def generate_strong_buy_signals(df: pd.DataFrame) -> pd.Series:
    """
    Detect strong buy opportunities.
    
    Criteria:
    - High accumulation score (≥7)
    - Near support level
    - Above VWAP
    - Healthy volume (1.2x-3.0x average)
    - Not an event day (ATR spike filter)
    
    Args:
        df: DataFrame with required columns: Accumulation_Score, Near_Support,
            Above_VWAP, Relative_Volume, Event_Day
            
    Returns:
        Boolean Series indicating strong buy signals
    """
    # Check if Event_Day column exists for filtering
    event_day_filter = ~df['Event_Day'] if 'Event_Day' in df.columns else True
    
    return (
        (df['Accumulation_Score'] >= 7) & 
        df['Near_Support'] & 
        df['Above_VWAP'] & 
        (df['Relative_Volume'] >= 1.2) &
        (df['Relative_Volume'] <= 3.0) &
        event_day_filter
    )


def generate_moderate_buy_signals(df: pd.DataFrame) -> pd.Series:
    """
    Detect moderate buy opportunities.
    
    Criteria:
    - Moderate accumulation score (5-7)
    - A/D rising OR OBV trending up
    - Above VWAP
    - Not already a strong buy signal
    - Not an event day (ATR spike filter)
    
    Args:
        df: DataFrame with required columns: Accumulation_Score, AD_Rising,
            OBV_Trend, Above_VWAP, Strong_Buy, Event_Day
            
    Returns:
        Boolean Series indicating moderate buy signals
    """
    # Check if Event_Day column exists for filtering
    event_day_filter = ~df['Event_Day'] if 'Event_Day' in df.columns else True
    
    moderate_conditions = (
        (df['Accumulation_Score'] >= 5) & 
        (df['Accumulation_Score'] < 7) &
        (df['AD_Rising'] | df['OBV_Trend']) &
        df['Above_VWAP'] &
        event_day_filter
    )
    
    # Exclude strong buy signals
    if 'Strong_Buy' in df.columns:
        return moderate_conditions & ~df['Strong_Buy']
    else:
        return moderate_conditions


def generate_stealth_accumulation_signals(df: pd.DataFrame) -> pd.Series:
    """
    Detect stealth accumulation patterns.
    
    Criteria:
    - High accumulation score (≥6)
    - Low/normal volume (<1.3x average)
    - A/D rising while price not rising (divergence)
    - Not already a strong or moderate buy signal
    - Not an event day (ATR spike filter)
    
    Args:
        df: DataFrame with required columns: Accumulation_Score, Relative_Volume,
            AD_Rising, Price_Rising, Strong_Buy, Moderate_Buy, Event_Day
            
    Returns:
        Boolean Series indicating stealth accumulation signals
    """
    # Check if Event_Day column exists for filtering
    event_day_filter = ~df['Event_Day'] if 'Event_Day' in df.columns else True
    
    stealth_conditions = (
        (df['Accumulation_Score'] >= 6) &
        (df['Relative_Volume'] < 1.3) &
        (df['AD_Rising'] & ~df['Price_Rising']) &
        event_day_filter
    )
    
    # Exclude other buy signals
    exclusions = pd.Series(False, index=df.index)
    if 'Strong_Buy' in df.columns:
        exclusions = exclusions | df['Strong_Buy']
    if 'Moderate_Buy' in df.columns:
        exclusions = exclusions | df['Moderate_Buy']
    
    return stealth_conditions & ~exclusions


def generate_confluence_signals(df: pd.DataFrame) -> pd.Series:
    """
    Detect multi-signal confluence.
    
    Criteria:
    - High accumulation score (≥6)
    - Near support level
    - Volume spike
    - Above VWAP
    - Both A/D and OBV trending up
    - Not an event day (ATR spike filter)
    
    Args:
        df: DataFrame with required columns: Accumulation_Score, Near_Support,
            Volume_Spike, Above_VWAP, AD_Rising, OBV_Trend, Event_Day
            
    Returns:
        Boolean Series indicating confluence signals
    """
    # Check if Event_Day column exists for filtering
    event_day_filter = ~df['Event_Day'] if 'Event_Day' in df.columns else True
    
    return (
        (df['Accumulation_Score'] >= 6) &
        df['Near_Support'] &
        df['Volume_Spike'] &
        df['Above_VWAP'] &
        (df['AD_Rising'] & df['OBV_Trend']) &
        event_day_filter
    )


def generate_volume_breakout_signals(df: pd.DataFrame) -> pd.Series:
    """
    Detect volume breakout patterns.
    
    Criteria:
    - Moderate accumulation score (≥5)
    - Very high volume (>2.5x average)
    - Price up on the day
    - Above VWAP
    - Not already a strong buy signal
    - Not an event day (ATR spike filter)
    
    Args:
        df: DataFrame with required columns: Accumulation_Score, Relative_Volume,
            Close, Above_VWAP, Strong_Buy, Event_Day
            
    Returns:
        Boolean Series indicating volume breakout signals
    """
    # Check if Event_Day column exists for filtering
    event_day_filter = ~df['Event_Day'] if 'Event_Day' in df.columns else True
    
    breakout_conditions = (
        (df['Accumulation_Score'] >= 5) &
        (df['Relative_Volume'] > 2.5) &
        (df['Close'] > df['Close'].shift(1)) &
        df['Above_VWAP'] &
        event_day_filter
    )
    
    # Exclude strong buy signals
    if 'Strong_Buy' in df.columns:
        return breakout_conditions & ~df['Strong_Buy']
    else:
        return breakout_conditions


def generate_profit_taking_signals(df: pd.DataFrame) -> pd.Series:
    """
    Detect profit taking opportunities.
    
    Criteria:
    - New highs (breaking 20-day max)
    - High volume (>1.8x average)
    - Still above VWAP
    - Accumulation waning (<4)
    - Price up on the day
    
    Args:
        df: DataFrame with required columns: Close, Relative_Volume, Above_VWAP,
            Accumulation_Score
            
    Returns:
        Boolean Series indicating profit taking signals
    """
    return (
        (df['Close'] > df['Close'].rolling(20).max().shift(1)) &
        (df['Relative_Volume'] > 1.8) &
        df['Above_VWAP'] &
        (df['Accumulation_Score'] < 4) &
        (df['Close'] > df['Close'].shift(1))
    )


def generate_distribution_warning_signals(df: pd.DataFrame) -> pd.Series:
    """
    Detect early distribution warnings.
    
    Criteria:
    - Distribution phase
    - Below VWAP
    - Above average volume (>1.3x)
    - Price declining over 3 days
    - A/D line declining
    - Not already a sell signal
    
    Args:
        df: DataFrame with required columns: Phase, Close, VWAP, Relative_Volume,
            AD_Line, AD_MA, Sell_Signal
            
    Returns:
        Boolean Series indicating distribution warning signals
    """
    warning_conditions = (
        (df['Phase'] == 'Distribution') &
        ~df['Above_VWAP'] &
        (df['Relative_Volume'] > 1.3) &
        (df['Close'] < df['Close'].shift(3)) &
        (df['AD_Line'] < df['AD_MA'])
    )
    
    # Exclude sell signals
    if 'Sell_Signal' in df.columns:
        return warning_conditions & ~df['Sell_Signal']
    else:
        return warning_conditions


def generate_sell_signals(df: pd.DataFrame) -> pd.Series:
    """
    Detect sell signal conditions.
    
    Criteria:
    - Distribution phase
    - Below VWAP
    - Above average volume (>1.5x)
    - Breaking support (within 2%)
    - A/D line declining
    - OBV declining
    
    Args:
        df: DataFrame with required columns: Phase, Above_VWAP, Relative_Volume,
            Close, Support_Level, AD_Line, AD_MA, OBV, OBV_MA
            
    Returns:
        Boolean Series indicating sell signals
    """
    return (
        (df['Phase'] == 'Distribution') &
        ~df['Above_VWAP'] &
        (df['Relative_Volume'] > 1.5) &
        (df['Close'] < df['Support_Level'] * 1.02) &
        (df['AD_Line'] < df['AD_MA']) &
        (df['OBV'] < df['OBV_MA'])
    )


def generate_momentum_exhaustion_signals(df: pd.DataFrame) -> pd.Series:
    """
    Detect momentum exhaustion patterns.
    
    Criteria:
    - Price still rising (vs 5 days ago)
    - Volume declining (<0.8x average)
    - Low accumulation score (<3)
    - Extended above MA (>3%)
    - Volume declining trend
    
    Args:
        df: DataFrame with required columns: Close, Relative_Volume,
            Accumulation_Score, Volume
            
    Returns:
        Boolean Series indicating momentum exhaustion signals
    """
    return (
        (df['Close'] > df['Close'].shift(5)) &
        (df['Relative_Volume'] < 0.8) &
        (df['Accumulation_Score'] < 3) &
        (df['Close'] > df['Close'].rolling(10).mean() * 1.03) &
        (df['Volume'] < df['Volume'].shift(3))
    )


def generate_stop_loss_signals(df: pd.DataFrame) -> pd.Series:
    """
    Detect stop loss trigger conditions.
    
    Criteria:
    - Below support level
    - High volume breakdown (>1.8x)
    - Below VWAP
    - Below 5-day MA by 3%
    - Price declining
    
    Args:
        df: DataFrame with required columns: Close, Support_Level, Relative_Volume,
            Above_VWAP
            
    Returns:
        Boolean Series indicating stop loss triggers
    """
    return (
        (df['Close'] < df['Support_Level']) &
        (df['Relative_Volume'] > 1.8) &
        ~df['Above_VWAP'] &
        (df['Close'] < df['Close'].rolling(5).mean() * 0.97) &
        (df['Close'] < df['Close'].shift(1))
    )


def generate_all_entry_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate all entry signals and add to DataFrame.
    
    This convenience function generates:
    - Accumulation Score
    - Strong Buy signals
    - Moderate Buy signals
    - Stealth Accumulation signals
    - Confluence signals
    - Volume Breakout signals
    
    Args:
        df: DataFrame with OHLCV data and technical indicators
        
    Returns:
        DataFrame with all entry signal columns added
    """
    df = df.copy()
    
    # Generate accumulation score first
    df['Accumulation_Score'] = calculate_accumulation_score(df)
    
    # Generate entry signals (order matters for exclusions)
    df['Strong_Buy'] = generate_strong_buy_signals(df)
    df['Moderate_Buy'] = generate_moderate_buy_signals(df)
    df['Stealth_Accumulation'] = generate_stealth_accumulation_signals(df)
    df['Confluence_Signal'] = generate_confluence_signals(df)
    df['Volume_Breakout'] = generate_volume_breakout_signals(df)
    
    return df


def generate_all_exit_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate all exit signals and add to DataFrame.
    
    This convenience function generates:
    - Exit Score
    - Profit Taking signals
    - Distribution Warning signals
    - Sell signals
    - Momentum Exhaustion signals
    - Stop Loss signals
    
    Args:
        df: DataFrame with OHLCV data and technical indicators
        
    Returns:
        DataFrame with all exit signal columns added
    """
    df = df.copy()
    
    # Generate exit score first
    df['Exit_Score'] = calculate_exit_score(df)
    
    # Generate exit signals (order matters for exclusions)
    df['Sell_Signal'] = generate_sell_signals(df)
    df['Profit_Taking'] = generate_profit_taking_signals(df)
    df['Distribution_Warning'] = generate_distribution_warning_signals(df)
    df['Momentum_Exhaustion'] = generate_momentum_exhaustion_signals(df)
    df['Stop_Loss'] = generate_stop_loss_signals(df)
    
    return df


def calculate_moderate_buy_score(df: pd.DataFrame) -> pd.Series:
    """
    Calculate Moderate Buy signal score (0-10 scale) for threshold optimization.
    
    Uses same logic as generate_moderate_buy_signals() but returns graduated scores
    instead of boolean flags. This enables empirical threshold optimization.
    
    Scoring Components:
    - Base accumulation score (0-7 points, normalized from calculate_accumulation_score)
    - A/D rising bonus (0-1.5 points)
    - OBV trending bonus (0-1.5 points) 
    - VWAP position bonus (0-1 point)
    
    Args:
        df: DataFrame with required columns: Accumulation_Score, AD_Rising,
            OBV_Trend, Above_VWAP, Event_Day
            
    Returns:
        Series with moderate buy scores (0-10 scale)
    """
    score = pd.Series(0.0, index=df.index)
    
    # Base: Use existing accumulation score as foundation (0-7 points)
    # Normalize from 0-10 scale to 0-7 to leave room for bonuses
    base_score = df['Accumulation_Score'] * 0.7  # Convert 10-scale to 7-scale
    score = score + base_score
    
    # A/D rising bonus (0-1.5 points)
    score = score + df['AD_Rising'].astype(float) * 1.5
    
    # OBV trending bonus (0-1.5 points)
    score = score + df['OBV_Trend'].astype(float) * 1.5
    
    # VWAP position bonus (0-1 point)
    score = score + df['Above_VWAP'].astype(float) * 1.0
    
    # Event day penalty (-2 points for ATR spikes)
    if 'Event_Day' in df.columns:
        score = score - df['Event_Day'].astype(float) * 2.0
    
    # Normalize to 0-10 scale and clip
    score = np.clip(score, 0, 10)
    
    return score


def calculate_profit_taking_score(df: pd.DataFrame) -> pd.Series:
    """
    Calculate Profit Taking signal score (0-10 scale) for threshold optimization.
    
    Uses same logic as generate_profit_taking_signals() but returns graduated scores
    instead of boolean flags.
    
    Scoring Components:
    - New highs bonus (0-3 points based on how new the high is)
    - High volume bonus (0-2.5 points based on volume ratio)
    - VWAP position bonus (0-1.5 points)
    - Waning accumulation bonus (0-2 points based on low accumulation)
    - Price momentum bonus (0-1 point)
    
    Args:
        df: DataFrame with required columns: Close, Relative_Volume, Above_VWAP,
            Accumulation_Score
            
    Returns:
        Series with profit taking scores (0-10 scale)
    """
    score = pd.Series(0.0, index=df.index)
    
    # New highs bonus (0-3 points based on how significant the breakout is)
    rolling_max_20 = df['Close'].rolling(20).max().shift(1)
    breakout_pct = ((df['Close'] - rolling_max_20) / rolling_max_20) * 100
    breakout_bonus = np.clip(breakout_pct * 0.3, 0, 3)  # Up to 3 points for 10%+ breakout
    score = score + breakout_bonus
    
    # High volume bonus (0-2.5 points based on volume ratio)
    volume_bonus = np.clip((df['Relative_Volume'] - 1.0) * 1.25, 0, 2.5)  # Max at 3x volume
    score = score + volume_bonus
    
    # VWAP position bonus (0-1.5 points)
    score = score + df['Above_VWAP'].astype(float) * 1.5
    
    # Waning accumulation bonus (0-2 points - higher score when accumulation is LOW)
    waning_bonus = np.clip((4 - df['Accumulation_Score']) * 0.5, 0, 2)
    score = score + waning_bonus
    
    # Price momentum bonus (0-1 point for up days)
    price_up = (df['Close'] > df['Close'].shift(1)).astype(float) * 1.0
    score = score + price_up
    
    # Normalize to 0-10 scale and clip
    score = np.clip(score, 0, 10)
    
    return score


def calculate_stealth_accumulation_score(df: pd.DataFrame) -> pd.Series:
    """
    Calculate Stealth Accumulation signal score (0-7 scale) for threshold optimization.
    
    Uses same logic as generate_stealth_accumulation_signals() but returns graduated scores.
    Note: Max score is 7 (not 10) to reflect this is a secondary strategy.
    
    Scoring Components:
    - High accumulation foundation (0-4 points from accumulation score ≥6)
    - Low volume bonus (0-1.5 points for volume <1.3x)
    - A/D divergence bonus (0-1.5 points for A/D up while price not up)
    
    Args:
        df: DataFrame with required columns: Accumulation_Score, Relative_Volume,
            AD_Rising, Price_Rising, Event_Day
            
    Returns:
        Series with stealth accumulation scores (0-7 scale)
    """
    score = pd.Series(0.0, index=df.index)
    
    # High accumulation foundation (0-4 points for scores ≥6)
    high_accumulation = (df['Accumulation_Score'] >= 6).astype(float)
    accumulation_strength = np.clip((df['Accumulation_Score'] - 6) * 0.8, 0, 4)
    score = score + high_accumulation * accumulation_strength
    
    # Low volume stealth bonus (0-1.5 points - higher score for lower volume)
    low_volume_bonus = np.clip((1.3 - df['Relative_Volume']) * 1.5, 0, 1.5)
    score = score + low_volume_bonus
    
    # A/D divergence bonus (0-1.5 points)
    divergence_bonus = (df['AD_Rising'] & ~df['Price_Rising']).astype(float) * 1.5
    score = score + divergence_bonus
    
    # Event day penalty (-1 point for ATR spikes)
    if 'Event_Day' in df.columns:
        score = score - df['Event_Day'].astype(float) * 1.0
    
    # Normalize to 0-7 scale (secondary strategy) and clip
    score = np.clip(score, 0, 7)
    
    return score


def generate_all_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate all entry and exit signals in one call.
    
    Convenience function that generates both entry and exit signals.
    
    Args:
        df: DataFrame with OHLCV data and technical indicators
        
    Returns:
        DataFrame with all signal columns added
    """
    df = generate_all_entry_signals(df)
    df = generate_all_exit_signals(df)
    
    return df
