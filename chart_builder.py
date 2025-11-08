"""
Chart Builder Module - Visualization Logic for Volume Analysis

This module contains all matplotlib plotting functionality, isolating visualization
from the main analysis logic. Supports the complete 3-panel analysis chart with
entry/exit signals, volume indicators, and scoring systems.

Phase 3 of refactoring plan: Extract Visualization Logic
"""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from typing import Optional, Tuple
import os
from datetime import datetime

# Import error handling for validation
from error_handler import (
    ErrorContext, FileOperationError, DataValidationError,
    validate_dataframe, validate_file_path, get_logger
)
from signal_metadata import get_chart_label


def create_price_chart(ax, df: pd.DataFrame, ticker: str, period: str) -> None:
    """
    Create the top panel price chart with all signal markers.
    
    EXECUTION TIMING: Chart markers now show on action day (T+1) instead of signal day (T).
    This eliminates visual lookahead bias - you see signal at close T, act at open T+1.
    
    Args:
        ax: Matplotlib axis for the price chart
        df (pd.DataFrame): Analysis results dataframe with signals
        ticker (str): Stock ticker symbol
        period (str): Analysis period
    """
    # Main price line and reference levels
    ax.plot(df.index, df['Close'], label='Close Price', color='black', linewidth=1.5)
    ax.plot(df.index, df['VWAP'], label='VWAP', color='purple', alpha=0.7, linestyle='--')
    # Plot swing-based support and resistance levels
    ax.plot(df.index, df['Recent_Swing_Low'], label='Swing Support', color='green', alpha=0.6, linestyle=':')
    ax.plot(df.index, df['Recent_Swing_High'], label='Swing Resistance', color='red', alpha=0.6, linestyle=':')
    
    # === ENTRY SIGNALS (Using *_display columns for T+1 visualization) ===
    
    # STRONG BUY SIGNALS (Large Green Dots) - Now shows on action day
    strong_buys = df[df['Strong_Buy_display'] == True]
    if not strong_buys.empty:
        ax.scatter(strong_buys.index, strong_buys['Close'], color='lime', marker='o', 
                   s=150, label=get_chart_label('Strong_Buy'), zorder=10, edgecolors='darkgreen', linewidth=2)
    
    # MODERATE BUY SIGNALS (Medium Yellow Dots) - Now shows on action day
    moderate_buys = df[df['Moderate_Buy_display'] == True]
    if not moderate_buys.empty:
        ax.scatter(moderate_buys.index, moderate_buys['Close'], color='gold', marker='o', 
                   s=100, label=get_chart_label('Moderate_Buy'), zorder=9, edgecolors='orange', linewidth=1.5)
    
    # STEALTH ACCUMULATION (Diamond Symbols) - Now shows on action day
    stealth = df[df['Stealth_Accumulation_display'] == True]
    if not stealth.empty:
        ax.scatter(stealth.index, stealth['Close'], color='cyan', marker='D', 
                   s=80, label=get_chart_label('Stealth_Accumulation'), zorder=8, alpha=0.8)
    
    # CONFLUENCE SIGNALS (Star Symbols) - Now shows on action day
    confluence = df[df['Confluence_Signal_display'] == True]
    if not confluence.empty:
        ax.scatter(confluence.index, confluence['Close'], color='magenta', marker='*', 
                   s=200, label=get_chart_label('Confluence_Signal'), zorder=11)
    
    # VOLUME BREAKOUT (Triangle Symbols) - Now shows on action day
    breakouts = df[df['Volume_Breakout_display'] == True]
    if not breakouts.empty:
        ax.scatter(breakouts.index, breakouts['Close'], color='orangered', marker='^', 
                   s=120, label=get_chart_label('Volume_Breakout'), zorder=9, edgecolors='darkred')
    
    # === EXIT SIGNALS (Using *_display columns for T+1 visualization) ===
    
    # PROFIT TAKING (Orange Dots) - Now shows on action day
    profit_takes = df[df['Profit_Taking_display'] == True]
    if not profit_takes.empty:
        ax.scatter(profit_takes.index, profit_takes['Close'], color='orange', marker='o', 
                   s=120, label=get_chart_label('Profit_Taking'), zorder=10, edgecolors='darkorange', linewidth=2)
    
    # DISTRIBUTION WARNING (Gold Squares) - Now shows on action day
    dist_warnings = df[df['Distribution_Warning_display'] == True]
    if not dist_warnings.empty:
        ax.scatter(dist_warnings.index, dist_warnings['Close'], color='gold', marker='s', 
                   s=100, label=get_chart_label('Distribution_Warning'), zorder=9, edgecolors='darkgoldenrod', linewidth=2)
    
    # SELL SIGNALS (Red Dots) - Now shows on action day
    sells = df[df['Sell_Signal_display'] == True]
    if not sells.empty:
        ax.scatter(sells.index, sells['Close'], color='red', marker='o', 
                   s=120, label=get_chart_label('Sell_Signal'), zorder=10, edgecolors='darkred', linewidth=2)
    
    # MOMENTUM EXHAUSTION (Purple X's) - Now shows on action day
    momentum_exhausts = df[df['Momentum_Exhaustion_display'] == True]
    if not momentum_exhausts.empty:
        ax.scatter(momentum_exhausts.index, momentum_exhausts['Close'], color='purple', marker='x', 
                   s=120, label=get_chart_label('Momentum_Exhaustion'), zorder=9, linewidth=3)
    
    # STOP LOSS TRIGGERS (Dark Red Triangles Down) - Now shows on action day
    stop_losses = df[df['Stop_Loss_display'] == True]
    if not stop_losses.empty:
        ax.scatter(stop_losses.index, stop_losses['Close'], color='darkred', marker='v', 
                   s=130, label=get_chart_label('Stop_Loss'), zorder=11, edgecolors='black', linewidth=2)
    
    # === EVENT DAY MARKERS (Item #3: News/Event Spike Filter) ===
    
    # EVENT DAYS (Yellow Warning Triangles) - News/earnings spikes filtered out
    event_days = df[df['Event_Day'] == True]
    if not event_days.empty:
        ax.scatter(event_days.index, event_days['High'], color='yellow', marker='^', 
                   s=100, label='Event Day (News/Earnings)', zorder=12, edgecolors='orange', 
                   linewidth=2, alpha=0.8)
    
    # Chart formatting
    ax.set_ylabel('Price ($)')
    ax.legend(loc='upper left')
    ax.set_title(f'{ticker} — Accumulation/Distribution Analysis ({period})')
    ax.grid(True, alpha=0.3)


