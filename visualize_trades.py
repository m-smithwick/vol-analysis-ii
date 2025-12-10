#!/usr/bin/env python3
"""
Trade Visualization Script

Visualizes backtest trades on price charts by reading trade data from CSV files.
Shows entry/exit markers with unique symbols for each signal type.

Usage:
    python visualize_trades.py --csv backtest_results/LOG_FILE_stocks_12mo_20251208.csv --ticker AAPL --period 12mo
"""

import pandas as pd
import numpy as np
import argparse
import sys
from datetime import datetime
from pathlib import Path

# Import existing modules
from analysis_service import prepare_analysis_dataframe
from chart_builder_plotly import create_price_chart, create_volume_indicators_chart, create_volume_bars_chart
from config_loader import load_config
from config_name_utils import get_config_name
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# Entry signal symbol mappings
ENTRY_SYMBOLS = {
    'Strong_Buy': {'symbol': 'star', 'color': 'lime', 'size': 20, 'line_color': 'darkgreen'},
    'Moderate_Buy_filtered': {'symbol': 'circle', 'color': 'gold', 'size': 14, 'line_color': 'orange'},
    'Stealth_Accumulation_filtered': {'symbol': 'diamond', 'color': 'cyan', 'size': 12, 'line_color': 'darkcyan'},
    'Confluence_Signal': {'symbol': 'star-triangle-up', 'color': 'magenta', 'size': 18, 'line_color': 'darkmagenta'},
    'Volume_Breakout': {'symbol': 'triangle-up', 'color': 'orangered', 'size': 16, 'line_color': 'darkred'},
}

# Exit signal symbol mappings
EXIT_SYMBOLS = {
    # Signal-based exits
    'Profit_Taking': {'symbol': 'circle', 'color': 'green', 'size': 14, 'line_color': 'darkgreen'},
    'Momentum_Exhaustion': {'symbol': 'x', 'color': 'purple', 'size': 16, 'line_color': 'purple'},
    'Distribution_Warning': {'symbol': 'square', 'color': 'orange', 'size': 12, 'line_color': 'darkorange'},
    'Sell_Signal': {'symbol': 'circle', 'color': 'red', 'size': 14, 'line_color': 'darkred'},
    'Stop_Loss': {'symbol': 'triangle-down', 'color': 'darkred', 'size': 14, 'line_color': 'black'},
    'MA_Crossdown': {'symbol': 'cross', 'color': 'coral', 'size': 14, 'line_color': 'red'},
    
    # Risk management exits (exit_type fallback)
    'TIME_STOP': {'symbol': 'hexagon', 'color': 'gray', 'size': 12, 'line_color': 'darkgray'},
    'HARD_STOP': {'symbol': 'triangle-down', 'color': 'black', 'size': 16, 'line_color': 'red'},
    'TRAIL_STOP': {'symbol': 'triangle-down', 'color': 'forestgreen', 'size': 14, 'line_color': 'darkgreen'},
    'PROFIT_TARGET': {'symbol': 'star', 'color': 'lightgreen', 'size': 16, 'line_color': 'green'},
    'END_OF_DATA': {'symbol': 'square', 'color': 'lightgray', 'size': 10, 'line_color': 'gray'},
    'SIGNAL_EXIT': {'symbol': 'circle', 'color': 'blue', 'size': 12, 'line_color': 'darkblue'},
}


def extract_config_from_csv(csv_filename: str) -> str:
    """
    Extract config name from CSV filename pattern.
    
    Expected pattern: LOG_FILE_{ticker}_{period}_{config_name}_{timestamp}.csv
    Example: LOG_FILE_SLV_36mo_conservative_20251208_151916.csv -> 'conservative'
    
    Args:
        csv_filename: CSV filename (not full path)
        
    Returns:
        str: Config name or None if pattern doesn't match
    """
    # Remove .csv extension and split by underscore
    base_name = csv_filename.replace('.csv', '')
    parts = base_name.split('_')
    
    # Expected pattern: LOG_FILE_{ticker}_{period}_{config}_{timestamp}
    # Parts: ['LOG', 'FILE', ticker, period, config, timestamp]
    if len(parts) >= 6 and parts[0] == 'LOG' and parts[1] == 'FILE':
        config_name = parts[4]  # 4th index is config name
        return config_name
    
    return None


