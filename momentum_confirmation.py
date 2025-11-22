"""
Momentum Confirmation Filter for Entry Signals

Reduces TIME_STOP rate by requiring price momentum confirmation before entry.
Applied AFTER accumulation score and regime filters.

Implementation Date: 2025-11-22
Target: Reduce TIME_STOP rate from 42% to <25%
"""

import pandas as pd
import numpy as np


def check_momentum_confirmation(df: pd.DataFrame, 
                               require_ma_alignment: bool = True,
                               require_positive_cmf: bool = True,
                               require_volume_support: bool = False) -> pd.Series:
    """
    Check if price has momentum confirmation before entry.
    
    Confirms that accumulation is translating into actual price movement,
    reducing entries on setups that stall immediately.
    
    Args:
        df: DataFrame with technical indicators
        require_ma_alignment: Price must be above 20-day MA (default: True)
        require_positive_cmf: CMF z-score must be positive (default: True)
        require_volume_support: Volume above 20-day average (default: False)
        
    Returns:
        Boolean Series indicating momentum confirmation
    """
    confirmation = pd.Series(True, index=df.index)
    
    # Requirement 1: Price above 20-day MA (trend confirmation)
    if require_ma_alignment and 'Close' in df.columns:
        ma_20 = df['Close'].rolling(20).mean()
        confirmation = confirmation & (df['Close'] > ma_20).fillna(False)
    
    # Requirement 2: Positive CMF (buying pressure present)
    if require_positive_cmf and 'CMF_Z' in df.columns:
        confirmation = confirmation & (df['CMF_Z'] > 0).fillna(False)
    
    # Requirement 3: Volume support (optional - may be too restrictive)
    if require_volume_support and 'Relative_Volume' in df.columns:
        confirmation = confirmation & (df['Relative_Volume'] >= 1.0).fillna(False)
    
    return confirmation


def apply_momentum_filter(df: pd.DataFrame, 
                         entry_signals: list = None,
                         verbose: bool = False) -> pd.DataFrame:
    """
    Apply momentum confirmation filter to entry signals.
    
    Args:
        df: DataFrame with signals and indicators
        entry_signals: List of signal column names to filter (default: all entry signals)
        verbose: Print filtering statistics
        
    Returns:
        DataFrame with momentum-filtered signals
    """
    if entry_signals is None:
        entry_signals = [
            'Strong_Buy', 'Moderate_Buy', 'Stealth_Accumulation',
            'Confluence_Signal', 'Volume_Breakout'
        ]
    
    # Calculate momentum confirmation
    momentum_ok = check_momentum_confirmation(
        df,
        require_ma_alignment=True,
        require_positive_cmf=True,
        require_volume_support=False  # Not required to avoid over-filtering
    )
    
    # Track how many signals get filtered
    total_before = sum(df[sig].sum() for sig in entry_signals if sig in df.columns)
    
    # Apply filter to each entry signal
    for signal_col in entry_signals:
        if signal_col not in df.columns:
            continue
        
        # Preserve pre-momentum signal if not already preserved
        if f'{signal_col}_pre_momentum' not in df.columns:
            df[f'{signal_col}_pre_momentum'] = df[signal_col].copy()
        
        # Apply momentum filter
        df[signal_col] = df[signal_col] & momentum_ok
    
    # Calculate filtering impact
    total_after = sum(df[sig].sum() for sig in entry_signals if sig in df.columns)
    filtered_count = total_before - total_after
    
    if verbose and total_before > 0:
        filter_pct = (filtered_count / total_before) * 100
        print(f"  🎯 Momentum filter: {filtered_count}/{total_before} signals filtered ({filter_pct:.1f}%)")
    
    return df


if __name__ == '__main__':
    print("Momentum Confirmation Filter Module")
    print("Import and use in analysis pipeline with:")
    print("  from momentum_confirmation import apply_momentum_filter")
    print("  df = apply_momentum_filter(df, verbose=True)")