def create_volume_indicators_chart(ax, df: pd.DataFrame) -> None:
    """
    Create the middle panel volume indicators chart.
    
    Args:
        ax: Matplotlib axis for the volume indicators chart
        df (pd.DataFrame): Analysis results dataframe with indicators
    """
    # Volume indicator lines
    ax.plot(df.index, df['OBV'], label='OBV', color='blue', alpha=0.8)
    ax.plot(df.index, df['AD_Line'], label='A/D Line', color='orange', alpha=0.8)
    ax.plot(df.index, df['OBV_MA'], label='OBV MA', color='lightblue', linestyle='--', alpha=0.6)
    ax.plot(df.index, df['AD_MA'], label='A/D MA', color='moccasin', linestyle='--', alpha=0.6)
    
    # Add divergence markers to volume indicators panel (using display columns for T+1 timing)
    stealth = df[df['Stealth_Accumulation_display'] == True]
    if not stealth.empty:
        # Mark stealth accumulation on A/D Line - now shows on action day
        ax.scatter(stealth.index, stealth.index.map(lambda x: df.loc[x, 'AD_Line']), 
                   color='cyan', marker='D', s=60, alpha=0.8, zorder=8)
    
    strong_buys = df[df['Strong_Buy_display'] == True]
    if not strong_buys.empty:
        # Mark strong buys on OBV - now shows on action day
        ax.scatter(strong_buys.index, strong_buys.index.map(lambda x: df.loc[x, 'OBV']), 
                   color='lime', marker='o', s=80, zorder=9, edgecolors='darkgreen')
    
    # Chart formatting
    ax.set_ylabel('Volume Indicators')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)