def read_trade_log(csv_path: str, ticker: str = None) -> pd.DataFrame:
    """
    Read backtest trade log CSV file.
    
    Args:
        csv_path: Path to CSV file
        ticker: Optional ticker filter
        
    Returns:
        DataFrame with trade data
    """
    print(f"📂 Reading trade log: {csv_path}")
    
    # Read CSV
    df = pd.read_csv(csv_path)
    
    # Convert date columns
    df['entry_date'] = pd.to_datetime(df['entry_date'])
    df['exit_date'] = pd.to_datetime(df['exit_date'])
    
    # Filter by ticker if specified
    if ticker:
        df = df[df['ticker'] == ticker].copy()
        print(f"   Filtered to {ticker}: {len(df)} trades")
    
    if len(df) == 0:
        print(f"⚠️  No trades found for {ticker if ticker else 'any ticker'}")
        return df
    
    print(f"   Loaded {len(df)} trades")
    print(f"   Date range: {df['entry_date'].min().strftime('%Y-%m-%d')} to {df['exit_date'].max().strftime('%Y-%m-%d')}")
    
    return df


def get_trade_line_color(profit_pct: float) -> tuple:
    """
    Get line color and style based on profitability.
    
    Args:
        profit_pct: Profit percentage
        
    Returns:
        Tuple of (color, dash_style, opacity)
    """
    if profit_pct > 0:
        return ('green', 'solid', 0.6)
    elif profit_pct > -0.5:
        return ('yellow', 'dash', 0.5)
    elif profit_pct > -5:
        return ('orange', 'dash', 0.5)
    else:
        return ('red', 'solid', 0.6)


