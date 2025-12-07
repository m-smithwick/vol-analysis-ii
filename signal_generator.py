"""
Signal Generation Module for Volume Analysis

This module contains all buy/sell signal detection logic, including:
- Accumulation scoring
- Exit scoring  
- Entry signal detection (Strong Buy, Moderate Buy, Stealth, etc.)
- Exit signal detection (Profit Taking, Distribution Warning, Sell, etc.)

All functions operate on pandas DataFrames with OHLCV data and technical indicators.

Updated 2025-12-05: Simplified threshold system - individual signal thresholds from
configs are now the sole authority. No global filters applied.
"""

import pandas as pd
import numpy as np
from typing import Tuple


def calculate_accumulation_score(df: pd.DataFrame) -> pd.Series:
    """
    Calculate accumulation confidence score (0-10 scale) using z-scored features.
    
    ITEM #12: Feature Standardization - Uses z-scored features for consistent
    weighting across stocks with different volatility characteristics.
    
    Analyzes multiple factors to determine accumulation strength:
    - CMF z-score (volume flow - replaces A/D and OBV)
    - Volume z-score (standardized volume spike detection)
    - Price position relative to VWAP
    - Proximity to support levels
    
    Args:
        df: DataFrame with columns: CMF_Z, Volume_Z (or Volume_Spike), 
            Above_VWAP, Near_Support, TR_Z (optional for event penalty)
            
    Returns:
        Series with accumulation scores (0-10 scale)
    """
    score = pd.Series(5.0, index=df.index)  # Start at neutral (mid-scale)
    
    # CMF z-score contribution (weight 2.0, clamped to ±2σ)
    # Replaces both A/D and OBV divergence logic (was 4 points combined)
    if 'CMF_Z' in df.columns:
        cmf_contribution = np.clip(df['CMF_Z'], -2, +2) * 2.0
        score = score + cmf_contribution
    
    # Volume spike using z-score (1 point for z > +1σ)
    # Standardized approach replaces raw volume multiples
    if 'Volume_Z' in df.columns:
        volume_contrib = (df['Volume_Z'] > 1.0).astype(float) * 1.0
        score = score + volume_contrib
    elif 'Volume_Spike' in df.columns:
        # Fallback to legacy Volume_Spike if z-score not available
        score = score + df['Volume_Spike'].astype(float) * 1.0
    
    # Price above VWAP (1 point)
    if 'Above_VWAP' in df.columns:
        score = score + df['Above_VWAP'].astype(float) * 1.0
    
    # Price near support level (1 point)
    if 'Near_Support' in df.columns:
        score = score + df['Near_Support'].astype(float) * 1.0
    
    # Event penalty using z-scored True Range (subtract 1.5 points for z > +2σ)
    # Prevents signals during extreme volatility events
    if 'TR_Z' in df.columns and 'Volume_Z' in df.columns:
        event_penalty = ((df['TR_Z'] > 2.0) | (df['Volume_Z'] > 2.0)).astype(float) * 1.5
        score = score - event_penalty
    
    # Normalize to 0-10 scale and clip
    score = np.clip(score, 0, 10)
    
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
    score = score + (df['Close'] < df['Close'].rolling(10).mean()).fillna(False).astype(float) * 0.5  # Below 10-day MA
    
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


def generate_strong_buy_signals(df: pd.DataFrame, threshold: float = 7.0) -> pd.Series:
    """
    Detect strong buy opportunities.
    
    Criteria:
    - High accumulation score (≥threshold, default 7.0)
    - Near support level
    - Above VWAP
    - Healthy volume (1.2x-3.0x average)
    - Not an event day (ATR spike filter)
    
    Args:
        df: DataFrame with required columns: Accumulation_Score, Near_Support,
            Above_VWAP, Relative_Volume, Event_Day
        threshold: Accumulation score threshold (default: 7.0, configurable)
            
    Returns:
        Boolean Series indicating strong buy signals
    """
    # Check if Event_Day column exists for filtering
    event_day_filter = ~df['Event_Day'] if 'Event_Day' in df.columns else True
    
    return (
        (df['Accumulation_Score'] >= threshold) & 
        df['Near_Support'] & 
        df['Above_VWAP'] & 
        (df['Relative_Volume'] >= 1.2) &
        (df['Relative_Volume'] <= 3.0) &
        event_day_filter
    )