def create_volume_bars_chart(ax, ax_twin, df: pd.DataFrame) -> None:
    """
    Create the bottom panel volume bars and score chart.
    
    Args:
        ax: Matplotlib axis for volume bars
        ax_twin: Twin axis for entry/exit scores
        df (pd.DataFrame): Analysis results dataframe
    """
    # Volume bars with color coding based on phase
    volume_colors = ['red' if phase == 'Distribution' 
                     else 'darkgreen' if phase == 'Strong_Accumulation'
                     else 'lightgreen' if phase == 'Moderate_Accumulation'
                     else 'yellow' if phase == 'Support_Accumulation'
                     else 'lightgray' for phase in df['Phase']]
    
    ax.bar(df.index, df['Volume'], color=volume_colors, alpha=0.6, width=1)
    ax.plot(df.index, df['Volume_MA'], label='Volume MA', color='black', linestyle='-', alpha=0.8)
    
    # Add signal markers to volume bars (using display columns for T+1 timing)
    breakouts = df[df['Volume_Breakout_display'] == True]
    if not breakouts.empty:
        ax.scatter(breakouts.index, breakouts.index.map(lambda x: df.loc[x, 'Volume']), 
                   color='orangered', marker='^', s=100, zorder=9, edgecolors='darkred')
    
    profit_takes = df[df['Profit_Taking_display'] == True]
    if not profit_takes.empty:
        ax.scatter(profit_takes.index, profit_takes.index.map(lambda x: df.loc[x, 'Volume']), 
                   color='orange', marker='o', s=80, zorder=9, edgecolors='darkorange')
    
    stop_losses = df[df['Stop_Loss_display'] == True]
    if not stop_losses.empty:
        ax.scatter(stop_losses.index, stop_losses.index.map(lambda x: df.loc[x, 'Volume']), 
                   color='darkred', marker='v', s=100, zorder=10, edgecolors='black')
    
    # Volume axis formatting
    ax.set_ylabel('Volume')
    ax.legend(loc='upper left')
    
    # Dual scoring system: Accumulation and Exit scores on twin axis
    ax_twin.plot(df.index, df['Accumulation_Score'], label='Accumulation Score', 
                  color='green', linewidth=2, alpha=0.8)
    ax_twin.plot(df.index, df['Exit_Score'], label='Exit Score', 
                  color='red', linewidth=2, alpha=0.8)
    
    # Add horizontal threshold lines for both entry and exit scores
    ax_twin.axhline(y=8, color='darkred', linestyle=':', alpha=0.8, label='Urgent Exit (8)')
    ax_twin.axhline(y=7, color='lime', linestyle=':', alpha=0.7, label='Strong Entry (7)')
    ax_twin.axhline(y=6, color='orange', linestyle=':', alpha=0.7, label='High Exit Risk (6)')
    ax_twin.axhline(y=4, color='gold', linestyle=':', alpha=0.6, label='Moderate Risk (4)')
    ax_twin.axhline(y=2, color='lightcoral', linestyle=':', alpha=0.5, label='Low Risk (2)')
    
    # Mark actual Strong Buy signal occurrences (using display column for T+1 timing)
    actual_strong_buys = df[df['Strong_Buy_display'] == True]
    if not actual_strong_buys.empty:
        ax_twin.scatter(actual_strong_buys.index, actual_strong_buys['Accumulation_Score'], 
                        color='lime', marker='o', s=50, zorder=10, alpha=0.8, 
                        label=f"{get_chart_label('Strong_Buy')} Signals")
    
    # Mark high exit score points
    high_exit_points = df[df['Exit_Score'] >= 6]
    if not high_exit_points.empty:
        ax_twin.scatter(high_exit_points.index, high_exit_points['Exit_Score'], 
                        color='red', marker='s', s=40, zorder=10, alpha=0.8)
    
    # Mark urgent exit points
    urgent_exit_points = df[df['Exit_Score'] >= 8]
    if not urgent_exit_points.empty:
        ax_twin.scatter(urgent_exit_points.index, urgent_exit_points['Exit_Score'], 
                        color='darkred', marker='X', s=60, zorder=11, alpha=0.9)
    
    # Twin axis formatting
    ax_twin.set_ylabel('Entry/Exit Scores (0-10)')
    ax_twin.legend(loc='upper left')
    ax_twin.set_ylim(0, 10)
    
    # Grid for volume panel
    ax.grid(True, alpha=0.3)


