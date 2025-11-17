"""
Chart Builder Module - Plotly/DASH Implementation

Plotly-based visualization for Volume Analysis charts.
Provides interactive 3-panel analysis charts with all signal markers.

This module maintains the same API as chart_builder.py (matplotlib version)
to enable drop-in replacement in the main analysis pipeline.

Author: Conversion from matplotlib to plotly
Date: 2025-11-06
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Optional, Tuple

from signal_metadata import get_chart_label


def _signal_labels() -> dict:
    """Return a mapping of signal keys to their display labels."""
    keys = [
        'Strong_Buy', 'Moderate_Buy', 'Stealth_Accumulation',
        'Confluence_Signal', 'Volume_Breakout', 'Profit_Taking',
        'Distribution_Warning', 'Sell_Signal', 'Momentum_Exhaustion',
        'Stop_Loss'
    ]
    return {key: get_chart_label(key) for key in keys}


def create_price_chart(fig, df: pd.DataFrame, ticker: str, period: str, row: int = 1) -> None:
    """
    Create the top panel price chart with all signal markers.
    
    EXECUTION TIMING: Chart markers show on action day (T+1) using *_display columns.
    
    Args:
        fig: Plotly figure object
        df (pd.DataFrame): Analysis results dataframe with signals
        ticker (str): Stock ticker symbol
        period (str): Analysis period
        row (int): Subplot row number
    """
    labels = _signal_labels()

    # Main price line
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['Close'],
        mode='lines',
        name='Close Price',
        line=dict(color='black', width=1.5),
        hovertemplate='<b>Close</b><br>Date: %{x}<br>Price: $%{y:.2f}<extra></extra>'
    ), row=row, col=1)
    
    # VWAP reference line
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['VWAP'],
        mode='lines',
        name='VWAP',
        line=dict(color='purple', width=1, dash='dash'),
        opacity=0.7,
        hovertemplate='<b>VWAP</b><br>%{y:.2f}<extra></extra>'
    ), row=row, col=1)
    
    # Swing support and resistance levels
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['Recent_Swing_Low'],
        mode='lines',
        name='Swing Support',
        line=dict(color='green', width=1, dash='dot'),
        opacity=0.6,
        hovertemplate='<b>Support</b><br>%{y:.2f}<extra></extra>'
    ), row=row, col=1)
    
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['Recent_Swing_High'],
        mode='lines',
        name='Swing Resistance',
        line=dict(color='red', width=1, dash='dot'),
        opacity=0.6,
        hovertemplate='<b>Resistance</b><br>%{y:.2f}<extra></extra>'
    ), row=row, col=1)
    
    # === ENTRY SIGNALS (Using *_display columns for T+1 visualization) ===
    
    # STRONG BUY SIGNALS (Large Green Dots)
    strong_buys = df[df['Strong_Buy_display'] == True]
    if not strong_buys.empty:
        fig.add_trace(go.Scatter(
            x=strong_buys.index,
            y=strong_buys['Close'],
            mode='markers',
            name=labels['Strong_Buy'],
            marker=dict(
                size=15,
                color='lime',
                symbol='circle',
                line=dict(width=2, color='darkgreen')
            ),
            hovertemplate=f'<b>{labels["Strong_Buy"]}</b><br>Date: %{{x}}<br>Price: $%{{y:.2f}}<extra></extra>'
        ), row=row, col=1)
    
    # MODERATE BUY SIGNALS (Medium Yellow Dots)
    moderate_buys = df[df['Moderate_Buy_display'] == True]
    if not moderate_buys.empty:
        fig.add_trace(go.Scatter(
            x=moderate_buys.index,
            y=moderate_buys['Close'],
            mode='markers',
            name=labels['Moderate_Buy'],
            marker=dict(
                size=10,
                color='gold',
                symbol='circle',
                line=dict(width=1.5, color='orange')
            ),
            hovertemplate=f'<b>{labels["Moderate_Buy"]}</b><br>Date: %{{x}}<br>Price: $%{{y:.2f}}<extra></extra>'
        ), row=row, col=1)
    
    # STEALTH ACCUMULATION (Diamond Symbols)
    stealth = df[df['Stealth_Accumulation_display'] == True]
    if not stealth.empty:
        fig.add_trace(go.Scatter(
            x=stealth.index,
            y=stealth['Close'],
            mode='markers',
            name=labels['Stealth_Accumulation'],
            marker=dict(
                size=8,
                color='cyan',
                symbol='diamond',
                opacity=0.8
            ),
            hovertemplate=f'<b>{labels["Stealth_Accumulation"]}</b><br>Date: %{{x}}<br>Price: $%{{y:.2f}}<extra></extra>'
        ), row=row, col=1)
    
    # CONFLUENCE SIGNALS (Star Symbols)
    confluence = df[df['Confluence_Signal_display'] == True]
    if not confluence.empty:
        fig.add_trace(go.Scatter(
            x=confluence.index,
            y=confluence['Close'],
            mode='markers',
            name=labels['Confluence_Signal'],
            marker=dict(
                size=20,
                color='magenta',
                symbol='star'
            ),
            hovertemplate=f'<b>{labels["Confluence_Signal"]}</b><br>Date: %{{x}}<br>Price: $%{{y:.2f}}<extra></extra>'
        ), row=row, col=1)
    
    # VOLUME BREAKOUT (Triangle Symbols)
    breakouts = df[df['Volume_Breakout_display'] == True]
    if not breakouts.empty:
        fig.add_trace(go.Scatter(
            x=breakouts.index,
            y=breakouts['Close'],
            mode='markers',
            name=labels['Volume_Breakout'],
            marker=dict(
                size=12,
                color='orangered',
                symbol='triangle-up',
                line=dict(width=1, color='darkred')
            ),
            hovertemplate=f'<b>{labels["Volume_Breakout"]}</b><br>Date: %{{x}}<br>Price: $%{{y:.2f}}<extra></extra>'
        ), row=row, col=1)
    
    # === EXIT SIGNALS (Using *_display columns for T+1 visualization) ===
    
    # PROFIT TAKING (Orange Dots)
    profit_takes = df[df['Profit_Taking_display'] == True]
    if not profit_takes.empty:
        fig.add_trace(go.Scatter(
            x=profit_takes.index,
            y=profit_takes['Close'],
            mode='markers',
            name=labels['Profit_Taking'],
            marker=dict(
                size=12,
                color='orange',
                symbol='circle',
                line=dict(width=2, color='darkorange')
            ),
            hovertemplate=f'<b>{labels["Profit_Taking"]}</b><br>Date: %{{x}}<br>Price: $%{{y:.2f}}<extra></extra>'
        ), row=row, col=1)
    
    # DISTRIBUTION WARNING (Gold Squares)
    dist_warnings = df[df['Distribution_Warning_display'] == True]
    if not dist_warnings.empty:
        fig.add_trace(go.Scatter(
            x=dist_warnings.index,
            y=dist_warnings['Close'],
            mode='markers',
            name=labels['Distribution_Warning'],
            marker=dict(
                size=10,
                color='gold',
                symbol='square',
                line=dict(width=2, color='darkgoldenrod')
            ),
            hovertemplate=f'<b>{labels["Distribution_Warning"]}</b><br>Date: %{{x}}<br>Price: $%{{y:.2f}}<extra></extra>'
        ), row=row, col=1)
    
    # SELL SIGNALS (Red Dots)
    sells = df[df['Sell_Signal_display'] == True]
    if not sells.empty:
        fig.add_trace(go.Scatter(
            x=sells.index,
            y=sells['Close'],
            mode='markers',
            name=labels['Sell_Signal'],
            marker=dict(
                size=12,
                color='red',
                symbol='circle',
                line=dict(width=2, color='darkred')
            ),
            hovertemplate=f'<b>{labels["Sell_Signal"]}</b><br>Date: %{{x}}<br>Price: $%{{y:.2f}}<extra></extra>'
        ), row=row, col=1)
    
    # MOMENTUM EXHAUSTION (Purple X's)
    momentum_exhausts = df[df['Momentum_Exhaustion_display'] == True]
    if not momentum_exhausts.empty:
        fig.add_trace(go.Scatter(
            x=momentum_exhausts.index,
            y=momentum_exhausts['Close'],
            mode='markers',
            name=labels['Momentum_Exhaustion'],
            marker=dict(
                size=12,
                color='purple',
                symbol='x',
            line=dict(width=3)
            ),
            hovertemplate=f'<b>{labels["Momentum_Exhaustion"]}</b><br>Date: %{{x}}<br>Price: $%{{y:.2f}}<extra></extra>'
        ), row=row, col=1)
    
    # STOP LOSS TRIGGERS (Dark Red Triangles Down)
    stop_losses = df[df['Stop_Loss_display'] == True]
    if not stop_losses.empty:
        fig.add_trace(go.Scatter(
            x=stop_losses.index,
            y=stop_losses['Close'],
            mode='markers',
            name=labels['Stop_Loss'],
            marker=dict(
                size=13,
                color='darkred',
                symbol='triangle-down',
                line=dict(width=2, color='black')
            ),
            hovertemplate=f'<b>{labels["Stop_Loss"]}</b><br>Date: %{{x}}<br>Price: $%{{y:.2f}}<extra></extra>'
        ), row=row, col=1)
    
    # === EVENT DAY MARKERS (News/Event Spike Filter) ===
    event_days = df[df['Event_Day'] == True]
    if not event_days.empty:
        fig.add_trace(go.Scatter(
            x=event_days.index,
            y=event_days['High'],
            mode='markers',
            name='Event Day (News/Earnings)',
            marker=dict(
                size=10,
                color='yellow',
                symbol='triangle-up',
                line=dict(width=2, color='orange'),
                opacity=0.8
            ),
            hovertemplate='<b>Event Day</b><br>Date: %{x}<br>High: $%{y:.2f}<extra></extra>'
        ), row=row, col=1)
    
    # Update y-axis
    fig.update_yaxes(title_text="Price ($)", row=row, col=1)


def create_volume_indicators_chart(fig, df: pd.DataFrame, row: int = 2) -> None:
    """
    Create the middle panel volume indicators chart.
    
    Args:
        fig: Plotly figure object
        df (pd.DataFrame): Analysis results dataframe with indicators
        row (int): Subplot row number
    """
    labels = _signal_labels()

    # OBV line
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['OBV'],
        mode='lines',
        name='OBV',
        line=dict(color='blue', width=2),
        opacity=0.8,
        hovertemplate='<b>OBV</b><br>%{y:,.0f}<extra></extra>'
    ), row=row, col=1)
    
    # A/D Line
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['AD_Line'],
        mode='lines',
        name='A/D Line',
        line=dict(color='orange', width=2),
        opacity=0.8,
        hovertemplate='<b>A/D Line</b><br>%{y:,.0f}<extra></extra>'
    ), row=row, col=1)
    
    # Moving averages
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['OBV_MA'],
        mode='lines',
        name='OBV MA',
        line=dict(color='lightblue', width=1, dash='dash'),
        opacity=0.6,
        hovertemplate='<b>OBV MA</b><br>%{y:,.0f}<extra></extra>'
    ), row=row, col=1)
    
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['AD_MA'],
        mode='lines',
        name='A/D MA',
        line=dict(color='moccasin', width=1, dash='dash'),
        opacity=0.6,
        hovertemplate='<b>A/D MA</b><br>%{y:,.0f}<extra></extra>'
    ), row=row, col=1)
    
    # Add divergence markers
    stealth = df[df['Stealth_Accumulation_display'] == True]
    if not stealth.empty:
        fig.add_trace(go.Scatter(
            x=stealth.index,
            y=[df.loc[idx, 'AD_Line'] for idx in stealth.index],
            mode='markers',
            name=f"{labels['Stealth_Accumulation']} (on A/D)",
            marker=dict(size=6, color='cyan', symbol='diamond', opacity=0.8),
            showlegend=False,
            hovertemplate=f'<b>{labels["Stealth_Accumulation"]}</b><br>%{{y:,.0f}}<extra></extra>'
        ), row=row, col=1)
    
    strong_buys = df[df['Strong_Buy_display'] == True]
    if not strong_buys.empty:
        fig.add_trace(go.Scatter(
            x=strong_buys.index,
            y=[df.loc[idx, 'OBV'] for idx in strong_buys.index],
            mode='markers',
            name=f"{labels['Strong_Buy']} (on OBV)",
            marker=dict(size=8, color='lime', symbol='circle', line=dict(color='darkgreen')),
            showlegend=False,
            hovertemplate=f'<b>{labels["Strong_Buy"]}</b><br>%{{y:,.0f}}<extra></extra>'
        ), row=row, col=1)
    
    # Update y-axis
    fig.update_yaxes(title_text="Volume Indicators", row=row, col=1)


def create_volume_bars_chart(fig, df: pd.DataFrame, row: int = 3) -> None:
    """
    Create the bottom panel volume bars and score chart.
    
    Args:
        fig: Plotly figure object
        df (pd.DataFrame): Analysis results dataframe
        row (int): Subplot row number
    """
    labels = _signal_labels()

    # Volume bars with color coding based on phase
    volume_colors = ['red' if phase == 'Distribution' 
                     else 'darkgreen' if phase == 'Strong_Accumulation'
                     else 'lightgreen' if phase == 'Moderate_Accumulation'
                     else 'yellow' if phase == 'Support_Accumulation'
                     else 'lightgray' for phase in df['Phase']]
    
    fig.add_trace(go.Bar(
        x=df.index,
        y=df['Volume'],
        name='Volume',
        marker=dict(color=volume_colors, opacity=0.6),
        hovertemplate='<b>Volume</b><br>Date: %{x}<br>%{y:,.0f}<extra></extra>'
    ), row=row, col=1)
    
    # Volume MA line
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['Volume_MA'],
        mode='lines',
        name='Volume MA',
        line=dict(color='black', width=1),
        opacity=0.8,
        hovertemplate='<b>Volume MA</b><br>%{y:,.0f}<extra></extra>'
    ), row=row, col=1)
    
    # === DUAL SCORING SYSTEM ON SECONDARY Y-AXIS ===
    
    # Accumulation Score (green line)
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['Accumulation_Score'],
        mode='lines',
        name='Accumulation Score',
        line=dict(color='green', width=2),
        opacity=0.8,
        yaxis='y2',
        hovertemplate='<b>Accumulation Score</b><br>%{y:.1f}<extra></extra>'
    ), row=row, col=1, secondary_y=True)
    
    # Exit Score (red line)
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['Exit_Score'],
        mode='lines',
        name='Exit Score',
        line=dict(color='red', width=2),
        opacity=0.8,
        yaxis='y2',
        hovertemplate='<b>Exit Score</b><br>%{y:.1f}<extra></extra>'
    ), row=row, col=1, secondary_y=True)
    
    # Threshold lines on secondary y-axis
    threshold_lines = [
        (8, 'darkred', 'Urgent Exit (8)'),
        (7, 'lime', 'Strong Entry (7)'),
        (6, 'orange', 'High Exit Risk (6)'),
        (4, 'gold', 'Moderate Risk (4)'),
        (2, 'lightcoral', 'Low Risk (2)')
    ]
    
    for threshold, color, label in threshold_lines:
        fig.add_trace(go.Scatter(
            x=[df.index[0], df.index[-1]],
            y=[threshold, threshold],
            mode='lines',
            name=label,
            line=dict(color=color, width=1, dash='dot'),
            opacity=0.7,
            yaxis='y2',
            showlegend=True,
            hovertemplate=f'<b>{label}</b><extra></extra>'
        ), row=row, col=1, secondary_y=True)
    
    # Mark actual Strong Buy signals
    actual_strong_buys = df[df['Strong_Buy_display'] == True]
    if not actual_strong_buys.empty:
        fig.add_trace(go.Scatter(
            x=actual_strong_buys.index,
            y=actual_strong_buys['Accumulation_Score'],
            mode='markers',
            name=f"{labels['Strong_Buy']} Signals",
            marker=dict(size=5, color='lime', opacity=0.8),
            yaxis='y2',
            showlegend=False,
            hovertemplate=f'<b>{labels["Strong_Buy"]}</b><br>Score: %{{y:.1f}}<extra></extra>'
        ), row=row, col=1, secondary_y=True)
    
    # Mark high exit score points
    high_exit_points = df[df['Exit_Score'] >= 6]
    if not high_exit_points.empty:
        fig.add_trace(go.Scatter(
            x=high_exit_points.index,
            y=high_exit_points['Exit_Score'],
            mode='markers',
            name='High Exit Risk',
            marker=dict(size=4, color='red', symbol='square', opacity=0.8),
            yaxis='y2',
            showlegend=False,
            hovertemplate='<b>High Exit Risk</b><br>Score: %{y:.1f}<extra></extra>'
        ), row=row, col=1, secondary_y=True)
    
    # Mark urgent exit points
    urgent_exit_points = df[df['Exit_Score'] >= 8]
    if not urgent_exit_points.empty:
        fig.add_trace(go.Scatter(
            x=urgent_exit_points.index,
            y=urgent_exit_points['Exit_Score'],
            mode='markers',
            name='Urgent Exit',
            marker=dict(size=6, color='darkred', symbol='x', opacity=0.9),
            yaxis='y2',
            showlegend=False,
            hovertemplate='<b>Urgent Exit</b><br>Score: %{y:.1f}<extra></extra>'
        ), row=row, col=1, secondary_y=True)
    
    # Update y-axes
    fig.update_yaxes(title_text="Volume", row=row, col=1, secondary_y=False)
    fig.update_yaxes(title_text="Entry/Exit Scores (0-10)", row=row, col=1, secondary_y=True, range=[0, 10])


def generate_analysis_chart(df: pd.DataFrame, ticker: str, period: str, 
                           save_path: Optional[str] = None, show: bool = True,
                           figsize: Tuple[int, int] = (1200, 900)) -> None:
    """
    Generate complete 3-panel analysis chart using Plotly.
    
    Args:
        df (pd.DataFrame): DataFrame with OHLCV data and all signals
        ticker (str): Stock ticker symbol
        period (str): Analysis period
        save_path (Optional[str]): If provided, save chart as HTML to this path
        show (bool): If True, display chart interactively in browser
        figsize (Tuple[int, int]): Figure size (width, height) in pixels
        
    Raises:
        ValueError: If DataFrame is invalid or missing required columns
    """
    # Validate required columns
    required_columns = [
        'Close', 'Volume', 'VWAP', 'Support_Level', 'OBV', 'AD_Line', 
        'OBV_MA', 'AD_MA', 'Volume_MA', 'Phase', 'Accumulation_Score', 
        'Exit_Score', 'Strong_Buy_display', 'Moderate_Buy_display', 
        'Stealth_Accumulation_display', 'Confluence_Signal_display', 
        'Volume_Breakout_display', 'Profit_Taking_display', 
        'Distribution_Warning_display', 'Sell_Signal_display', 
        'Momentum_Exhaustion_display', 'Stop_Loss_display'
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    # Create 3-panel subplot with secondary y-axis for bottom panel
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(
            f'{ticker} — Accumulation/Distribution Analysis ({period})',
            'Volume Indicators',
            'Volume & Entry/Exit Scores'
        ),
        specs=[[{"secondary_y": False}],
               [{"secondary_y": False}],
               [{"secondary_y": True}]]  # Bottom panel needs dual y-axis
    )
    
    # Create the three chart panels
    create_price_chart(fig, df, ticker, period, row=1)
    create_volume_indicators_chart(fig, df, row=2)
    create_volume_bars_chart(fig, df, row=3)
    
    # Update layout
    fig.update_layout(
        width=figsize[0],
        height=figsize[1],
        showlegend=True,
        hovermode='x unified',
        template='plotly_white',
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.01
        )
    )
    
    # Update x-axis to show dates nicely
    fig.update_xaxes(
        title_text="Date",
        row=3,
        rangeslider_visible=False,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=3, label="3m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=12, label="12m", step="month", stepmode="backward"),
                dict(step="all", label="All")
            ])
        )
    )
    
    # Add grid to all panels
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    
    # Save or show
    if save_path:
        fig.write_html(save_path)
        print(f"📊 Chart saved to {save_path}")
    
    if show:
        fig.show()


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
        ValueError: If input data is invalid
    """
    if not results_dict:
        raise ValueError("No timeframe data provided")
    
    num_periods = len(results_dict)
    labels = _signal_labels()
    
    # Create subplots for each timeframe
    fig = make_subplots(
        rows=num_periods, cols=1,
        shared_xaxes=False,
        vertical_spacing=0.05,
        subplot_titles=[f'{ticker} - {period} Analysis' for period in results_dict.keys()]
    )
    
    # Plot each timeframe
    for i, (period, df) in enumerate(results_dict.items(), 1):
        # Simple price chart with key signals
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['Close'],
            mode='lines',
            name=f'Close ({period})',
            line=dict(color='black', width=1.5),
            showlegend=(i==1)
        ), row=i, col=1)
        
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['VWAP'],
            mode='lines',
            name=f'VWAP ({period})',
            line=dict(color='purple', width=1, dash='dash'),
            opacity=0.7,
            showlegend=(i==1)
        ), row=i, col=1)
        
        # Add key signals
        strong_buys = df[df['Strong_Buy_display'] == True]
        if not strong_buys.empty:
            fig.add_trace(go.Scatter(
                x=strong_buys.index,
                y=strong_buys['Close'],
                mode='markers',
                name=labels['Strong_Buy'],
                marker=dict(size=10, color='lime', symbol='circle', 
                           line=dict(width=1, color='darkgreen')),
                showlegend=(i==1)
            ), row=i, col=1)
        
        sells = df[df['Sell_Signal_display'] == True]
        if not sells.empty:
            fig.add_trace(go.Scatter(
                x=sells.index,
                y=sells['Close'],
                mode='markers',
                name=labels['Sell_Signal'],
                marker=dict(size=10, color='red', symbol='circle',
                           line=dict(width=1, color='darkred')),
                showlegend=(i==1)
            ), row=i, col=1)
        
        # Update y-axis label
        fig.update_yaxes(title_text="Price ($)", row=i, col=1)
    
    # Update layout
    fig.update_layout(
        height=400 * num_periods,
        width=1400,
        title_text=f'{ticker} Multi-Timeframe Analysis',
        showlegend=True,
        hovermode='x unified',
        template='plotly_white'
    )
    
    # Save or show
    if save_path:
        fig.write_html(save_path)
        print(f"Multi-timeframe chart saved to {save_path}")
    
    if show:
        fig.show()


# Utility functions for compatibility

def get_chart_filename(ticker: str, period: str, start_date: str, end_date: str) -> str:
    """
    Generate standardized chart filename (HTML instead of PNG).
    
    Args:
        ticker (str): Stock ticker symbol
        period (str): Analysis period
        start_date (str): Start date in YYYYMMDD format
        end_date (str): End date in YYYYMMDD format
        
    Returns:
        str: Standardized chart filename
    """
    return f"{ticker}_{period}_{start_date}_{end_date}_chart.html"


def validate_chart_data(df: pd.DataFrame) -> bool:
    """
    Validate that DataFrame contains required columns for charting.
    
    Args:
        df (pd.DataFrame): DataFrame to validate
        
    Returns:
        bool: True if valid
        
    Raises:
        ValueError: If required columns are missing
    """
    required_columns = [
        'Close', 'Volume', 'VWAP', 'Support_Level', 'OBV', 'AD_Line',
        'Phase', 'Accumulation_Score', 'Exit_Score', 'Strong_Buy_display'
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValueError(f"Missing required columns for charting: {missing_columns}")
    
    return True