def generate_moderate_buy_signals(df: pd.DataFrame, threshold: float = 5.0) -> pd.Series:
    """
    Detect moderate buy opportunities during pullbacks in uptrends.
    
    NEW LOGIC (Nov 2025): Redesigned to catch pullbacks in uptrends with 
    accumulation building. Complementary to Stealth (catches before move) 
    and Strong Buy (catches breakouts).
    
    Criteria:
    - Accumulation score ≥threshold (default 5.0, configurable, no upper limit)
    - In pullback zone (below 5-day MA but above 20-day MA)
    - Volume normalizing (<1.5x average)
    - CMF positive (buying pressure returning)
    - Not an event day (ATR spike filter)
    - Not already a strong buy signal
    
    Args:
        df: DataFrame with required columns: Accumulation_Score, Close,
            Relative_Volume, CMF_Z, Strong_Buy, Event_Day
        threshold: Accumulation score threshold (default: 5.0, configurable)
            
    Returns:
        Boolean Series indicating moderate buy signals during pullbacks
    """
    # Check if Event_Day column exists for filtering
    event_day_filter = ~df['Event_Day'] if 'Event_Day' in df.columns else True
    
    # CMF z-score positive indicates buying pressure returning
    cmf_positive = df['CMF_Z'] > 0 if 'CMF_Z' in df.columns else True
    
    # Define pullback zone: below short-term MA but above long-term MA
    ma_5 = df['Close'].rolling(5).mean()
    ma_20 = df['Close'].rolling(20).mean()
    
    # Handle NaN values in boolean operations
    pullback_zone = (df['Close'] < ma_5).fillna(False) & (df['Close'] > ma_20).fillna(False)
    
    moderate_conditions = (
        (df['Accumulation_Score'] >= threshold) &  # Now configurable
        pullback_zone &                             # In pullback zone (key change)
        (df['Relative_Volume'] < 1.5) &             # Volume normalizing
        cmf_positive &                              # Buying pressure returning
        event_day_filter
    )
    
    # Exclude strong buy signals
    if 'Strong_Buy' in df.columns:
        return moderate_conditions & ~df['Strong_Buy']
    else:
        return moderate_conditions


