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


def _generate_date_ticks(df: pd.DataFrame, interval_days: int, date_format: str) -> Tuple[list, list]:
    """
    Generate x-axis tick positions and labels for gap-less date plotting.
    
    Args:
        df: DataFrame with DatetimeIndex
        interval_days: Approximate number of trading days between ticks
        date_format: strftime format string for date labels
        
    Returns:
        Tuple of (tick_positions, tick_labels)
    """
    tick_positions = []
    tick_labels = []
    
    # Always include first date
    tick_positions.append(0)
    tick_labels.append(df.index[0].strftime(date_format))
    
    # Add intermediate dates at specified intervals
    for i in range(interval_days, len(df), interval_days):
        tick_positions.append(i)
        tick_labels.append(df.index[i].strftime(date_format))
    
    # Always include last date (if not already included)
    if tick_positions[-1] != len(df) - 1:
        tick_positions.append(len(df) - 1)
        tick_labels.append(df.index[-1].strftime(date_format))
    
    return tick_positions, tick_labels


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
    GAP-LESS PLOTTING: Uses integer positions for x-axis to eliminate weekend/holiday gaps.
    
    Args:
        fig: Plotly figure object
        df (pd.DataFrame): Analysis results dataframe with signals
        ticker (str): Stock ticker symbol
        period (str): Analysis period
        row (int): Subplot row number
    """
    labels = _signal_labels()
    
    # Create integer-based x-axis for gap-less plotting
    x_positions = list(range(len(df)))
    date_strings = df.index.strftime('%Y-%m-%d').tolist()

    # === REGIME STATUS BACKGROUND SHADING ===
    # Shows when market/sector regime allowed signals (green) vs blocked them (red)
    if 'Overall_Regime_OK' in df.columns:
        # Find regime change points
        regime_changes = df['Overall_Regime_OK'].ne(df['Overall_Regime_OK'].shift()).fillna(True)
        change_positions = [i for i, idx in enumerate(df.index) if idx in df[regime_changes].index]
        
        # Add shaded regions as background shapes
        for i in range(len(change_positions)):
            start_pos = change_positions[i]
            end_pos = change_positions[i + 1] if i + 1 < len(change_positions) else len(df) - 1
            
            regime_ok = df.iloc[start_pos]['Overall_Regime_OK']
            
            # Add shape to first subplot (price chart)
            fig.add_shape(
                type="rect",
                xref="x", yref=f"y{'' if row == 1 else row} domain",
                x0=start_pos, x1=end_pos,
                y0=0, y1=1,
                fillcolor="green" if regime_ok else "red",
                opacity=0.15,
                layer="below",
                line_width=0,
                row=row, col=1
            )
    
    # Main price line
    fig.add_trace(go.Scatter(
        x=x_positions,
        y=df['Close'],
        customdata=date_strings,
        mode='lines',
        name='Close Price',
        line=dict(color='black', width=1.5),
        hovertemplate='<b>Close</b><br>Date: %{customdata}<br>Price: $%{y:.2f}<extra></extra>'
    ), row=row, col=1)
    
    # VWAP reference line
    fig.add_trace(go.Scatter(
        x=x_positions,
        y=df['VWAP'],
        customdata=date_strings,
        mode='lines',
        name='VWAP',
        line=dict(color='purple', width=1, dash='dash'),
        opacity=0.7,
        hovertemplate='<b>VWAP</b><br>Date: %{customdata}<br>%{y:.2f}<extra></extra>'
    ), row=row, col=1)
    
    # Long-term moving averages for trend context
    fig.add_trace(go.Scatter(
        x=x_positions,
        y=df['SMA_50'],
        customdata=date_strings,
        mode='lines',
        name='50-day MA',
        line=dict(color='blue', width=1.5),
        opacity=0.8,
        hovertemplate='<b>50-day MA</b><br>Date: %{customdata}<br>%{y:.2f}<extra></extra>'
    ), row=row, col=1)
    
    fig.add_trace(go.Scatter(
        x=x_positions,
        y=df['SMA_200'],
        customdata=date_strings,
        mode='lines',
        name='200-day MA',
        line=dict(color='orangered', width=1.5),
        opacity=0.8,
        hovertemplate='<b>200-day MA</b><br>Date: %{customdata}<br>%{y:.2f}<extra></extra>'
    ), row=row, col=1)
    
    # Swing support and resistance levels
    fig.add_trace(go.Scatter(
        x=x_positions,
        y=df['Recent_Swing_Low'],
        customdata=date_strings,
        mode='lines',
        name='Swing Support',
        line=dict(color='green', width=1, dash='dot'),
        opacity=0.6,
        hovertemplate='<b>Support</b><br>Date: %{customdata}<br>%{y:.2f}<extra></extra>'
    ), row=row, col=1)
    
    fig.add_trace(go.Scatter(
        x=x_positions,
        y=df['Recent_Swing_High'],
        customdata=date_strings,
        mode='lines',
        name='Swing Resistance',
        line=dict(color='red', width=1, dash='dot'),
        opacity=0.6,
        hovertemplate='<b>Resistance</b><br>Date: %{customdata}<br>%{y:.2f}<extra></extra>'
    ), row=row, col=1)
    
    # === ENTRY SIGNALS (Using *_display columns for T+1 visualization) ===
    
    # STRONG BUY SIGNALS (Large Green Dots)
    strong_buys = df[df['Strong_Buy_display'] == True]
    if not strong_buys.empty:
        strong_buy_positions = [i for i, idx in enumerate(df.index) if idx in strong_buys.index]
        strong_buy_dates = [date_strings[i] for i in strong_buy_positions]
        fig.add_trace(go.Scatter(
            x=strong_buy_positions,
            y=strong_buys['Close'].values,
            customdata=strong_buy_dates,
            mode='markers',
            name=labels['Strong_Buy'],
            marker=dict(
                size=15,
                color='lime',
                symbol='circle',
                line=dict(width=2, color='darkgreen')
            ),
            hovertemplate=f'<b>{labels["Strong_Buy"]}</b><br>Date: %{{customdata}}<br>Price: $%{{y:.2f}}<extra></extra>'
        ), row=row, col=1)
    
    # MODERATE BUY SIGNALS (Medium Yellow Dots)
    moderate_buys = df[df['Moderate_Buy_display'] == True]
    if not moderate_buys.empty:
        moderate_buy_positions = [i for i, idx in enumerate(df.index) if idx in moderate_buys.index]
        moderate_buy_dates = [date_strings[i] for i in moderate_buy_positions]
        fig.add_trace(go.Scatter(
            x=moderate_buy_positions,
            y=moderate_buys['Close'].values,
            customdata=moderate_buy_dates,
            mode='markers',
            name=labels['Moderate_Buy'],
            marker=dict(
                size=10,
                color='gold',
                symbol='circle',
                line=dict(width=1.5, color='orange')
            ),
            hovertemplate=f'<b>{labels["Moderate_Buy"]}</b><br>Date: %{{customdata}}<br>Price: $%{{y:.2f}}<extra></extra>'
        ), row=row, col=1)
    
    # STEALTH ACCUMULATION (Diamond Symbols)
    stealth = df[df['Stealth_Accumulation_display'] == True]
    if not stealth.empty:
        stealth_positions = [i for i, idx in enumerate(df.index) if idx in stealth.index]
        stealth_dates = [date_strings[i] for i in stealth_positions]
        fig.add_trace(go.Scatter(
            x=stealth_positions,
            y=stealth['Close'].values,
            customdata=stealth_dates,
            mode='markers',
            name=labels['Stealth_Accumulation'],
            marker=dict(
                size=8,
                color='cyan',
                symbol='diamond',
                opacity=0.8
            ),
            hovertemplate=f'<b>{labels["Stealth_Accumulation"]}</b><br>Date: %{{customdata}}<br>Price: $%{{y:.2f}}<extra></extra>'
        ), row=row, col=1)
    
    # CONFLUENCE SIGNALS (Star Symbols)
    confluence = df[df['Confluence_Signal_display'] == True]
    if not confluence.empty:
        confluence_positions = [i for i, idx in enumerate(df.index) if idx in confluence.index]
        confluence_dates = [date_strings[i] for i in confluence_positions]
        fig.add_trace(go.Scatter(
            x=confluence_positions,
            y=confluence['Close'].values,
            customdata=confluence_dates,
            mode='markers',
            name=labels['Confluence_Signal'],
            marker=dict(
                size=20,
                color='magenta',
                symbol='star'
            ),
            hovertemplate=f'<b>{labels["Confluence_Signal"]}</b><br>Date: %{{customdata}}<br>Price: $%{{y:.2f}}<extra></extra>'
        ), row=row, col=1)
    
    # VOLUME BREAKOUT (Triangle Symbols)
    breakouts = df[df['Volume_Breakout_display'] == True]
    if not breakouts.empty:
        breakout_positions = [i for i, idx in enumerate(df.index) if idx in breakouts.index]
        breakout_dates = [date_strings[i] for i in breakout_positions]
        fig.add_trace(go.Scatter(
            x=breakout_positions,
            y=breakouts['Close'].values,
            customdata=breakout_dates,
            mode='markers',
            name=labels['Volume_Breakout'],
            marker=dict(
                size=12,
                color='orangered',
                symbol='triangle-up',
                line=dict(width=1, color='darkred')
            ),
            hovertemplate=f'<b>{labels["Volume_Breakout"]}</b><br>Date: %{{customdata}}<br>Price: $%{{y:.2f}}<extra></extra>'
        ), row=row, col=1)
    
    # === EXIT SIGNALS (Using *_display columns for T+1 visualization) ===
    
    # PROFIT TAKING (Orange Dots)
    profit_takes = df[df['Profit_Taking_display'] == True]
    if not profit_takes.empty:
        profit_take_positions = [i for i, idx in enumerate(df.index) if idx in profit_takes.index]
        profit_take_dates = [date_strings[i] for i in profit_take_positions]
        fig.add_trace(go.Scatter(
            x=profit_take_positions,
            y=profit_takes['Close'].values,
            customdata=profit_take_dates,
            mode='markers',
            name=labels['Profit_Taking'],
            marker=dict(
                size=12,
                color='orange',
                symbol='circle',
                line=dict(width=2, color='darkorange')
            ),
            hovertemplate=f'<b>{labels["Profit_Taking"]}</b><br>Date: %{{customdata}}<br>Price: $%{{y:.2f}}<extra></extra>'
        ), row=row, col=1)
    
    # DISTRIBUTION WARNING (Gold Squares)
    dist_warnings = df[df['Distribution_Warning_display'] == True]
    if not dist_warnings.empty:
        dist_warning_positions = [i for i, idx in enumerate(df.index) if idx in dist_warnings.index]
        dist_warning_dates = [date_strings[i] for i in dist_warning_positions]
        fig.add_trace(go.Scatter(
            x=dist_warning_positions,
            y=dist_warnings['Close'].values,
            customdata=dist_warning_dates,
            mode='markers',
            name=labels['Distribution_Warning'],
            marker=dict(
                size=10,
                color='gold',
                symbol='square',
                line=dict(width=2, color='darkgoldenrod')
            ),
            hovertemplate=f'<b>{labels["Distribution_Warning"]}</b><br>Date: %{{customdata}}<br>Price: $%{{y:.2f}}<extra></extra>'
        ), row=row, col=1)
    
    # SELL SIGNALS (Red Dots)
    sells = df[df['Sell_Signal_display'] == True]
    if not sells.empty:
        sell_positions = [i for i, idx in enumerate(df.index) if idx in sells.index]
        sell_dates = [date_strings[i] for i in sell_positions]
        fig.add_trace(go.Scatter(
            x=sell_positions,
            y=sells['Close'].values,
            customdata=sell_dates,
            mode='markers',
            name=labels['Sell_Signal'],
            marker=dict(
                size=12,
                color='red',
                symbol='circle',
                line=dict(width=2, color='darkred')
            ),
            hovertemplate=f'<b>{labels["Sell_Signal"]}</b><br>Date: %{{customdata}}<br>Price: $%{{y:.2f}}<extra></extra>'
        ), row=row, col=1)
    
    # MOMENTUM EXHAUSTION (Purple X's)
    momentum_exhausts = df[df['Momentum_Exhaustion_display'] == True]
    if not momentum_exhausts.empty:
        momentum_exhaust_positions = [i for i, idx in enumerate(df.index) if idx in momentum_exhausts.index]
        momentum_exhaust_dates = [date_strings[i] for i in momentum_exhaust_positions]
        fig.add_trace(go.Scatter(
            x=momentum_exhaust_positions,
            y=momentum_exhausts['Close'].values,
            customdata=momentum_exhaust_dates,
            mode='markers',
            name=labels['Momentum_Exhaustion'],
            marker=dict(
                size=12,
                color='purple',
                symbol='x',
            line=dict(width=3)
            ),
            hovertemplate=f'<b>{labels["Momentum_Exhaustion"]}</b><br>Date: %{{customdata}}<br>Price: $%{{y:.2f}}<extra></extra>'
        ), row=row, col=1)
    
    # STOP LOSS TRIGGERS (Dark Red Triangles Down)
    stop_losses = df[df['Stop_Loss_display'] == True]
    if not stop_losses.empty:
        stop_loss_positions = [i for i, idx in enumerate(df.index) if idx in stop_losses.index]
        stop_loss_dates = [date_strings[i] for i in stop_loss_positions]
        fig.add_trace(go.Scatter(
            x=stop_loss_positions,
            y=stop_losses['Close'].values,
            customdata=stop_loss_dates,
            mode='markers',
            name=labels['Stop_Loss'],
            marker=dict(
                size=13,
                color='darkred',
                symbol='triangle-down',
                line=dict(width=2, color='black')
            ),
            hovertemplate=f'<b>{labels["Stop_Loss"]}</b><br>Date: %{{customdata}}<br>Price: $%{{y:.2f}}<extra></extra>'
        ), row=row, col=1)
    
    # === EVENT DAY MARKERS (News/Event Spike Filter) ===
    event_days = df[df['Event_Day'] == True]
    if not event_days.empty:
        event_day_positions = [i for i, idx in enumerate(df.index) if idx in event_days.index]
        event_day_dates = [date_strings[i] for i in event_day_positions]
        fig.add_trace(go.Scatter(
            x=event_day_positions,
            y=event_days['High'].values,
            customdata=event_day_dates,
            mode='markers',
            name='Event Day (News/Earnings)',
            marker=dict(
                size=10,
                color='yellow',
                symbol='triangle-up',
                line=dict(width=2, color='orange'),
                opacity=0.8
            ),
            hovertemplate='<b>Event Day</b><br>Date: %{customdata}<br>High: $%{y:.2f}<extra></extra>'
        ), row=row, col=1)
    
    # Update y-axis
    fig.update_yaxes(title_text="Price ($)", row=row, col=1)


def create_volume_indicators_chart(fig, df: pd.DataFrame, row: int = 2) -> None:
    """
    Create the middle panel volume indicators chart.
    
    GAP-LESS PLOTTING: Uses integer positions for x-axis to eliminate weekend/holiday gaps.
    
    Args:
        fig: Plotly figure object
        df (pd.DataFrame): Analysis results dataframe with indicators
        row (int): Subplot row number
    """
    labels = _signal_labels()
    
    # Create integer-based x-axis for gap-less plotting
    x_positions = list(range(len(df)))
    date_strings = df.index.strftime('%Y-%m-%d').tolist()

    # OBV line
    fig.add_trace(go.Scatter(
        x=x_positions,
        y=df['OBV'],
        customdata=date_strings,
        mode='lines',
        name='OBV',
        line=dict(color='blue', width=2),
        opacity=0.8,
        hovertemplate='<b>OBV</b><br>Date: %{customdata}<br>%{y:,.0f}<extra></extra>'
    ), row=row, col=1)
    
    # A/D Line
    fig.add_trace(go.Scatter(
        x=x_positions,
        y=df['AD_Line'],
        customdata=date_strings,
        mode='lines',
        name='A/D Line',
        line=dict(color='orange', width=2),
        opacity=0.8,
        hovertemplate='<b>A/D Line</b><br>Date: %{customdata}<br>%{y:,.0f}<extra></extra>'
    ), row=row, col=1)
    
    # Moving averages
    fig.add_trace(go.Scatter(
        x=x_positions,
        y=df['OBV_MA'],
        customdata=date_strings,
        mode='lines',
        name='OBV MA',
        line=dict(color='lightblue', width=1, dash='dash'),
        opacity=0.6,
        hovertemplate='<b>OBV MA</b><br>Date: %{customdata}<br>%{y:,.0f}<extra></extra>'
    ), row=row, col=1)
    
    fig.add_trace(go.Scatter(
        x=x_positions,
        y=df['AD_MA'],
        customdata=date_strings,
        mode='lines',
        name='A/D MA',
        line=dict(color='moccasin', width=1, dash='dash'),
        opacity=0.6,
        hovertemplate='<b>A/D MA</b><br>Date: %{customdata}<br>%{y:,.0f}<extra></extra>'
    ), row=row, col=1)
    
    # Add divergence markers
    stealth = df[df['Stealth_Accumulation_display'] == True]
    if not stealth.empty:
        stealth_positions = [i for i, idx in enumerate(df.index) if idx in stealth.index]
        stealth_dates = [date_strings[i] for i in stealth_positions]
        stealth_ad_values = [df.loc[df.index[i], 'AD_Line'] for i in stealth_positions]
        fig.add_trace(go.Scatter(
            x=stealth_positions,
            y=stealth_ad_values,
            customdata=stealth_dates,
            mode='markers',
            name=f"{labels['Stealth_Accumulation']} (on A/D)",
            marker=dict(size=6, color='cyan', symbol='diamond', opacity=0.8),
            showlegend=False,
            hovertemplate=f'<b>{labels["Stealth_Accumulation"]}</b><br>Date: %{{customdata}}<br>%{{y:,.0f}}<extra></extra>'
        ), row=row, col=1)
    
    strong_buys = df[df['Strong_Buy_display'] == True]
    if not strong_buys.empty:
        strong_buy_positions = [i for i, idx in enumerate(df.index) if idx in strong_buys.index]
        strong_buy_dates = [date_strings[i] for i in strong_buy_positions]
        strong_buy_obv_values = [df.loc[df.index[i], 'OBV'] for i in strong_buy_positions]
        fig.add_trace(go.Scatter(
            x=strong_buy_positions,
            y=strong_buy_obv_values,
            customdata=strong_buy_dates,
            mode='markers',
            name=f"{labels['Strong_Buy']} (on OBV)",
            marker=dict(size=8, color='lime', symbol='circle', line=dict(color='darkgreen')),
            showlegend=False,
            hovertemplate=f'<b>{labels["Strong_Buy"]}</b><br>Date: %{{customdata}}<br>%{{y:,.0f}}<extra></extra>'
        ), row=row, col=1)
    
    # Update y-axis
    fig.update_yaxes(title_text="Volume Indicators", row=row, col=1)


def create_volume_bars_chart(fig, df: pd.DataFrame, row: int = 3) -> None:
    """
    Create the bottom panel volume bars and score chart.
    
    GAP-LESS PLOTTING: Uses integer positions for x-axis to eliminate weekend/holiday gaps.
    
    Args:
        fig: Plotly figure object
        df (pd.DataFrame): Analysis results dataframe
        row (int): Subplot row number
    """
    labels = _signal_labels()
    
    # Create integer-based x-axis for gap-less plotting
    x_positions = list(range(len(df)))
    date_strings = df.index.strftime('%Y-%m-%d').tolist()

    # Volume bars with color coding based on phase
    volume_colors = ['red' if phase == 'Distribution' 
                     else 'darkgreen' if phase == 'Strong_Accumulation'
                     else 'lightgreen' if phase == 'Moderate_Accumulation'
                     else 'yellow' if phase == 'Support_Accumulation'
                     else 'lightgray' for phase in df['Phase']]
    
    fig.add_trace(go.Bar(
        x=x_positions,
        y=df['Volume'],
        customdata=date_strings,
        name='Volume',
        marker=dict(color=volume_colors, opacity=0.6),
        hovertemplate='<b>Volume</b><br>Date: %{customdata}<br>%{y:,.0f}<extra></extra>'
    ), row=row, col=1)
    
    # Volume MA line
    fig.add_trace(go.Scatter(
        x=x_positions,
        y=df['Volume_MA'],
        customdata=date_strings,
        mode='lines',
        name='Volume MA',
        line=dict(color='black', width=1),
        opacity=0.8,
        hovertemplate='<b>Volume MA</b><br>Date: %{customdata}<br>%{y:,.0f}<extra></extra>'
    ), row=row, col=1)
    
    # === DUAL SCORING SYSTEM ON SECONDARY Y-AXIS ===
    
    # Accumulation Score (green line)
    fig.add_trace(go.Scatter(
        x=x_positions,
        y=df['Accumulation_Score'],
        customdata=date_strings,
        mode='lines',
        name='Accumulation Score',
        line=dict(color='green', width=2),
        opacity=0.8,
        yaxis='y2',
        hovertemplate='<b>Accumulation Score</b><br>Date: %{customdata}<br>%{y:.1f}<extra></extra>'
    ), row=row, col=1, secondary_y=True)
    
    # Exit Score (red line)
    fig.add_trace(go.Scatter(
        x=x_positions,
        y=df['Exit_Score'],
        customdata=date_strings,
        mode='lines',
        name='Exit Score',
        line=dict(color='red', width=2),
        opacity=0.8,
        yaxis='y2',
        hovertemplate='<b>Exit Score</b><br>Date: %{customdata}<br>%{y:.1f}<extra></extra>'
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
            x=[0, len(df) - 1],
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
        strong_buy_positions = [i for i, idx in enumerate(df.index) if idx in actual_strong_buys.index]
        strong_buy_dates = [date_strings[i] for i in strong_buy_positions]
        fig.add_trace(go.Scatter(
            x=strong_buy_positions,
            y=actual_strong_buys['Accumulation_Score'].values,
            customdata=strong_buy_dates,
            mode='markers',
            name=f"{labels['Strong_Buy']} Signals",
            marker=dict(size=5, color='lime', opacity=0.8),
            yaxis='y2',
            showlegend=False,
            hovertemplate=f'<b>{labels["Strong_Buy"]}</b><br>Date: %{{customdata}}<br>Score: %{{y:.1f}}<extra></extra>'
        ), row=row, col=1, secondary_y=True)
    
    # Mark high exit score points
    high_exit_points = df[df['Exit_Score'] >= 6]
    if not high_exit_points.empty:
        high_exit_positions = [i for i, idx in enumerate(df.index) if idx in high_exit_points.index]
        high_exit_dates = [date_strings[i] for i in high_exit_positions]
        fig.add_trace(go.Scatter(
            x=high_exit_positions,
            y=high_exit_points['Exit_Score'].values,
            customdata=high_exit_dates,
            mode='markers',
            name='High Exit Risk',
            marker=dict(size=4, color='red', symbol='square', opacity=0.8),
            yaxis='y2',
            showlegend=False,
            hovertemplate='<b>High Exit Risk</b><br>Date: %{customdata}<br>Score: %{y:.1f}<extra></extra>'
        ), row=row, col=1, secondary_y=True)
    
    # Mark urgent exit points
    urgent_exit_points = df[df['Exit_Score'] >= 8]
    if not urgent_exit_points.empty:
        urgent_exit_positions = [i for i, idx in enumerate(df.index) if idx in urgent_exit_points.index]
        urgent_exit_dates = [date_strings[i] for i in urgent_exit_positions]
        fig.add_trace(go.Scatter(
            x=urgent_exit_positions,
            y=urgent_exit_points['Exit_Score'].values,
            customdata=urgent_exit_dates,
            mode='markers',
            name='Urgent Exit',
            marker=dict(size=6, color='darkred', symbol='x', opacity=0.9),
            yaxis='y2',
            showlegend=False,
            hovertemplate='<b>Urgent Exit</b><br>Date: %{customdata}<br>Score: %{y:.1f}<extra></extra>'
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
    
    # Generate custom date ticks based on data range
    num_days = len(df)
    if num_days <= 50:  # ~2 months
        # Short period: show dates every 5 trading days
        tick_positions, tick_labels = _generate_date_ticks(df, 5, '%b %d')
    elif num_days <= 130:  # ~6 months
        # Medium period: show dates every 10 trading days
        tick_positions, tick_labels = _generate_date_ticks(df, 10, '%b %d')
    else:
        # Long period: show dates monthly (~21 trading days)
        tick_positions, tick_labels = _generate_date_ticks(df, 21, '%b %Y')
    
    # Create custom range buttons that work with integer x-axis
    # Calculate approximate trading days for each period
    total_days = len(df)
    
    # Define time periods in approximate trading days
    one_month = 21
    three_months = 63
    six_months = 126
    twelve_months = 252
    
    # Helper function to generate tick labels for a specific range
    def get_ticks_for_range(start_pos, end_pos, df_subset):
        """Generate tick positions and labels for a specific date range."""
        range_size = end_pos - start_pos + 1
        
        if range_size <= 50:  # ~1-2 months
            # Weekly ticks: every ~5 trading days
            interval = 5
            date_format = '%b %d'
        elif range_size <= 130:  # ~3-6 months
            # Bi-weekly ticks: every ~7 trading days
            interval = 7
            date_format = '%b %d'
        else:
            # Monthly ticks: every ~21 trading days
            interval = 21
            date_format = '%b %Y'
        
        # Calculate relative tick positions within the range
        relative_ticks = []
        tick_labels = []
        
        # Always include first date
        relative_ticks.append(start_pos)
        tick_labels.append(df.index[start_pos].strftime(date_format))
        
        # Add intermediate ticks
        for i in range(start_pos + interval, end_pos, interval):
            relative_ticks.append(i)
            tick_labels.append(df.index[i].strftime(date_format))
        
        # Always include last date (if not already included)
        if relative_ticks[-1] != end_pos:
            relative_ticks.append(end_pos)
            tick_labels.append(df.index[end_pos].strftime(date_format))
        
        return relative_ticks, tick_labels
    
    # Helper function to calculate y-axis ranges with 2% padding
    def get_y_axis_ranges(start_pos, end_pos):
        """Calculate y-axis ranges for all panels with 2% padding."""
        visible_df = df.iloc[start_pos:end_pos+1]
        
        # Panel 1: Price chart (including moving averages)
        price_values = [
            visible_df['Close'].min(), visible_df['Close'].max(),
            visible_df['VWAP'].min(), visible_df['VWAP'].max(),
            visible_df['SMA_50'].min(), visible_df['SMA_50'].max(),
            visible_df['SMA_200'].min(), visible_df['SMA_200'].max(),
            visible_df['Recent_Swing_Low'].min(), visible_df['Recent_Swing_Low'].max(),
            visible_df['Recent_Swing_High'].min(), visible_df['Recent_Swing_High'].max()
        ]
        price_min = min(price_values)
        price_max = max(price_values)
        price_padding = (price_max - price_min) * 0.02
        price_range = [price_min - price_padding, price_max + price_padding]
        
        # Panel 2: Volume indicators
        vol_ind_values = [
            visible_df['OBV'].min(), visible_df['OBV'].max(),
            visible_df['AD_Line'].min(), visible_df['AD_Line'].max(),
            visible_df['OBV_MA'].min(), visible_df['OBV_MA'].max(),
            visible_df['AD_MA'].min(), visible_df['AD_MA'].max()
        ]
        vol_ind_min = min(vol_ind_values)
        vol_ind_max = max(vol_ind_values)
        vol_ind_padding = (vol_ind_max - vol_ind_min) * 0.02
        vol_ind_range = [vol_ind_min - vol_ind_padding, vol_ind_max + vol_ind_padding]
        
        # Panel 3: Volume bars (primary y-axis only, keep scores at 0-10)
        volume_min = visible_df['Volume'].min()
        volume_max = max(visible_df['Volume'].max(), visible_df['Volume_MA'].max())
        volume_padding = (volume_max - volume_min) * 0.02
        volume_range = [volume_min - volume_padding, volume_max + volume_padding]
        
        return price_range, vol_ind_range, volume_range
    
    # Build button configurations with dynamic tick updates
    range_buttons = []
    
    # 1 Month button
    if total_days > one_month:
        start_pos = total_days - one_month
        end_pos = total_days - 1
        ticks_1m, labels_1m = get_ticks_for_range(start_pos, end_pos, df)
        price_range_1m, vol_ind_range_1m, volume_range_1m = get_y_axis_ranges(start_pos, end_pos)
        
        range_buttons.append(dict(
            label="1m",
            method="relayout",
            args=[{"xaxis.range": [start_pos, end_pos],
                   "xaxis2.range": [start_pos, end_pos],
                   "xaxis3.range": [start_pos, end_pos],
                   "xaxis.tickvals": ticks_1m,
                   "xaxis.ticktext": labels_1m,
                   "xaxis2.tickvals": ticks_1m,
                   "xaxis2.ticktext": labels_1m,
                   "xaxis3.tickvals": ticks_1m,
                   "xaxis3.ticktext": labels_1m,
                   "yaxis.range": price_range_1m,
                   "yaxis2.range": vol_ind_range_1m,
                   "yaxis3.range": volume_range_1m}]
        ))
    
    # 3 Month button
    if total_days > three_months:
        start_pos = total_days - three_months
        end_pos = total_days - 1
        ticks_3m, labels_3m = get_ticks_for_range(start_pos, end_pos, df)
        price_range_3m, vol_ind_range_3m, volume_range_3m = get_y_axis_ranges(start_pos, end_pos)
        
        range_buttons.append(dict(
            label="3m",
            method="relayout",
            args=[{"xaxis.range": [start_pos, end_pos],
                   "xaxis2.range": [start_pos, end_pos],
                   "xaxis3.range": [start_pos, end_pos],
                   "xaxis.tickvals": ticks_3m,
                   "xaxis.ticktext": labels_3m,
                   "xaxis2.tickvals": ticks_3m,
                   "xaxis2.ticktext": labels_3m,
                   "xaxis3.tickvals": ticks_3m,
                   "xaxis3.ticktext": labels_3m,
                   "yaxis.range": price_range_3m,
                   "yaxis2.range": vol_ind_range_3m,
                   "yaxis3.range": volume_range_3m}]
        ))
    
    # 6 Month button
    if total_days > six_months:
        start_pos = total_days - six_months
        end_pos = total_days - 1
        ticks_6m, labels_6m = get_ticks_for_range(start_pos, end_pos, df)
        price_range_6m, vol_ind_range_6m, volume_range_6m = get_y_axis_ranges(start_pos, end_pos)
        
        range_buttons.append(dict(
            label="6m",
            method="relayout",
            args=[{"xaxis.range": [start_pos, end_pos],
                   "xaxis2.range": [start_pos, end_pos],
                   "xaxis3.range": [start_pos, end_pos],
                   "xaxis.tickvals": ticks_6m,
                   "xaxis.ticktext": labels_6m,
                   "xaxis2.tickvals": ticks_6m,
                   "xaxis2.ticktext": labels_6m,
                   "xaxis3.tickvals": ticks_6m,
                   "xaxis3.ticktext": labels_6m,
                   "yaxis.range": price_range_6m,
                   "yaxis2.range": vol_ind_range_6m,
                   "yaxis3.range": volume_range_6m}]
        ))
    
    # 12 Month button
    if total_days > twelve_months:
        start_pos = total_days - twelve_months
        end_pos = total_days - 1
        ticks_12m, labels_12m = get_ticks_for_range(start_pos, end_pos, df)
        price_range_12m, vol_ind_range_12m, volume_range_12m = get_y_axis_ranges(start_pos, end_pos)
        
        range_buttons.append(dict(
            label="12m",
            method="relayout",
            args=[{"xaxis.range": [start_pos, end_pos],
                   "xaxis2.range": [start_pos, end_pos],
                   "xaxis3.range": [start_pos, end_pos],
                   "xaxis.tickvals": ticks_12m,
                   "xaxis.ticktext": labels_12m,
                   "xaxis2.tickvals": ticks_12m,
                   "xaxis2.ticktext": labels_12m,
                   "xaxis3.tickvals": ticks_12m,
                   "xaxis3.ticktext": labels_12m,
                   "yaxis.range": price_range_12m,
                   "yaxis2.range": vol_ind_range_12m,
                   "yaxis3.range": volume_range_12m}]
        ))
    
    # All button - use the original tick labels we calculated
    price_range_all, vol_ind_range_all, volume_range_all = get_y_axis_ranges(0, total_days - 1)
    range_buttons.append(dict(
        label="All",
        method="relayout",
        args=[{"xaxis.range": [0, total_days - 1],
               "xaxis2.range": [0, total_days - 1],
               "xaxis3.range": [0, total_days - 1],
               "xaxis.tickvals": tick_positions,
               "xaxis.ticktext": tick_labels,
               "xaxis2.tickvals": tick_positions,
               "xaxis2.ticktext": tick_labels,
               "xaxis3.tickvals": tick_positions,
               "xaxis3.ticktext": tick_labels,
               "yaxis.range": price_range_all,
               "yaxis2.range": vol_ind_range_all,
               "yaxis3.range": volume_range_all}]
    ))
    
    # Update layout with custom range buttons
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
        ),
        updatemenus=[dict(
            type="buttons",
            direction="left",
            buttons=range_buttons,
            pad={"r": 10, "t": 10},
            showactive=True,
            x=0.0,
            xanchor="left",
            y=1.15,
            yanchor="top"
        )]
    )
    
    # Apply custom date ticks to all x-axes
    fig.update_xaxes(
        title_text="Date",
        row=3,
        tickmode='array',
        tickvals=tick_positions,
        ticktext=tick_labels,
        tickangle=-45,
        rangeslider_visible=False
    )
    
    # Apply same ticks to other panels (without title)
    fig.update_xaxes(
        tickmode='array',
        tickvals=tick_positions,
        ticktext=tick_labels,
        tickangle=-45,
        row=1
    )
    fig.update_xaxes(
        tickmode='array',
        tickvals=tick_positions,
        ticktext=tick_labels,
        tickangle=-45,
        row=2
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
