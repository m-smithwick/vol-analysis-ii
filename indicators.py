"""
Technical indicators module for stock analysis.
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple

def calculate_obv(df: pd.DataFrame) -> pd.Series:
    """
    Calculate On-Balance Volume (OBV).
    
    Args:
        df (pd.DataFrame): DataFrame with Close and Volume columns
        
    Returns:
        pd.Series: OBV values
    """
    return ((df['Close'] > df['Close'].shift(1)) * df['Volume'] - 
            (df['Close'] < df['Close'].shift(1)) * df['Volume']).cumsum()

def calculate_ad_line(df: pd.DataFrame) -> pd.Series:
    """
    Calculate Accumulation/Distribution Line.
    
    Args:
        df (pd.DataFrame): DataFrame with OHLCV columns
        
    Returns:
        pd.Series: A/D Line values
    """
    # Handle division by zero when High == Low
    high_low_diff = df['High'] - df['Low']
    
    # Calculate AD_Multiplier with proper handling of zero divisions
    ad_multiplier = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / high_low_diff
    ad_multiplier = ad_multiplier.fillna(0)  # Replace inf/NaN with 0
    ad_multiplier = ad_multiplier.replace([np.inf, -np.inf], 0)  # Replace inf values with 0
    
    # Calculate A/D Line
    ad_line = (ad_multiplier * df['Volume']).cumsum()
    
    return ad_line

def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Calculate Volume-Weighted Average Price (VWAP).
    
    Args:
        df (pd.DataFrame): DataFrame with Close and Volume columns
        
    Returns:
        pd.Series: VWAP values
    """
    return (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()

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

def calculate_anchored_vwap(df: pd.DataFrame, lookback: int = 3) -> pd.Series:
    """
    Calculate VWAP anchored from the most recent significant pivot low.
    
    This creates a more meaningful VWAP that represents institutional cost basis
    from actual turning points, rather than arbitrary chart start dates.
    
    Args:
        df (pd.DataFrame): DataFrame with OHLCV columns
        lookback (int): Lookback period for pivot detection
        
    Returns:
        pd.Series: Anchored VWAP values
    """
    # Find pivot lows (we anchor to lows for bullish analysis)
    pivot_lows, _ = find_pivots(df, lookback=lookback)
    
    # Find the most recent pivot low
    pivot_indices = df.index[pivot_lows].tolist()
    
    if not pivot_indices:
        # No pivots found, fall back to regular VWAP
        return calculate_vwap(df)
    
    # Use the most recent pivot low as anchor point
    anchor_idx = pivot_indices[-1]
    anchor_position = df.index.get_loc(anchor_idx)
    
    # Initialize result series
    anchored_vwap = pd.Series(np.nan, index=df.index)
    
    # Calculate VWAP from anchor point forward
    anchor_slice = df.iloc[anchor_position:]
    if len(anchor_slice) > 0:
        cumulative_pv = (anchor_slice['Close'] * anchor_slice['Volume']).cumsum()
        cumulative_volume = anchor_slice['Volume'].cumsum()
        
        # Calculate anchored VWAP for the period from anchor forward
        vwap_values = cumulative_pv / cumulative_volume
        
        # Assign to result series
        anchored_vwap.iloc[anchor_position:] = vwap_values.values
    
    # Forward fill any NaN values at the beginning with the first calculated value
    if not anchored_vwap.isna().all():
        first_valid_idx = anchored_vwap.first_valid_index()
        if first_valid_idx is not None:
            first_valid_pos = df.index.get_loc(first_valid_idx)
            if first_valid_pos > 0:
                first_value = anchored_vwap.iloc[first_valid_pos]
                anchored_vwap.iloc[:first_valid_pos] = first_value
    
    return anchored_vwap

def calculate_price_volume_correlation(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    Calculate rolling correlation between price and volume changes.
    
    Args:
        df (pd.DataFrame): DataFrame with Close and Volume columns
        window (int): Rolling window size
        
    Returns:
        pd.Series: Correlation values
    """
    df_temp = df.copy()
    df_temp['Return'] = df_temp['Close'].pct_change()
    df_temp['VolChange'] = df_temp['Volume'].pct_change()
    return df_temp['Return'].rolling(window).corr(df_temp['VolChange'])

def calculate_support_levels(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    Calculate rolling support levels.
    
    Args:
        df (pd.DataFrame): DataFrame with Low column
        window (int): Rolling window size
        
    Returns:
        pd.Series: Support level values
    """
    return df['Low'].rolling(window=window).min()

def calculate_intraday_momentum(df: pd.DataFrame) -> pd.Series:
    """
    Calculate intraday momentum score.
    
    Higher values indicate stronger intraday momentum from open.
    
    Args:
        df (pd.DataFrame): DataFrame with OHLC columns
        
    Returns:
        pd.Series: Momentum score values
    """
    # Calculate percentage change from open
    open_to_close = (df['Close'] - df['Open']) / df['Open'] * 100
    
    # Calculate percentage of daily range achieved
    daily_range = (df['High'] - df['Low'])
    open_to_close_range = (df['Close'] - df['Open']).abs()
    range_percent = open_to_close_range / daily_range
    range_percent = range_percent.fillna(0)  # Handle zero range
    range_percent = range_percent.replace([np.inf, -np.inf], 0)  # Handle infinite values
    
    # Combine into momentum score
    momentum = open_to_close * range_percent
    return momentum

def detect_price_jumps(df: pd.DataFrame, threshold_pct: float = 0.5, consecutive_bars: int = 2) -> pd.Series:
    """
    Detect significant price jumps.
    
    Args:
        df (pd.DataFrame): DataFrame with Close column
        threshold_pct (float): Minimum percentage increase to be considered significant
        consecutive_bars (int): Number of consecutive bars to consider
        
    Returns:
        pd.Series: Boolean series where True indicates significant jumps
    """
    # Calculate percentage change between periods
    df_temp = df.copy()
    df_temp['pct_change'] = df_temp['Close'].pct_change() * 100
    
    # Create signals for threshold crossings
    jumps = df_temp['pct_change'] > threshold_pct
    
    # Require consecutive bars if specified
    if consecutive_bars > 1:
        # Rolling sum of Boolean values
        consecutive_jumps = jumps.rolling(window=consecutive_bars).sum() >= consecutive_bars
        return consecutive_jumps
    
    return jumps

def calculate_volume_surprise(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    Calculate volume surprise (ratio of current volume to average).
    
    Args:
        df (pd.DataFrame): DataFrame with Volume column
        window (int): Rolling window size
        
    Returns:
        pd.Series: Volume surprise ratio
    """
    avg_volume = df['Volume'].rolling(window=window).mean()
    return df['Volume'] / avg_volume

def calculate_gap_analysis(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate gap-up and gap-down events.
    
    Args:
        df (pd.DataFrame): DataFrame with OHLC columns
        
    Returns:
        Tuple[pd.Series, pd.Series]: (Gap up series, Gap down series)
    """
    # Calculate previous day's close and current day's open
    prev_close = df['Close'].shift(1)
    curr_open = df['Open']
    
    # Calculate gap percentage
    gap_pct = ((curr_open - prev_close) / prev_close) * 100
    
    # Define gaps
    gap_up = (gap_pct > 1.0)  # Gap up more than 1%
    gap_down = (gap_pct < -1.0)  # Gap down more than 1%
    
    return gap_up, gap_down

def calculate_intraday_high_low_analysis(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """
    Analyze where the close is relative to the intraday high-low range.
    
    Args:
        df (pd.DataFrame): DataFrame with OHLC columns
        
    Returns:
        Tuple[pd.Series, pd.Series]: (Position in range, Strength score)
    """
    # Calculate where the close is in the day's range
    day_range = df['High'] - df['Low']
    position_in_range = (df['Close'] - df['Low']) / day_range
    position_in_range = position_in_range.fillna(0.5)  # Handle zero range days
    position_in_range = position_in_range.replace([np.inf, -np.inf], 0.5)
    
    # Calculate strength - higher when close is near high, negative when close is near low
    strength = (2 * position_in_range - 1) * 100  # Scale to -100 to +100
    
    return position_in_range, strength

def detect_afterhours_gap(prev_day: pd.Series, current_day: pd.Series) -> Tuple[float, bool, bool]:
    """
    Detect and analyze after-hours gaps between previous day close and current day open.
    
    Args:
        prev_day (pd.Series): Previous day OHLCV data
        current_day (pd.Series): Current day OHLCV data
        
    Returns:
        Tuple[float, bool, bool]: (Gap percentage, Is gap up, Is significant gap)
    """
    # Calculate gap
    if prev_day is None or current_day is None:
        return 0.0, False, False
    
    prev_close = prev_day['Close']
    curr_open = current_day['Open']
    
    gap_pct = ((curr_open - prev_close) / prev_close) * 100
    is_gap_up = gap_pct > 0
    is_significant = abs(gap_pct) > 1.0  # 1% threshold for significance
    
    return gap_pct, is_gap_up, is_significant

def calculate_swing_levels(df: pd.DataFrame, lookback: int = 3) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate support and resistance levels based on swing structure.
    
    Uses actual pivot lows and highs to define meaningful support/resistance levels
    instead of rolling min/max which can give false signals during crashes or trends.
    
    Args:
        df (pd.DataFrame): DataFrame with High and Low columns
        lookback (int): Lookback period for pivot detection
        
    Returns:
        Tuple[pd.Series, pd.Series]: (Recent_Swing_Low, Recent_Swing_High) forward-filled series
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

def calculate_swing_proximity_signals(df: pd.DataFrame, recent_swing_low: pd.Series, recent_swing_high: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate swing-based proximity and breakdown signals.
    
    Args:
        df (pd.DataFrame): DataFrame with Close column
        recent_swing_low (pd.Series): Recent swing low levels
        recent_swing_high (pd.Series): Recent swing high levels
        
    Returns:
        Tuple[pd.Series, pd.Series, pd.Series]: (Near_Support, Lost_Support, Near_Resistance)
    """
    # Near support: within 5% above recent swing low
    near_support = df['Close'] <= recent_swing_low * 1.05
    
    # Lost support: broke below recent swing low 
    lost_support = df['Close'] < recent_swing_low
    
    # Near resistance: within 5% below recent swing high
    near_resistance = df['Close'] >= recent_swing_high * 0.95
    
    return near_support, lost_support, near_resistance


def create_next_day_reference_levels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create reference columns showing what structural levels will be available
    for next-day decision making. These columns document what information
    you'll have available when making trading decisions.
    
    EXECUTION TIMING EXPLANATION:
    - Signals are calculated at market close on day T using complete OHLCV data
    - You make trading decisions after market close on day T  
    - You execute trades at market open on day T+1
    - These reference levels show what data is available for day T+1 decisions
    
    Args:
        df (pd.DataFrame): DataFrame with swing levels and VWAP
        
    Returns:
        pd.DataFrame: DataFrame with next-day reference columns added
    """
    df_with_refs = df.copy()
    
    # Create reference levels for next-day execution
    # These show what structural levels you'll reference tomorrow
    df_with_refs['Swing_Low_next_day'] = df['Recent_Swing_Low']
    df_with_refs['Swing_High_next_day'] = df['Recent_Swing_High'] 
    df_with_refs['VWAP_next_day'] = df['VWAP']
    df_with_refs['Support_Level_next_day'] = df['Support_Level']
    
    # Add next day's open price for realistic backtest entry prices
    df_with_refs['Next_Open'] = df['Open'].shift(-1)
    
    return df_with_refs

def calculate_atr(df: pd.DataFrame, period: int = 20) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate True Range and Average True Range (ATR).
    
    True Range is the greatest of:
    - Current High - Current Low
    - Abs(Current High - Previous Close)
    - Abs(Current Low - Previous Close)
    
    Args:
        df (pd.DataFrame): DataFrame with High, Low, Close columns
        period (int): Rolling period for ATR calculation (default: 20)
        
    Returns:
        Tuple[pd.Series, pd.Series]: (TR series, ATR series)
    """
    # Calculate previous close
    prev_close = df['Close'].shift(1)
    
    # Calculate the three components of True Range
    high_low = df['High'] - df['Low']
    high_prev_close = abs(df['High'] - prev_close)
    low_prev_close = abs(df['Low'] - prev_close)
    
    # True Range is the maximum of the three
    true_range = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)
    
    # Average True Range is the rolling mean of True Range
    atr = true_range.rolling(window=period).mean()
    
    return true_range, atr


def detect_event_days(df: pd.DataFrame, atr_multiplier: float = 2.5, 
                     volume_threshold: float = 2.0) -> pd.Series:
    """
    Detect event-driven spike days (earnings, news, macro shocks).
    
    Event days are characterized by:
    - Range Spike: TR > atr_multiplier * ATR20
    - Volume Spike: Relative_Volume > volume_threshold
    
    This filter prevents false accumulation signals during extreme volatility
    events like earnings announcements or macro shock days.
    
    Args:
        df (pd.DataFrame): DataFrame with TR, ATR20, Relative_Volume columns
        atr_multiplier (float): Multiplier for ATR threshold (default: 2.5)
        volume_threshold (float): Volume multiplier threshold (default: 2.0)
        
    Returns:
        pd.Series: Boolean series indicating event days
    """
    # Require both conditions for an event day
    range_spike = df['TR'] > (atr_multiplier * df['ATR20'])
    volume_spike = df['Relative_Volume'] > volume_threshold
    
    # Event day = both range spike AND volume spike
    event_day = range_spike & volume_spike
    
    return event_day


def analyze_morning_momentum(df: pd.DataFrame, morning_end_hour: int = 11) -> pd.Series:
    """
    Analyze morning momentum (from open to specified hour).
    
    Args:
        df (pd.DataFrame): Intraday DataFrame with OHLCV columns
        morning_end_hour (int): Hour that defines the end of morning session (e.g., 11 for 11:00 AM)
        
    Returns:
        pd.Series: Morning momentum scores
    """
    result = pd.Series(index=df.index, dtype=float)
    result[:] = np.nan
    
    # Group by date to analyze each day separately
    grouped = df.groupby(df.index.date)
    
    for day, day_data in grouped:
        # Find the open price (first bar of the day)
        if len(day_data) == 0:
            continue
            
        open_price = day_data.iloc[0]['Open']
        
        # Find all bars until morning_end_hour
        morning_data = day_data[day_data.index.hour <= morning_end_hour]
        
        if not morning_data.empty:
            # Calculate momentum from open to each bar
            for idx, bar in morning_data.iterrows():
                momentum = ((bar['Close'] - open_price) / open_price) * 100
                result.loc[idx] = momentum
    
    return result

def identify_early_movers(df_dict: dict, threshold_pct: float = 1.5) -> list:
    """
    Identify stocks with significant early price movement.
    
    Args:
        df_dict (dict): Dictionary of {ticker: dataframe} with intraday data
        threshold_pct (float): Percentage threshold for significant movement
        
    Returns:
        list: List of dictionaries with early mover information
    """
    early_movers = []
    
    for ticker, df in df_dict.items():
        # Group by date
        grouped = df.groupby(df.index.date)
        
        for day, day_data in grouped:
            # Need at least a few bars to analyze
            if len(day_data) < 3:
                continue
                
            # Get first hour of trading
            market_open_time = pd.Timestamp(day).replace(hour=9, minute=30)
            first_hour_end = market_open_time + pd.Timedelta(hours=1)
            
            first_hour_data = day_data[
                (day_data.index >= market_open_time) & 
                (day_data.index <= first_hour_end)
            ]
            
            if len(first_hour_data) < 2:
                continue
                
            # Calculate movement in first hour
            open_price = first_hour_data.iloc[0]['Open']
            max_price = first_hour_data['High'].max()
            min_price = first_hour_data['Low'].min()
            end_price = first_hour_data.iloc[-1]['Close']
            
            up_move_pct = ((max_price - open_price) / open_price) * 100
            down_move_pct = ((min_price - open_price) / open_price) * 100
            net_move_pct = ((end_price - open_price) / open_price) * 100
            
            # Check if movement is significant
            if abs(net_move_pct) >= threshold_pct:
                direction = "up" if net_move_pct > 0 else "down"
                
                early_movers.append({
                    'ticker': ticker,
                    'date': day,
                    'direction': direction,
                    'net_move_pct': net_move_pct,
                    'max_move_pct': up_move_pct if direction == "up" else down_move_pct,
                    'open_price': open_price,
                    'end_price': end_price
                })
    
    # Sort by absolute movement
    return sorted(early_movers, key=lambda x: abs(x['net_move_pct']), reverse=True)