def generate_stealth_accumulation_signals(df: pd.DataFrame) -> pd.Series:
    """
    ⚠️  DEPRECATED - DO NOT USE ⚠️
    
    ❌ SIGNAL FAILED OUT-OF-SAMPLE VALIDATION (2025-11-08) ❌
    
    This signal showed 53.2% win rate on 24-month training data but COLLAPSED to 
    22.7% win rate on 6-month out-of-sample test. Median return became NEGATIVE 
    (-7.65%). This is textbook overfitting.
    
    Status: FAILED VALIDATION - Do NOT trade this signal
    Action: Requires complete redesign and re-validation before use
    See: OUT_OF_SAMPLE_VALIDATION_REPORT.md for details
    
    ---
    
    Original criteria (now deprecated):
    - High accumulation score (≥6)
    - Low/normal volume (<1.3x average)
    - CMF positive while price not rising (divergence)
    - Not already a strong or moderate buy signal
    - Not an event day (ATR spike filter)
    
    Args:
        df: DataFrame with required columns: Accumulation_Score, Relative_Volume,
            CMF_Z, Price_Rising, Strong_Buy, Moderate_Buy, Event_Day
            
    Returns:
        Boolean Series indicating stealth accumulation signals (DEPRECATED - returns all False)
    """
    import warnings
    warnings.warn(
        "⚠️  Stealth Accumulation signal FAILED out-of-sample validation "
        "(22.7% win rate vs 53.2% expected). DO NOT USE until redesigned. "
        "See OUT_OF_SAMPLE_VALIDATION_REPORT.md",
        DeprecationWarning,
        stacklevel=2
    )
    # Check if Event_Day column exists for filtering
    event_day_filter = ~df['Event_Day'] if 'Event_Day' in df.columns else True
    
    # CMF positive while price not rising indicates stealth accumulation
    # (replaces A/D rising & ~Price_Rising divergence)
    if 'CMF_Z' in df.columns and 'Price_Rising' in df.columns:
        cmf_divergence = (df['CMF_Z'] > 0) & ~df['Price_Rising']
    else:
        cmf_divergence = True  # Default to allowing signal if columns missing
    
    stealth_conditions = (
        (df['Accumulation_Score'] >= 6) &
        (df['Relative_Volume'] < 1.3) &
        cmf_divergence &
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
    - Strong CMF (z-score > 1.0, indicating strong buying pressure)
    - Not an event day (ATR spike filter)
    
    Args:
        df: DataFrame with required columns: Accumulation_Score, Near_Support,
            Volume_Spike, Above_VWAP, CMF_Z, Event_Day
            
    Returns:
        Boolean Series indicating confluence signals
    """
    # Check if Event_Day column exists for filtering
    event_day_filter = ~df['Event_Day'] if 'Event_Day' in df.columns else True
    
    # Strong CMF (>1σ) replaces "both A/D and OBV trending up"
    strong_cmf = df['CMF_Z'] > 1.0 if 'CMF_Z' in df.columns else True
    
    return (
        (df['Accumulation_Score'] >= 6) &
        df['Near_Support'] &
        df['Volume_Spike'] &
        df['Above_VWAP'] &
        strong_cmf &
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
        (df['Close'] > df['Close'].rolling(20).max().shift(1)).fillna(False) &
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
        (df['Close'] > df['Close'].rolling(10).mean() * 1.03).fillna(False) &
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
        df (pd.DataFrame): DataFrame with required columns: Close, Support_Level, Relative_Volume,
            Above_VWAP
            
    Returns:
        pd.Series: Boolean Series indicating stop loss triggers
    """
    return (
        (df['Close'] < df['Support_Level']) &
        (df['Relative_Volume'] > 1.8) &
        ~df['Above_VWAP'] &
        (df['Close'] < df['Close'].rolling(5).mean() * 0.97).fillna(False) &
        (df['Close'] < df['Close'].shift(1))
    )


def generate_ma_crossdown_signals(
    df: pd.DataFrame,
    ma_period: int = 50,
    confirmation_days: int = 1,
    buffer_pct: float = 0.0
) -> pd.Series:
    """
    Detect moving average crossdown exit signals.
    
    This signal triggers when price crosses below a moving average, indicating
    a potential trend reversal or weakness. Designed to complement volume-based
    exits with trend structure confirmation.
    
    Criteria:
    - Close crosses below N-day moving average
    - Optional: Requires confirmation over multiple days
    - Optional: Buffer zone to reduce whipsaws
    
    Args:
        df (pd.DataFrame): DataFrame with Close prices
        ma_period (int): Number of days for moving average (default: 50)
            Common values: 20, 48, 50, 60, 200
            Use 48 to avoid crowd behavior at exact 50-day
        confirmation_days (int): Days below MA required to trigger (default: 1)
            1 = Immediate exit on crossdown
            2 = Conservative, requires 2 consecutive closes below MA
        buffer_pct (float): Buffer percentage below MA (default: 0.0)
            0.0 = No buffer, trigger at exact crossdown
            0.5 = Trigger when price < MA * 0.995 (0.5% below)
            Reduces whipsaws in choppy markets
            
    Returns:
        pd.Series: Boolean Series indicating MA crossdown signals
        
    Examples:
        >>> # Simple 50-day MA crossdown (immediate)
        >>> signals = generate_ma_crossdown_signals(df, ma_period=50, confirmation_days=1)
        
        >>> # Conservative 48-day MA with 2-day confirmation
        >>> signals = generate_ma_crossdown_signals(df, ma_period=48, confirmation_days=2)
        
        >>> # 50-day MA with 0.5% buffer to reduce whipsaws
        >>> signals = generate_ma_crossdown_signals(df, ma_period=50, buffer_pct=0.5)
    """
    # Calculate moving average
    ma = df['Close'].rolling(window=ma_period).mean()
    
    # Apply buffer if specified (price must be X% below MA to trigger)
    threshold = ma * (1 - buffer_pct / 100)
    
    # Detect when price is below MA (with buffer)
    below_ma = df['Close'] < threshold
    
    # Apply confirmation requirement
    if confirmation_days == 1:
        # Immediate crossdown - trigger on first close below MA
        # Previous bar was above MA, current bar is below
        prev_above_ma = df['Close'].shift(1) >= ma.shift(1)
        crossdown = below_ma & prev_above_ma
        return crossdown
    
    elif confirmation_days == 2:
        # Two-day confirmation - require 2 consecutive closes below MA
        # Current bar AND previous bar both below MA
        prev_below_ma = df['Close'].shift(1) < threshold.shift(1)
        # Two days ago was above MA (ensures this is a fresh crossdown)
        two_days_ago_above = df['Close'].shift(2) >= ma.shift(2)
        
        confirmed_crossdown = below_ma & prev_below_ma & two_days_ago_above
        return confirmed_crossdown
    
    else:
        # General N-day confirmation
        # Require N consecutive days below MA
        # Use rolling sum to count consecutive days below MA
        consecutive_below = below_ma.rolling(window=confirmation_days).sum()
        
        # Also check that N+1 days ago was above MA (fresh crossdown)
        n_plus_1_ago_above = df['Close'].shift(confirmation_days) >= ma.shift(confirmation_days)
        
        confirmed_crossdown = (consecutive_below == confirmation_days) & n_plus_1_ago_above
        return confirmed_crossdown


def generate_all_entry_signals(df: pd.DataFrame, apply_prefilters: bool = True,
                               thresholds: dict = None) -> pd.DataFrame:
    """
    Generate all entry signals and add to DataFrame.
    
    ITEM #11: Pre-Trade Quality Filters - If apply_prefilters=True and Pre_Filter_OK
    column exists, raw signals are preserved with _raw suffix and filtered signals
    are created that respect liquidity, price, and earnings window filters.
    
    Updated 2025-12-05: Simplified threshold system - uses only config-based thresholds.
    No global filters applied. Individual signal thresholds are authoritative.
    
    This convenience function generates:
    - Accumulation Score
    - Strong Buy signals
    - Moderate Buy signals
    - Stealth Accumulation signals
    - Confluence signals
    - Volume Breakout signals
    
    Args:
        df: DataFrame with OHLCV data and technical indicators
        apply_prefilters: If True and Pre_Filter_OK exists, apply pre-trade filters
        thresholds: Optional dict with signal thresholds from config file
            Expected keys: 'strong_buy', 'moderate_buy_pullback', etc.
        
    Returns:
        DataFrame with all entry signal columns added (and _raw versions if filtered)
    """
    df = df.copy()
    
    # Extract thresholds from config or use defaults
    if thresholds:
        strong_buy_threshold = thresholds.get('strong_buy', 7.0)
        moderate_buy_threshold = thresholds.get('moderate_buy_pullback', 6.0)
    else:
        # Use defaults
        strong_buy_threshold = 7.0
        moderate_buy_threshold = 6.0
    
    # Generate accumulation score first
    df['Accumulation_Score'] = calculate_accumulation_score(df)
    
    # Generate raw entry signals (order matters for exclusions)
    signal_columns = ['Strong_Buy', 'Moderate_Buy', 'Stealth_Accumulation', 
                      'Confluence_Signal', 'Volume_Breakout']
    
    df['Strong_Buy'] = generate_strong_buy_signals(df, threshold=strong_buy_threshold)
    df['Moderate_Buy'] = generate_moderate_buy_signals(df, threshold=moderate_buy_threshold)
    df['Stealth_Accumulation'] = generate_stealth_accumulation_signals(df)
    df['Confluence_Signal'] = generate_confluence_signals(df)
    df['Volume_Breakout'] = generate_volume_breakout_signals(df)
    
    # No global filter - individual signal thresholds (from config or defaults) are authoritative
    
    # Apply pre-filters if available and requested
    if apply_prefilters and 'Pre_Filter_OK' in df.columns:
        # Preserve raw signals
        for col in signal_columns:
            df[f'{col}_raw'] = df[col].copy()
        
        # Apply filter to all entry signals
        for col in signal_columns:
            df[col] = df[col] & df['Pre_Filter_OK']
    
    return df


def generate_all_exit_signals(df: pd.DataFrame, exit_params: dict = None) -> pd.DataFrame:
    """
    Generate all exit signals and add to DataFrame.
    
    This convenience function generates:
    - Exit Score
    - Profit Taking signals
    - Distribution Warning signals
    - Sell signals
    - Momentum Exhaustion signals
    - Stop Loss signals
    - MA Crossdown signals (optional, configured via exit_params)
    
    Args:
        df: DataFrame with OHLCV data and technical indicators
        exit_params: Optional dict with exit signal parameters from config file
            Expected structure:
            {
                'ma_crossdown': {
                    'enabled': bool,
                    'ma_period': int,
                    'confirmation_days': int,
                    'buffer_pct': float
                }
            }
        
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
    
    # Generate MA crossdown signal if configured
    if exit_params and 'ma_crossdown' in exit_params:
        ma_config = exit_params['ma_crossdown']
        
        # Only generate if enabled
        if ma_config.get('enabled', False):
            ma_period = ma_config.get('ma_period', 50)
            confirmation_days = ma_config.get('confirmation_days', 1)
            buffer_pct = ma_config.get('buffer_pct', 0.0)
            
            df['MA_Crossdown'] = generate_ma_crossdown_signals(
                df,
                ma_period=ma_period,
                confirmation_days=confirmation_days,
                buffer_pct=buffer_pct
            )
        else:
            # Signal disabled, create column with all False
            df['MA_Crossdown'] = False
    else:
        # No config provided, create column with all False for backward compatibility
        df['MA_Crossdown'] = False
    
    return df


def calculate_moderate_buy_score(df: pd.DataFrame) -> pd.Series:
    """
    Calculate Moderate Buy signal score (0-10 scale) for threshold optimization.
    
    NEW LOGIC (Nov 2025): Aligned with redesigned pullback strategy.
    Uses same logic as generate_moderate_buy_signals() but returns graduated scores
    instead of boolean flags. This enables empirical threshold optimization.
    
    Scoring Components:
    - Base accumulation score ≥5 (0-5 points)
    - Pullback zone bonus (0-3 points based on pullback depth)
    - Volume normalizing bonus (0-1.5 points)
    - CMF positive bonus (0-1.5 points based on CMF strength)
    
    Args:
        df: DataFrame with required columns: Accumulation_Score, Close,
            Relative_Volume, CMF_Z, Event_Day
            
    Returns:
        Series with moderate buy scores (0-10 scale)
    """
    score = pd.Series(0.0, index=df.index)
    
    # Base: Accumulation score foundation (0-5 points for score ≥5)
    base_condition = (df['Accumulation_Score'] >= 5).astype(float)
    accumulation_strength = np.clip((df['Accumulation_Score'] - 5) * 1.0, 0, 5)
    score = score + base_condition * accumulation_strength
    
    # Pullback zone bonus (0-3 points based on pullback depth)
    ma_5 = df['Close'].rolling(5).mean()
    ma_20 = df['Close'].rolling(20).mean()
    
    # Calculate pullback depth as % below 5-day MA
    pullback_depth = ((ma_5 - df['Close']) / ma_5) * 100
    # Handle NaN values in boolean operations
    pullback_zone = (df['Close'] < ma_5).fillna(False) & (df['Close'] > ma_20).fillna(False)
    
    # More points for deeper pullbacks (up to 3% below 5-day MA)
    pullback_bonus = np.clip(pullback_depth, 0, 3) * pullback_zone.astype(float)
    score = score + pullback_bonus
    
    # Volume normalizing bonus (0-1.5 points - higher score for lower volume)
    volume_bonus = np.clip((1.5 - df['Relative_Volume']) * 1.5, 0, 1.5)
    score = score + volume_bonus
    
    # CMF positive bonus (0-1.5 points based on CMF z-score strength)
    if 'CMF_Z' in df.columns:
        cmf_bonus = np.clip(df['CMF_Z'], 0, 2) * 0.75  # Max 1.5 at +2σ
        score = score + cmf_bonus
    
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
    ⚠️  DEPRECATED - DO NOT USE ⚠️
    
    ❌ SIGNAL FAILED OUT-OF-SAMPLE VALIDATION (2025-11-08) ❌
    
    This scoring function is deprecated because the underlying Stealth Accumulation
    signal failed validation (22.7% win rate vs 53.2% expected on out-of-sample data).
    
    Status: FAILED VALIDATION - Do NOT use for threshold optimization
    See: OUT_OF_SAMPLE_VALIDATION_REPORT.md for details
    
    ---
    
    Original scoring logic (now deprecated):
    - High accumulation foundation (0-4 points from accumulation score ≥6)
    - Low volume bonus (0-1.5 points for volume <1.3x)
    - A/D divergence bonus (0-1.5 points for A/D up while price not up)
    
    Args:
        df: DataFrame with required columns: Accumulation_Score, Relative_Volume,
            AD_Rising, Price_Rising, Event_Day
            
    Returns:
        Series with stealth accumulation scores (0-7 scale) (DEPRECATED - returns zeros)
    """
    import warnings
    warnings.warn(
        "⚠️  Stealth Accumulation scoring FAILED validation. DO NOT USE. "
        "See OUT_OF_SAMPLE_VALIDATION_REPORT.md",
        DeprecationWarning,
        stacklevel=2
    )
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
