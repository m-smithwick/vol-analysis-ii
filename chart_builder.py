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
import warnings

# Suppress matplotlib emoji font warnings - emojis are in labels but may not render in all fonts
warnings.filterwarnings('ignore', message='Glyph.*missing from font')

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
    
    GAP-LESS PLOTTING: Uses integer positions for x-axis to create contiguous price action.
    Weekend/holiday gaps removed from visualization while preserving data integrity.
    
    Args:
        ax: Matplotlib axis for the price chart
        df (pd.DataFrame): Analysis results dataframe with signals
        ticker (str): Stock ticker symbol
        period (str): Analysis period
    """
    # Create integer-based x-axis for gap-less plotting
    x_positions = range(len(df))
    # === REGIME STATUS BACKGROUND SHADING ===
    # Shows when market/sector regime allowed signals (green) vs blocked them (red)
    if 'Overall_Regime_OK' in df.columns:
        # Find regime change points
        regime_changes = df['Overall_Regime_OK'].ne(df['Overall_Regime_OK'].shift()).fillna(True)
        change_positions = [i for i, idx in enumerate(df.index) if idx in df[regime_changes].index]
        
        # Draw shaded regions for each regime period
        for i in range(len(change_positions)):
            start_pos = change_positions[i]
            end_pos = change_positions[i + 1] if i + 1 < len(change_positions) else len(df) - 1
            
            regime_ok = df.iloc[start_pos]['Overall_Regime_OK']
            
            if regime_ok:
                # Green tint: Regime OK (signals allowed)
                ax.axvspan(start_pos, end_pos, alpha=0.15, color='green', zorder=0, label='_nolegend_')
            else:
                # Red tint: Regime blocked signals
                ax.axvspan(start_pos, end_pos, alpha=0.15, color='red', zorder=0, label='_nolegend_')
    
    # Main price line and reference levels
    ax.plot(x_positions, df['Close'], label='Close Price', color='black', linewidth=1.5)
    ax.plot(x_positions, df['VWAP'], label='VWAP', color='purple', alpha=0.7, linestyle='--')
    
    # Long-term moving averages for trend context
    ax.plot(x_positions, df['SMA_50'], label='50-day MA', color='blue', alpha=0.8, linewidth=1.5)
    ax.plot(x_positions, df['SMA_200'], label='200-day MA', color='orangered', alpha=0.8, linewidth=1.5)
    
    # Plot swing-based support and resistance levels
    ax.plot(x_positions, df['Recent_Swing_Low'], label='Swing Support', color='green', alpha=0.6, linestyle=':')
    ax.plot(x_positions, df['Recent_Swing_High'], label='Swing Resistance', color='red', alpha=0.6, linestyle=':')
    
    # === ENTRY SIGNALS (Using *_display columns for T+1 visualization) ===
    
    # STRONG BUY SIGNALS (Large Green Dots) - Now shows on action day
    strong_buys = df[df['Strong_Buy_display'] == True]
    if not strong_buys.empty:
        strong_buy_positions = [i for i, idx in enumerate(df.index) if idx in strong_buys.index]
        ax.scatter(strong_buy_positions, strong_buys['Close'].values, color='lime', marker='o', 
                   s=150, label=get_chart_label('Strong_Buy'), zorder=10, edgecolors='darkgreen', linewidth=2)
    
    # MODERATE BUY SIGNALS (Medium Yellow Dots) - Now shows on action day
    moderate_buys = df[df['Moderate_Buy_display'] == True]
    if not moderate_buys.empty:
        moderate_buy_positions = [i for i, idx in enumerate(df.index) if idx in moderate_buys.index]
        ax.scatter(moderate_buy_positions, moderate_buys['Close'].values, color='gold', marker='o', 
                   s=100, label=get_chart_label('Moderate_Buy'), zorder=9, edgecolors='orange', linewidth=1.5)
    
    # STEALTH ACCUMULATION (Diamond Symbols) - Now shows on action day
    stealth = df[df['Stealth_Accumulation_display'] == True]
    if not stealth.empty:
        stealth_positions = [i for i, idx in enumerate(df.index) if idx in stealth.index]
        ax.scatter(stealth_positions, stealth['Close'].values, color='cyan', marker='D', 
                   s=80, label=get_chart_label('Stealth_Accumulation'), zorder=8, alpha=0.8)
    
    # CONFLUENCE SIGNALS (Star Symbols) - Now shows on action day
    confluence = df[df['Confluence_Signal_display'] == True]
    if not confluence.empty:
        confluence_positions = [i for i, idx in enumerate(df.index) if idx in confluence.index]
        ax.scatter(confluence_positions, confluence['Close'].values, color='magenta', marker='*', 
                   s=200, label=get_chart_label('Confluence_Signal'), zorder=11)
    
    # VOLUME BREAKOUT (Triangle Symbols) - Now shows on action day
    breakouts = df[df['Volume_Breakout_display'] == True]
    if not breakouts.empty:
        breakout_positions = [i for i, idx in enumerate(df.index) if idx in breakouts.index]
        ax.scatter(breakout_positions, breakouts['Close'].values, color='orangered', marker='^', 
                   s=120, label=get_chart_label('Volume_Breakout'), zorder=9, edgecolors='darkred')
    
    # === EXIT SIGNALS (Using *_display columns for T+1 visualization) ===
    
    # PROFIT TAKING (Orange Dots) - Now shows on action day
    profit_takes = df[df['Profit_Taking_display'] == True]
    if not profit_takes.empty:
        profit_take_positions = [i for i, idx in enumerate(df.index) if idx in profit_takes.index]
        ax.scatter(profit_take_positions, profit_takes['Close'].values, color='orange', marker='o', 
                   s=120, label=get_chart_label('Profit_Taking'), zorder=10, edgecolors='darkorange', linewidth=2)
    
    # DISTRIBUTION WARNING (Gold Squares) - Now shows on action day
    dist_warnings = df[df['Distribution_Warning_display'] == True]
    if not dist_warnings.empty:
        dist_warning_positions = [i for i, idx in enumerate(df.index) if idx in dist_warnings.index]
        ax.scatter(dist_warning_positions, dist_warnings['Close'].values, color='gold', marker='s', 
                   s=100, label=get_chart_label('Distribution_Warning'), zorder=9, edgecolors='darkgoldenrod', linewidth=2)
    
    # SELL SIGNALS (Red Dots) - Now shows on action day
    sells = df[df['Sell_Signal_display'] == True]
    if not sells.empty:
        sell_positions = [i for i, idx in enumerate(df.index) if idx in sells.index]
        ax.scatter(sell_positions, sells['Close'].values, color='red', marker='o', 
                   s=120, label=get_chart_label('Sell_Signal'), zorder=10, edgecolors='darkred', linewidth=2)
    
    # MOMENTUM EXHAUSTION (Purple X's) - Now shows on action day
    momentum_exhausts = df[df['Momentum_Exhaustion_display'] == True]
    if not momentum_exhausts.empty:
        momentum_exhaust_positions = [i for i, idx in enumerate(df.index) if idx in momentum_exhausts.index]
        ax.scatter(momentum_exhaust_positions, momentum_exhausts['Close'].values, color='purple', marker='x', 
                   s=120, label=get_chart_label('Momentum_Exhaustion'), zorder=9, linewidth=3)
    
    # STOP LOSS TRIGGERS (Dark Red Triangles Down) - Now shows on action day
    stop_losses = df[df['Stop_Loss_display'] == True]
    if not stop_losses.empty:
        stop_loss_positions = [i for i, idx in enumerate(df.index) if idx in stop_losses.index]
        ax.scatter(stop_loss_positions, stop_losses['Close'].values, color='darkred', marker='v', 
                   s=130, label=get_chart_label('Stop_Loss'), zorder=11, edgecolors='black', linewidth=2)
    
    # === EVENT DAY MARKERS (Item #3: News/Event Spike Filter) ===
    
    # EVENT DAYS (Yellow Warning Triangles) - News/earnings spikes filtered out
    event_days = df[df['Event_Day'] == True]
    if not event_days.empty:
        event_day_positions = [i for i, idx in enumerate(df.index) if idx in event_days.index]
        ax.scatter(event_day_positions, event_days['High'].values, color='yellow', marker='^', 
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
    # Create integer-based x-axis for gap-less plotting
    x_positions = range(len(df))
    
    # Volume indicator lines
    ax.plot(x_positions, df['OBV'], label='OBV', color='blue', alpha=0.8)
    ax.plot(x_positions, df['AD_Line'], label='A/D Line', color='orange', alpha=0.8)
    ax.plot(x_positions, df['OBV_MA'], label='OBV MA', color='lightblue', linestyle='--', alpha=0.6)
    ax.plot(x_positions, df['AD_MA'], label='A/D MA', color='moccasin', linestyle='--', alpha=0.6)
    
    # Add divergence markers to volume indicators panel (using display columns for T+1 timing)
    stealth = df[df['Stealth_Accumulation_display'] == True]
    if not stealth.empty:
        # Mark stealth accumulation on A/D Line - now shows on action day
        stealth_positions = [i for i, idx in enumerate(df.index) if idx in stealth.index]
        stealth_ad_values = [df.loc[df.index[i], 'AD_Line'] for i in stealth_positions]
        ax.scatter(stealth_positions, stealth_ad_values, 
                   color='cyan', marker='D', s=60, alpha=0.8, zorder=8)
    
    strong_buys = df[df['Strong_Buy_display'] == True]
    if not strong_buys.empty:
        # Mark strong buys on OBV - now shows on action day
        strong_buy_positions = [i for i, idx in enumerate(df.index) if idx in strong_buys.index]
        strong_buy_obv_values = [df.loc[df.index[i], 'OBV'] for i in strong_buy_positions]
        ax.scatter(strong_buy_positions, strong_buy_obv_values, 
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
    # Create integer-based x-axis for gap-less plotting
    x_positions = range(len(df))
    
    # Volume bars with color coding based on phase
    volume_colors = ['red' if phase == 'Distribution' 
                     else 'darkgreen' if phase == 'Strong_Accumulation'
                     else 'lightgreen' if phase == 'Moderate_Accumulation'
                     else 'yellow' if phase == 'Support_Accumulation'
                     else 'lightgray' for phase in df['Phase']]
    
    ax.bar(x_positions, df['Volume'], color=volume_colors, alpha=0.6, width=1)
    ax.plot(x_positions, df['Volume_MA'], label='Volume MA', color='black', linestyle='-', alpha=0.8)
    
    # Add signal markers to volume bars (using display columns for T+1 timing)
    breakouts = df[df['Volume_Breakout_display'] == True]
    if not breakouts.empty:
        breakout_positions = [i for i, idx in enumerate(df.index) if idx in breakouts.index]
        breakout_volumes = [df.loc[df.index[i], 'Volume'] for i in breakout_positions]
        ax.scatter(breakout_positions, breakout_volumes, 
                   color='orangered', marker='^', s=100, zorder=9, edgecolors='darkred')
    
    profit_takes = df[df['Profit_Taking_display'] == True]
    if not profit_takes.empty:
        profit_take_positions = [i for i, idx in enumerate(df.index) if idx in profit_takes.index]
        profit_take_volumes = [df.loc[df.index[i], 'Volume'] for i in profit_take_positions]
        ax.scatter(profit_take_positions, profit_take_volumes, 
                   color='orange', marker='o', s=80, zorder=9, edgecolors='darkorange')
    
    stop_losses = df[df['Stop_Loss_display'] == True]
    if not stop_losses.empty:
        stop_loss_positions = [i for i, idx in enumerate(df.index) if idx in stop_losses.index]
        stop_loss_volumes = [df.loc[df.index[i], 'Volume'] for i in stop_loss_positions]
        ax.scatter(stop_loss_positions, stop_loss_volumes, 
                   color='darkred', marker='v', s=100, zorder=10, edgecolors='black')
    
    # Volume axis formatting
    ax.set_ylabel('Volume')
    ax.legend(loc='upper left')
    
    # Dual scoring system: Accumulation and Exit scores on twin axis
    ax_twin.plot(x_positions, df['Accumulation_Score'], label='Accumulation Score', 
                  color='green', linewidth=2, alpha=0.8)
    ax_twin.plot(x_positions, df['Exit_Score'], label='Exit Score', 
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
        strong_buy_positions = [i for i, idx in enumerate(df.index) if idx in actual_strong_buys.index]
        ax_twin.scatter(strong_buy_positions, actual_strong_buys['Accumulation_Score'].values, 
                        color='lime', marker='o', s=50, zorder=10, alpha=0.8, 
                        label=f"{get_chart_label('Strong_Buy')} Signals")
    
    # Mark high exit score points
    high_exit_points = df[df['Exit_Score'] >= 6]
    if not high_exit_points.empty:
        high_exit_positions = [i for i, idx in enumerate(df.index) if idx in high_exit_points.index]
        ax_twin.scatter(high_exit_positions, high_exit_points['Exit_Score'].values, 
                        color='red', marker='s', s=40, zorder=10, alpha=0.8)
    
    # Mark urgent exit points
    urgent_exit_points = df[df['Exit_Score'] >= 8]
    if not urgent_exit_points.empty:
        urgent_exit_positions = [i for i, idx in enumerate(df.index) if idx in urgent_exit_points.index]
        ax_twin.scatter(urgent_exit_positions, urgent_exit_points['Exit_Score'].values, 
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
            
            # Create integer-based x-axis for gap-less plotting
            x_positions = range(len(df))
            
            # Simple price chart with basic signals for multi-timeframe view
            ax.plot(x_positions, df['Close'], label='Close Price', color='black', linewidth=1.5)
            ax.plot(x_positions, df['VWAP'], label='VWAP', color='purple', alpha=0.7, linestyle='--')
            
            # Add key signals (using display columns for T+1 timing)
            strong_buys = df[df['Strong_Buy_display'] == True]
            if not strong_buys.empty:
                strong_buy_positions = [j for j, idx in enumerate(df.index) if idx in strong_buys.index]
                ax.scatter(strong_buy_positions, strong_buys['Close'].values, color='lime', marker='o', 
                           s=100, label=get_chart_label('Strong_Buy'), zorder=10, edgecolors='darkgreen')
            
            sells = df[df['Sell_Signal_display'] == True]
            if not sells.empty:
                sell_positions = [j for j, idx in enumerate(df.index) if idx in sells.index]
                ax.scatter(sell_positions, sells['Close'].values, color='red', marker='o', 
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