def generate_analysis_chart(df: pd.DataFrame, ticker: str, period: str, 
                           save_path: Optional[str] = None, show: bool = True,
                           figsize: Tuple[int, int] = (12, 9)) -> None:
    """
    Generate complete 3-panel analysis chart.
    
    Args:
        df (pd.DataFrame): DataFrame with OHLCV data and all signals
        ticker (str): Stock ticker symbol
        period (str): Analysis period
        save_path (Optional[str]): If provided, save chart to this path
        show (bool): If True, display chart interactively
        figsize (Tuple[int, int]): Figure size (width, height)
        
    Raises:
        DataValidationError: If DataFrame is invalid
        FileOperationError: If chart saving fails
    """
    with ErrorContext("generating analysis chart", ticker=ticker, period=period):
        # Validate DataFrame
        required_columns = [
            'Close', 'Volume', 'VWAP', 'Support_Level', 'OBV', 'AD_Line', 
            'OBV_MA', 'AD_MA', 'Volume_MA', 'Phase', 'Accumulation_Score', 
            'Exit_Score', 'Strong_Buy_display', 'Moderate_Buy_display', 'Stealth_Accumulation_display',
            'Confluence_Signal_display', 'Volume_Breakout_display', 'Profit_Taking_display', 
            'Distribution_Warning_display', 'Sell_Signal_display', 'Momentum_Exhaustion_display', 
            'Stop_Loss_display'
        ]
        validate_dataframe(df, required_columns=required_columns)
        
        logger = get_logger()
        
        # Create figure and subplots (3-panel layout optimized for 16" Mac)
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=figsize, sharex=True)
        
        # Create the three chart panels
        create_price_chart(ax1, df, ticker, period)
        create_volume_indicators_chart(ax2, df)
        
        # Create twin axis for volume/score panel
        ax3_twin = ax3.twinx()
        create_volume_bars_chart(ax3, ax3_twin, df)
        
        # Final formatting
        plt.xlabel('Date')
        plt.tight_layout()
        
        # Handle chart display/saving with error handling
        if save_path:
            try:
                # Validate output directory is writable
                output_dir = os.path.dirname(save_path) if os.path.dirname(save_path) else '.'
                validate_file_path(output_dir, check_exists=True, check_writable=True)
                
                # Save chart
                plt.savefig(save_path, dpi=150, bbox_inches='tight')
                logger.info(f"Chart saved to {save_path}")
                
            except Exception as e:
                plt.close()  # Ensure cleanup on error
                raise FileOperationError(f"Failed to save chart: {str(e)}")
        
        # Display or close chart
        if show and not save_path:
            plt.show()
        elif show and save_path:
            plt.show()
        else:
            plt.close()  # Close without displaying


