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