def add_trade_markers_to_chart(fig, df_price: pd.DataFrame, trades_df: pd.DataFrame, row: int = 1):
    """
    Add trade entry/exit markers and connection lines to price chart.
    
    Args:
        fig: Plotly figure object
        df_price: DataFrame with price data (for x-axis positioning)
        trades_df: DataFrame with trade data from CSV
        row: Chart row number
    """
    if len(trades_df) == 0:
        print("⚠️  No trades to visualize")
        return
    
    # Create integer-based x-axis mapping (same as price chart)
    x_positions = list(range(len(df_price)))
    date_to_position = {date: pos for pos, date in enumerate(df_price.index)}
    
    print(f"\n📊 Adding {len(trades_df)} trades to chart...")
    
    # Track which symbols we've added to legend
    entry_symbols_added = set()
    exit_symbols_added = set()
    
    # Add connection lines first (bottom layer)
    for idx, trade in trades_df.iterrows():
        entry_date = trade['entry_date']
        exit_date = trade['exit_date']
        
        # Skip if dates not in price data range
        if entry_date not in date_to_position or exit_date not in date_to_position:
            continue
        
        entry_pos = date_to_position[entry_date]
        exit_pos = date_to_position[exit_date]
        
        # Get line styling
        profit_pct = trade['profit_pct']
        line_color, dash_style, opacity = get_trade_line_color(profit_pct)
        
        # Draw connection line
        fig.add_trace(go.Scatter(
            x=[entry_pos, exit_pos],
            y=[trade['entry_price'], trade['exit_price']],
            mode='lines',
            line=dict(color=line_color, dash=dash_style, width=2),
            opacity=opacity,
            showlegend=False,
            hoverinfo='skip'
        ), row=row, col=1)
    
    # Add entry markers
    for idx, trade in trades_df.iterrows():
        entry_date = trade['entry_date']
        
        if entry_date not in date_to_position:
            continue
        
        entry_pos = date_to_position[entry_date]
        primary_signal = trade['primary_signal']
        
        # Get symbol config
        symbol_config = ENTRY_SYMBOLS.get(primary_signal, {
            'symbol': 'circle', 'color': 'blue', 'size': 12, 'line_color': 'darkblue'
        })
        
        # Build hover text
        entry_signals = trade.get('entry_signals_str', primary_signal)
        acc_score = trade.get('accumulation_score', '')
        mb_score = trade.get('moderate_buy_score', '')
        spy_ok = '✅' if trade.get('spy_regime_ok', False) else '❌'
        sector_etf = trade.get('sector_etf', 'N/A')
        sector_ok = '✅' if trade.get('sector_regime_ok', False) else '❌'
        
        hover_text = f"<b>🎯 ENTRY</b><br>"
        hover_text += f"Date: {entry_date.strftime('%Y-%m-%d')}<br>"
        hover_text += f"Price: ${trade['entry_price']:.2f}<br>"
        hover_text += f"Signal: {primary_signal}<br>"
        if entry_signals != primary_signal:
            hover_text += f"All Signals: {entry_signals}<br>"
        hover_text += f"Position: {trade['position_size']} shares<br>"
        if pd.notna(acc_score):
            hover_text += f"Accumulation Score: {acc_score:.1f}<br>"
        if pd.notna(mb_score):
            hover_text += f"Moderate Buy Score: {mb_score:.1f}<br>"
        hover_text += f"Regime: SPY {spy_ok} | {sector_etf} {sector_ok}"
        
        # Add to legend only once per signal type
        show_in_legend = primary_signal not in entry_symbols_added
        if show_in_legend:
            entry_symbols_added.add(primary_signal)
            legend_name = f"📥 {primary_signal.replace('_', ' ')}"
        else:
            legend_name = None
        
        # Add marker
        fig.add_trace(go.Scatter(
            x=[entry_pos],
            y=[trade['entry_price']],
            mode='markers',
            name=legend_name,
            marker=dict(
                size=symbol_config['size'],
                color=symbol_config['color'],
                symbol=symbol_config['symbol'],
                line=dict(width=2, color=symbol_config['line_color'])
            ),
            showlegend=show_in_legend,
            hovertemplate=hover_text + '<extra></extra>'
        ), row=row, col=1)
    
    # Add exit markers
    for idx, trade in trades_df.iterrows():
        exit_date = trade['exit_date']
        
        if pd.isna(exit_date) or exit_date not in date_to_position:
            continue
        
        exit_pos = date_to_position[exit_date]
        
        # Determine exit symbol (prioritize primary_exit_signal over exit_type)
        primary_exit = trade.get('primary_exit_signal', '')
        exit_type = trade.get('exit_type', '')
        
        if primary_exit and primary_exit in EXIT_SYMBOLS:
            exit_key = primary_exit
        elif exit_type and exit_type in EXIT_SYMBOLS:
            exit_key = exit_type
        else:
            # Fallback
            exit_key = 'SIGNAL_EXIT'
        
        # Get symbol config
        symbol_config = EXIT_SYMBOLS.get(exit_key, {
            'symbol': 'circle', 'color': 'gray', 'size': 12, 'line_color': 'darkgray'
        })
        
        # Build hover text
        exit_signals = trade.get('exit_signals_str', exit_key)
        holding_days = (exit_date - trade['entry_date']).days
        
        hover_text = f"<b>🚪 EXIT</b><br>"
        hover_text += f"Date: {exit_date.strftime('%Y-%m-%d')}<br>"
        hover_text += f"Price: ${trade['exit_price']:.2f}<br>"
        if primary_exit:
            hover_text += f"Signal: {primary_exit}<br>"
        hover_text += f"Exit Type: {exit_type}<br>"
        hover_text += f"P&L: {trade['profit_pct']:+.2f}% (${trade['dollar_pnl']:,.0f})<br>"
        hover_text += f"R-Multiple: {trade['r_multiple']:+.2f}R<br>"
        hover_text += f"Held: {holding_days} days"
        
        # Add to legend only once per exit type
        show_in_legend = exit_key not in exit_symbols_added
        if show_in_legend:
            exit_symbols_added.add(exit_key)
            legend_name = f"📤 {exit_key.replace('_', ' ')}"
        else:
            legend_name = None
        
        # Add marker
        fig.add_trace(go.Scatter(
            x=[exit_pos],
            y=[trade['exit_price']],
            mode='markers',
            name=legend_name,
            marker=dict(
                size=symbol_config['size'],
                color=symbol_config['color'],
                symbol=symbol_config['symbol'],
                line=dict(width=2, color=symbol_config['line_color'])
            ),
            showlegend=show_in_legend,
            hovertemplate=hover_text + '<extra></extra>'
        ), row=row, col=1)
    
    print(f"✅ Added {len(entry_symbols_added)} entry signal types")
    print(f"✅ Added {len(exit_symbols_added)} exit signal types")