def create_multi_timeframe_chart(results_dict: dict, ticker: str, 
                                save_path: Optional[str] = None, 
                                show: bool = True) -> None:
    """
    Create a multi-timeframe analysis chart showing different periods.
    
    Args:
        results_dict (dict): Dictionary with period keys and DataFrame values
        ticker (str): Stock ticker symbol
        save_path (Optional[str]): If provided, save chart to this path
        show (bool): If True, display chart interactively
        
    Raises:
        DataValidationError: If input data is invalid
        FileOperationError: If chart saving fails
    """
    with ErrorContext("generating multi-timeframe chart", ticker=ticker):
        if not results_dict:
            raise DataValidationError("No timeframe data provided")
        
        logger = get_logger()
        
        # Create subplots for each timeframe
        num_periods = len(results_dict)
        fig, axes = plt.subplots(num_periods, 1, figsize=(14, 4 * num_periods), sharex=False)
        
        # Handle single subplot case
        if num_periods == 1:
            axes = [axes]
        
        # Plot each timeframe
        for i, (period, df) in enumerate(results_dict.items()):
            ax = axes[i]
            
            # Simple price chart with basic signals for multi-timeframe view
            ax.plot(df.index, df['Close'], label='Close Price', color='black', linewidth=1.5)
            ax.plot(df.index, df['VWAP'], label='VWAP', color='purple', alpha=0.7, linestyle='--')
            
            # Add key signals (using display columns for T+1 timing)
            strong_buys = df[df['Strong_Buy_display'] == True]
            if not strong_buys.empty:
                ax.scatter(strong_buys.index, strong_buys['Close'], color='lime', marker='o', 
                           s=100, label=get_chart_label('Strong_Buy'), zorder=10, edgecolors='darkgreen')
            
            sells = df[df['Sell_Signal_display'] == True]
            if not sells.empty:
                ax.scatter(sells.index, sells['Close'], color='red', marker='o', 
                           s=100, label=get_chart_label('Sell_Signal'), zorder=10, edgecolors='darkred')
            
            ax.set_title(f'{ticker} - {period} Analysis')
            ax.set_ylabel('Price ($)')
            ax.legend(loc='upper left')
            ax.grid(True, alpha=0.3)
        
        plt.suptitle(f'{ticker} Multi-Timeframe Analysis', fontsize=16, y=0.98)
        plt.tight_layout()
        plt.subplots_adjust(top=0.95)
        
        # Handle saving and display
        if save_path:
            try:
                output_dir = os.path.dirname(save_path) if os.path.dirname(save_path) else '.'
                validate_file_path(output_dir, check_exists=True, check_writable=True)
                
                plt.savefig(save_path, dpi=150, bbox_inches='tight')
                logger.info(f"Multi-timeframe chart saved to {save_path}")
                
            except Exception as e:
                plt.close()
                raise FileOperationError(f"Failed to save multi-timeframe chart: {str(e)}")
        
        if show:
            plt.show()
        else:
            plt.close()


def get_chart_filename(ticker: str, period: str, start_date: str, end_date: str) -> str:
    """
    Generate standardized chart filename.
    
    Args:
        ticker (str): Stock ticker symbol
        period (str): Analysis period
        start_date (str): Start date in YYYYMMDD format
        end_date (str): End date in YYYYMMDD format
        
    Returns:
        str: Standardized chart filename
    """
    return f"{ticker}_{period}_{start_date}_{end_date}_chart.png"


def validate_chart_data(df: pd.DataFrame) -> bool:
    """
    Validate that DataFrame contains required columns for charting.
    
    Args:
        df (pd.DataFrame): DataFrame to validate
        
    Returns:
        bool: True if valid, raises exception if not
        
    Raises:
        DataValidationError: If required columns are missing
    """
    required_columns = [
        'Close', 'Volume', 'VWAP', 'Support_Level', 'OBV', 'AD_Line',
        'Phase', 'Accumulation_Score', 'Exit_Score', 'Strong_Buy_display'
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise DataValidationError(f"Missing required columns for charting: {missing_columns}")
    
    return True
