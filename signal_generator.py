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
    
    Args:
        df: DataFrame with required columns: Accumulation_Score, Near_Support,
            Above_VWAP, Relative_Volume
            
    Returns:
        Boolean Series indicating strong buy signals
    """
    return (
        (df['Accumulation_Score'] >= 7) & 
        df['Near_Support'] & 
        df['Above_VWAP'] & 
        (df['Relative_Volume'] >= 1.2) &
        (df['Relative_Volume'] <= 3.0)
    )


def generate_moderate_buy_signals(df: pd.DataFrame) -> pd.Series:
    """
    Detect moderate buy opportunities.
    
    Criteria:
    - Moderate accumulation score (5-7)
    - A/D rising OR OBV trending up
    - Above VWAP
    - Not already a strong buy signal
    
    Args:
        df: DataFrame with required columns: Accumulation_Score, AD_Rising,
            OBV_Trend, Above_VWAP, Strong_Buy
            
    Returns:
        Boolean Series indicating moderate buy signals
    """
    moderate_conditions = (
        (df['Accumulation_Score'] >= 5) & 
        (df['Accumulation_Score'] < 7) &
        (df['AD_Rising'] | df['OBV_Trend']) &
        df['Above_VWAP']
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
    
    Args:
        df: DataFrame with required columns: Accumulation_Score, Relative_Volume,
            AD_Rising, Price_Rising, Strong_Buy, Moderate_Buy
            
    Returns:
        Boolean Series indicating stealth accumulation signals
    """
    stealth_conditions = (
        (df['Accumulation_Score'] >= 6) &
        (df['Relative_Volume'] < 1.3) &
        (df['AD_Rising'] & ~df['Price_Rising'])
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
    
    Args:
        df: DataFrame with required columns: Accumulation_Score, Near_Support,
            Volume_Spike, Above_VWAP, AD_Rising, OBV_Trend
            
    Returns:
        Boolean Series indicating confluence signals
    """
    return (
        (df['Accumulation_Score'] >= 6) &
        df['Near_Support'] &
        df['Volume_Spike'] &
        df['Above_VWAP'] &
        (df['AD_Rising'] & df['OBV_Trend'])
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
    
    Args:
        df: DataFrame with required columns: Accumulation_Score, Relative_Volume,
            Close, Above_VWAP, Strong_Buy
            
    Returns:
        Boolean Series indicating volume breakout signals
    """
    breakout_conditions = (
        (df['Accumulation_Score'] >= 5) &
        (df['Relative_Volume'] > 2.5) &
        (df['Close'] > df['Close'].shift(1)) &
        df['Above_VWAP']
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
        (df['Close'] < df['VWAP']) &
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