def generate_trade_visualization_chart(
    df_price: pd.DataFrame,
    trades_df: pd.DataFrame,
    ticker: str,
    period: str,
    save_path: str = None,
    config: dict = None
):
    """
    Generate complete chart with price data and trade overlays.
    Includes interactive time range selector buttons (1m, 3m, 6m, 12m, All).
    
    Args:
        df_price: DataFrame with price/signal data
        trades_df: DataFrame with trade data from CSV
        ticker: Stock ticker
        period: Analysis period
        save_path: Path to save HTML file
        config: Optional config dict for metadata display
    """
    print(f"\n📊 Generating trade visualization chart for {ticker}...")
    
    # Create 3-panel subplot
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(
            f'{ticker} — Trade Visualization ({period})',
            'Volume Indicators',
            'Volume & Entry/Exit Scores'
        ),
        specs=[[{"secondary_y": False}],
               [{"secondary_y": False}],
               [{"secondary_y": True}]]
    )
    
    # Create standard price chart with signals (hide signal legends to avoid duplicates with trade markers)
    create_price_chart(fig, df_price, ticker, period, row=1, config=config, show_signal_legends=False)
    create_volume_indicators_chart(fig, df_price, row=2)
    create_volume_bars_chart(fig, df_price, row=3)
    
    # Add trade markers on top
    add_trade_markers_to_chart(fig, df_price, trades_df, row=1)
    
    # Generate custom date ticks for full data range
    num_days = len(df_price)
    if num_days <= 50:
        interval = 5
        date_format = '%b %d'
    elif num_days <= 130:
        interval = 10
        date_format = '%b %d'
    else:
        interval = 21
        date_format = '%b %Y'
    
    tick_positions = []
    tick_labels = []
    tick_positions.append(0)
    tick_labels.append(df_price.index[0].strftime(date_format))
    for i in range(interval, len(df_price), interval):
        tick_positions.append(i)
        tick_labels.append(df_price.index[i].strftime(date_format))
    if tick_positions[-1] != len(df_price) - 1:
        tick_positions.append(len(df_price) - 1)
        tick_labels.append(df_price.index[-1].strftime(date_format))
    
    # Helper function for dynamic tick generation per range
    def get_ticks_for_range(start_pos, end_pos):
        range_size = end_pos - start_pos + 1
        if range_size <= 50:
            interval = 5
            date_format = '%b %d'
        elif range_size <= 130:
            interval = 7
            date_format = '%b %d'
        else:
            interval = 21
            date_format = '%b %Y'
        
        ticks = [start_pos]
        labels = [df_price.index[start_pos].strftime(date_format)]
        
        for i in range(start_pos + interval, end_pos, interval):
            ticks.append(i)
            labels.append(df_price.index[i].strftime(date_format))
        
        if ticks[-1] != end_pos:
            ticks.append(end_pos)
            labels.append(df_price.index[end_pos].strftime(date_format))
        
        return ticks, labels
    
    # Helper function for y-axis range calculation with 2% padding
    def get_y_axis_ranges(start_pos, end_pos):
        visible_df = df_price.iloc[start_pos:end_pos+1]
        
        # Panel 1: Price chart
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
        
        # Panel 3: Volume bars
        volume_min = visible_df['Volume'].min()
        volume_max = max(visible_df['Volume'].max(), visible_df['Volume_MA'].max())
        volume_padding = (volume_max - volume_min) * 0.02
        volume_range = [volume_min - volume_padding, volume_max + volume_padding]
        
        return price_range, vol_ind_range, volume_range
    
    # Build time range selector buttons
    range_buttons = []
    total_days = len(df_price)
    
    # Define approximate trading days per period
    one_month = 21
    three_months = 63
    six_months = 126
    twelve_months = 252
    
    # 1 Month button
    if total_days > one_month:
        start_pos = total_days - one_month
        end_pos = total_days - 1
        x_range_end = end_pos + 5  # Buffer for regime shapes
        ticks_1m, labels_1m = get_ticks_for_range(start_pos, end_pos)
        price_range_1m, vol_ind_range_1m, volume_range_1m = get_y_axis_ranges(start_pos, end_pos)
        
        range_buttons.append(dict(
            label="1m",
            method="relayout",
            args=[{"xaxis.range": [start_pos, x_range_end],
                   "xaxis2.range": [start_pos, x_range_end],
                   "xaxis3.range": [start_pos, x_range_end],
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
        x_range_end = end_pos + 5
        ticks_3m, labels_3m = get_ticks_for_range(start_pos, end_pos)
        price_range_3m, vol_ind_range_3m, volume_range_3m = get_y_axis_ranges(start_pos, end_pos)
        
        range_buttons.append(dict(
            label="3m",
            method="relayout",
            args=[{"xaxis.range": [start_pos, x_range_end],
                   "xaxis2.range": [start_pos, x_range_end],
                   "xaxis3.range": [start_pos, x_range_end],
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
        x_range_end = end_pos + 5
        ticks_6m, labels_6m = get_ticks_for_range(start_pos, end_pos)
        price_range_6m, vol_ind_range_6m, volume_range_6m = get_y_axis_ranges(start_pos, end_pos)
        
        range_buttons.append(dict(
            label="6m",
            method="relayout",
            args=[{"xaxis.range": [start_pos, x_range_end],
                   "xaxis2.range": [start_pos, x_range_end],
                   "xaxis3.range": [start_pos, x_range_end],
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
        x_range_end = end_pos + 5
        ticks_12m, labels_12m = get_ticks_for_range(start_pos, end_pos)
        price_range_12m, vol_ind_range_12m, volume_range_12m = get_y_axis_ranges(start_pos, end_pos)
        
        range_buttons.append(dict(
            label="12m",
            method="relayout",
            args=[{"xaxis.range": [start_pos, x_range_end],
                   "xaxis2.range": [start_pos, x_range_end],
                   "xaxis3.range": [start_pos, x_range_end],
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
    
    # All button (full data range)
    price_range_all, vol_ind_range_all, volume_range_all = get_y_axis_ranges(0, total_days - 1)
    range_buttons.append(dict(
        label="All",
        method="relayout",
        args=[{"xaxis.range": [0, total_days - 1 + 5],
               "xaxis2.range": [0, total_days - 1 + 5],
               "xaxis3.range": [0, total_days - 1 + 5],
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
    
    # Update layout with time range selector buttons
    fig.update_layout(
        width=1200,
        height=900,
        showlegend=True,
        hovermode='closest',
        template='plotly_white',
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.01
        ),
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Arial",
            font_color="black"
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
    
    # Apply date ticks to all x-axes
    fig.update_xaxes(
        title_text="Date",
        row=3,
        tickmode='array',
        tickvals=tick_positions,
        ticktext=tick_labels,
        tickangle=-45,
        rangeslider_visible=False
    )
    fig.update_xaxes(tickmode='array', tickvals=tick_positions, ticktext=tick_labels, tickangle=-45, row=1)
    fig.update_xaxes(tickmode='array', tickvals=tick_positions, ticktext=tick_labels, tickangle=-45, row=2)
    
    # Add grid
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    
    # Save or show
    if save_path:
        fig.write_html(save_path)
        print(f"✅ Chart saved to {save_path}")
    else:
        fig.show()


def main():
    parser = argparse.ArgumentParser(
        description='Visualize backtest trades on price charts'
    )
    
    parser.add_argument(
        '--csv',
        required=True,
        help='Path to backtest CSV file (LOG_FILE_*.csv)'
    )
    
    parser.add_argument(
        '--ticker',
        required=True,
        help='Ticker symbol to visualize'
    )
    
    parser.add_argument(
        '--period',
        default='12mo',
        help='Analysis period for fetching price data (default: 12mo)'
    )
    
    parser.add_argument(
        '--output',
        help='Output path for HTML file (default: auto-generated)'
    )
    
    parser.add_argument(
        '--config',
        default='configs/conservative_config.yaml',
        help='Path to config file for chart metadata (default: conservative_config.yaml)'
    )
    
    args = parser.parse_args()
    
    # Validate CSV file exists
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"❌ CSV file not found: {args.csv}")
        sys.exit(1)
    
    # Extract config name from CSV filename
    csv_filename = csv_path.name
    extracted_config_name = extract_config_from_csv(csv_filename)
    
    if extracted_config_name:
        print(f"📋 Detected config from CSV filename: {extracted_config_name}")
    
    # Determine which config to load (explicit --config overrides CSV extraction)
    config_path_to_load = None
    final_config_name = None
    
    if args.config and args.config != 'configs/conservative_config.yaml':
        # User explicitly specified a non-default config
        config_path_to_load = args.config
        final_config_name = get_config_name(config_path=args.config)
        print(f"📋 Using explicit config: {args.config}")
    elif extracted_config_name:
        # Use config extracted from CSV filename
        config_path_to_load = f"configs/{extracted_config_name}_config.yaml"
        final_config_name = extracted_config_name
        print(f"📋 Using config from CSV: {config_path_to_load}")
    else:
        # Fallback to default
        config_path_to_load = 'configs/conservative_config.yaml'
        final_config_name = 'conservative'
        print(f"⚠️  Could not extract config from CSV, using default: {config_path_to_load}")
    
    # Load configuration
    config_dict = None
    if config_path_to_load and Path(config_path_to_load).exists():
        try:
            config_loader = load_config(config_path_to_load)
            config_dict = config_loader.config
            print(f"✅ Loaded config: {config_path_to_load}")
        except Exception as e:
            print(f"⚠️  Could not load config: {e}")
            final_config_name = 'default'
    else:
        print(f"⚠️  Config file not found: {config_path_to_load}")
        final_config_name = 'default'
    
    # Read trade log
    trades_df = read_trade_log(args.csv, ticker=args.ticker)
    
    if len(trades_df) == 0:
        print(f"❌ No trades found for {args.ticker} in {args.csv}")
        sys.exit(1)
    
    # Fetch price data
    print(f"\n📈 Fetching price data for {args.ticker}...")
    df_price = prepare_analysis_dataframe(
        ticker=args.ticker,
        period=args.period,
        data_source='yfinance',
        force_refresh=False,
        verbose=True,
        config=config_dict
    )
    
    # Generate output path in backtest_results directory with config name
    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"trade_visualization_{args.ticker}_{args.period}_{final_config_name}_{timestamp}.html"
        output_path = f"backtest_results/{output_filename}"
        
        # Ensure backtest_results directory exists
        Path('backtest_results').mkdir(exist_ok=True)
    
    # Generate chart
    generate_trade_visualization_chart(
        df_price=df_price,
        trades_df=trades_df,
        ticker=args.ticker,
        period=args.period,
        save_path=output_path,
        config=config_dict
    )
    
    print(f"\n✅ Trade visualization complete!")
    print(f"📂 Saved to: {output_path}")
    print(f"🔍 Trades visualized: {len(trades_df)}")


if __name__ == '__main__':
    main()
