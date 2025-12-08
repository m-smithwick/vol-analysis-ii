"""
Batch Processing Module for Volume Analysis
==========================================

This module handles multi-ticker processing and reporting functionality.

Functions:
- calculate_recent_stealth_score(): Calculate recent stealth buying activity
- calculate_recent_entry_score(): Calculate recent strong entry signal activity  
- generate_html_summary(): Generate interactive HTML summary with clickable charts
- process_batch(): Process multiple tickers from a file

Author: Volume Analysis Tool
Date: 2025-11-03
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

# Import error handling framework
from error_handler import (
    ErrorContext, DataValidationError, CacheError, DataDownloadError,
    FileOperationError, validate_ticker, validate_period, validate_dataframe,
    validate_file_path, safe_operation, get_logger, setup_logging
)

# Import utilities
from utils import is_data_stale

# Import empirically validated thresholds
from threshold_config import OPTIMAL_THRESHOLDS, get_threshold_summary, get_threshold_quality
import signal_generator
from signal_metadata import get_display_name

STEALTH_DISPLAY = get_display_name('Stealth_Accumulation')
MODERATE_DISPLAY = get_display_name('Moderate_Buy')
PROFIT_DISPLAY = get_display_name('Profit_Taking')

def export_dataframe_to_excel(df: pd.DataFrame, ticker: str, period: str, 
                             output_dir: str) -> Optional[str]:
    """
    Export analysis DataFrame to Excel file with proper formatting.
    
    Args:
        df (pd.DataFrame): Complete analysis DataFrame with all indicators and signals
        ticker (str): Stock ticker symbol
        period (str): Analysis period
        output_dir (str): Directory to save Excel file
        
    Returns:
        Optional[str]: Excel filename if successful, None if failed
        
    Raises:
        FileOperationError: If Excel export fails
    """
    with ErrorContext("exporting DataFrame to Excel", ticker=ticker, period=period):
        logger = get_logger()
        
        try:
            # Check if openpyxl is available for Excel export
            try:
                import openpyxl
            except ImportError:
                logger.warning("openpyxl not available - Excel export requires: pip install openpyxl")
                raise FileOperationError("Excel export requires openpyxl: pip install openpyxl")
            
            # Generate filename with date range (consistent with existing patterns)
            start_date = df.index[0].strftime('%Y%m%d')
            end_date = df.index[-1].strftime('%Y%m%d')
            excel_filename = f"{ticker}_{period}_{start_date}_{end_date}_data.xlsx"
            excel_filepath = os.path.join(output_dir, excel_filename)
            
            # Validate output directory
            validate_file_path(output_dir, check_exists=True, check_writable=True)
            
            # Prepare DataFrame for Excel export
            df_export = df.copy()
            
            # Ensure the index (dates) is included as a column for Excel
            df_export.reset_index(inplace=True)
            
            # Convert boolean columns to cleaner text for Excel readability
            bool_columns = df_export.select_dtypes(include=['bool']).columns
            for col in bool_columns:
                df_export[col] = df_export[col].map({True: 'TRUE', False: 'FALSE', np.nan: ''})
            
            # Round numeric columns to reasonable precision
            numeric_columns = df_export.select_dtypes(include=[np.number]).columns
            for col in numeric_columns:
                if col not in ['Volume']:  # Keep volume as integers
                    df_export[col] = df_export[col].round(4)
            
            # Export to Excel with multiple sheets for organization
            with pd.ExcelWriter(excel_filepath, engine='openpyxl') as writer:
                # Main data sheet with all columns
                df_export.to_excel(writer, sheet_name='Analysis_Data', index=False)
                
                # Create a summary sheet with key metrics
                summary_data = {
                    'Metric': [
                        'Ticker Symbol',
                        'Analysis Period', 
                        'Date Range',
                        'Total Trading Days',
                        'Current Price',
                        'Current VWAP',
                        'Current Phase',
                        'Accumulation Score (Latest)',
                        'Exit Score (Latest)',
                        'Strong Buy Signals',
                        'Moderate Buy Signals',
                        'Stealth Accumulation Signals',
                        'Profit Taking Signals',
                        'Total Entry Signals',
                        'Total Exit Signals'
                    ],
                    'Value': [
                        ticker,
                        period,
                        f"{df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}",
                        len(df),
                        f"${df['Close'].iloc[-1]:.2f}",
                        f"${df['VWAP'].iloc[-1]:.2f}",
                        df['Phase'].iloc[-1],
                        f"{df['Accumulation_Score'].iloc[-1]:.2f}",
                        f"{df['Exit_Score'].iloc[-1]:.2f}",
                        int(df['Strong_Buy'].sum()) if 'Strong_Buy' in df.columns else 0,
                        int(df['Moderate_Buy'].sum()) if 'Moderate_Buy' in df.columns else 0,
                        int(df['Stealth_Accumulation'].sum()) if 'Stealth_Accumulation' in df.columns else 0,
                        int(df['Profit_Taking'].sum()) if 'Profit_Taking' in df.columns else 0,
                        int(df[['Strong_Buy', 'Moderate_Buy', 'Stealth_Accumulation', 'Confluence_Signal', 'Volume_Breakout']].sum().sum()) if all(col in df.columns for col in ['Strong_Buy', 'Moderate_Buy', 'Stealth_Accumulation']) else 0,
                        int(df[['Profit_Taking', 'Distribution_Warning', 'Sell_Signal', 'Momentum_Exhaustion', 'Stop_Loss']].sum().sum()) if all(col in df.columns for col in ['Profit_Taking', 'Distribution_Warning', 'Sell_Signal']) else 0
                    ]
                }
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                # Format the Excel workbook for better readability
                workbook = writer.book
                
                # Format main data sheet
                worksheet = writer.sheets['Analysis_Data']
                worksheet.freeze_panes = 'B2'  # Freeze first row and Date column
                
                # Auto-adjust column widths (with reasonable limits)
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 20)  # Max width of 20
                    worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Format summary sheet
                summary_worksheet = writer.sheets['Summary'] 
                summary_worksheet.column_dimensions['A'].width = 25
                summary_worksheet.column_dimensions['B'].width = 30
            
            logger.info(f"Excel file exported: {excel_filename}")
            return excel_filename
            
        except Exception as e:
            error_msg = f"Failed to export Excel file for {ticker}: {str(e)}"
            logger.error(error_msg)
            raise FileOperationError(error_msg)

def extract_data_end_date(result: Dict) -> Optional[datetime]:
    """
    Extract the data end date from a result's filename.
    
    Args:
        result: Result dictionary with 'filename' key
        
    Returns:
        datetime object of the data end date, or None if cannot parse
    """
    try:
        # Filename format: TICKER_PERIOD_STARTDATE_ENDDATE_analysis.txt
        filename = result['filename']
        parts = filename.split('_')
        if len(parts) >= 4:
            data_date_str = parts[3]  # e.g., "20251201"
            return datetime.strptime(data_date_str, '%Y%m%d')
    except (ValueError, IndexError, KeyError):
        return None
    return None


def check_data_staleness(results: List[Dict], warning_threshold_hours: int = 24) -> Dict[str, Any]:
    """
    Check if any tickers have stale data and return warning information.
    
    Args:
        results (List[Dict]): Processed ticker results with filenames
        warning_threshold_hours (int): Hours before data is considered stale (default: 24)
        
    Returns:
        Dict[str, Any]: Dictionary with staleness information including:
            - has_stale_data: Whether any stale data exists
            - stale_count: Number of stale tickers
            - stale_tickers: List of stale ticker details
            - max_age_hours: Maximum age in hours
    """
    stale_tickers = []
    max_age_hours = 0
    
    for result in results:
        # Extract data end date from filename (e.g., NBIX_12mo_20241112_20251110_analysis.txt)
        # Format: TICKER_PERIOD_STARTDATE_ENDDATE_analysis.txt
        filename = result.get('filename')
        if not filename:
            # Skip results without filenames (non-actionable tickers didn't get files created)
            continue
        parts = filename.split('_')
        
        if len(parts) >= 4:
            try:
                # Get the end date (4th part before _analysis.txt)
                data_date_str = parts[3]  # e.g., "20251110"
                data_date = datetime.strptime(data_date_str, '%Y%m%d')
                
                # Check if data is stale using shared utility (accounts for weekends)
                if is_data_stale(data_date, warning_threshold_hours):
                    # Calculate age for reporting purposes
                    now = datetime.now()
                    age_hours = (now - data_date).total_seconds() / 3600
                    
                    stale_tickers.append({
                        'ticker': result['ticker'],
                        'data_date': data_date.strftime('%Y-%m-%d'),
                        'age_hours': int(age_hours),
                        'age_days': int(age_hours / 24)
                    })
                    max_age_hours = max(max_age_hours, age_hours)
            except (ValueError, IndexError) as e:
                # If we can't parse the date, skip this ticker
                logger = get_logger()
                logger.warning(f"Could not parse date from filename {filename}: {e}")
                continue
    
    return {
        'has_stale_data': len(stale_tickers) > 0,
        'stale_count': len(stale_tickers),
        'stale_tickers': stale_tickers,
        'max_age_hours': int(max_age_hours),
        'max_age_days': int(max_age_hours / 24) if max_age_hours > 0 else 0
    }

def is_ticker_actionable(metrics: Dict[str, Any]) -> bool:
    """
    Determine if a ticker has actionable buy or sell signals.
    
    Actionable signals are those that:
    1. Are currently active (on the most recent trading day)
    2. Meet empirically validated threshold requirements
    
    Args:
        metrics (Dict[str, Any]): Calculated batch metrics from calculate_batch_metrics()
        
    Returns:
        bool: True if ticker has actionable buy or sell signals
    """
    # Check for actionable BUY signals
    has_actionable_buy = (
        # Moderate Buy: Active + exceeds ≥6.5 threshold (64.3% win rate)
        (metrics['moderate_signal_active'] and metrics['moderate_exceeds_threshold']) or
        # Strong Buy: Always actionable when active
        metrics['strong_signal_active'] or
        # Confluence: Always actionable when active
        metrics['confluence_signal_active'] or
        # Stealth Accumulation: Active + exceeds ≥4.5 threshold (58.7% win rate)
        (metrics['stealth_signal_active'] and metrics['stealth_exceeds_threshold'])
    )
    
    # Check for actionable SELL signals
    has_actionable_sell = (
        # Profit Taking: Active + exceeds ≥7.0 threshold (96.1% win rate)
        metrics['profit_signal_active'] and metrics['profit_exceeds_threshold']
    )
    
    return has_actionable_buy or has_actionable_sell


def calculate_batch_metrics(df: pd.DataFrame, account_value: float = 500000) -> Dict[str, Any]:
    """
    Calculate batch processing metrics using empirically validated thresholds.
    
    Includes position sizing calculations for actionable trade execution.
    Uses signal_generator functions with OPTIMAL_THRESHOLDS from threshold_config.py
    to ensure consistent scoring methodology across the system.
    
    Args:
        df (pd.DataFrame): Analysis results dataframe with required score columns
        account_value (float): Account value for position sizing (default: $500,000)
        
    Returns:
        Dict[str, Any]: Dictionary with all signal metrics, threshold compliance, and position sizing
    """
    # Get empirically validated thresholds
    moderate_threshold = OPTIMAL_THRESHOLDS['moderate_buy']['threshold']
    profit_threshold = OPTIMAL_THRESHOLDS['profit_taking']['threshold'] 
    stealth_threshold = OPTIMAL_THRESHOLDS['stealth_accumulation']['threshold']
    
    # Calculate scores using signal_generator functions (ensures consistency)
    moderate_buy_score = signal_generator.calculate_moderate_buy_score(df)
    profit_taking_score = signal_generator.calculate_profit_taking_score(df)
    stealth_accumulation_score = signal_generator.calculate_stealth_accumulation_score(df)
    
    # Get current scores
    current_moderate_score = moderate_buy_score.iloc[-1] if len(moderate_buy_score) > 0 else 0
    current_profit_score = profit_taking_score.iloc[-1] if len(profit_taking_score) > 0 else 0
    current_stealth_score = stealth_accumulation_score.iloc[-1] if len(stealth_accumulation_score) > 0 else 0
    
    # Check threshold compliance (empirically validated signals)
    moderate_exceeds_threshold = current_moderate_score >= moderate_threshold
    profit_exceeds_threshold = current_profit_score >= profit_threshold
    stealth_exceeds_threshold = current_stealth_score >= stealth_threshold
    
    # Calculate signal counts and current status
    moderate_signals = df[df['Moderate_Buy'] == True]
    profit_signals = df[df['Profit_Taking'] == True] 
    stealth_signals = df[df['Stealth_Accumulation'] == True]
    
    # Current signal status (is there an actionable signal NOW?)
    moderate_signal_active = df['Moderate_Buy'].iloc[-1] if len(df) > 0 else False
    profit_signal_active = df['Profit_Taking'].iloc[-1] if len(df) > 0 else False
    stealth_signal_active = df['Stealth_Accumulation'].iloc[-1] if len(df) > 0 else False
    
    # Also check for Strong_Buy and Confluence signals (primary entry opportunities)
    strong_signal_active = df['Strong_Buy'].iloc[-1] if 'Strong_Buy' in df.columns and len(df) > 0 else False
    confluence_signal_active = df['Confluence_Signal'].iloc[-1] if 'Confluence_Signal' in df.columns and len(df) > 0 else False
    
    # NEW: Check if this is a NEW signal (wasn't active yesterday) to match backtest behavior
    # Backtest only enters on FIRST occurrence of signal, not on continuing signals
    is_new_moderate_signal = False
    is_new_strong_signal = False
    is_new_confluence_signal = False
    
    if len(df) >= 2:
        # Check if signal is new (wasn't active on previous trading day)
        if moderate_signal_active:
            previous_moderate = df['Moderate_Buy'].iloc[-2]
            is_new_moderate_signal = not previous_moderate
        
        if strong_signal_active:
            previous_strong = df['Strong_Buy'].iloc[-2]
            is_new_strong_signal = not previous_strong
        
        if confluence_signal_active:
            previous_confluence = df['Confluence_Signal'].iloc[-2]
            is_new_confluence_signal = not previous_confluence
    else:
        # Only 1 day of data - must be new
        is_new_moderate_signal = moderate_signal_active
        is_new_strong_signal = strong_signal_active
        is_new_confluence_signal = confluence_signal_active
    
    # Overall: is there ANY new entry signal?
    is_new_entry_signal = is_new_moderate_signal or is_new_strong_signal or is_new_confluence_signal
    
    # Recent signal counts (last 5 trading days for actionable recency)
    recent_df = df.tail(5)
    recent_moderate_count = recent_df['Moderate_Buy'].sum()
    recent_profit_count = recent_df['Profit_Taking'].sum()
    recent_stealth_count = recent_df['Stealth_Accumulation'].sum()
    
    # Price change analysis for stealth
    price_change_pct = 0
    if not stealth_signals.empty:
        first_stealth_price = stealth_signals['Close'].iloc[0] if len(stealth_signals) > 1 else stealth_signals['Close'].iloc[-1]
        current_price = df['Close'].iloc[-1]
        price_change_pct = ((current_price - first_stealth_price) / first_stealth_price) * 100
    
    # Position sizing calculations (using RiskManager logic)
    # Only calculate if there's an active signal
    position_sizing = None
    if moderate_signal_active or strong_signal_active or confluence_signal_active:
        current_price = df['Close'].iloc[-1]
        
        # Calculate initial stop using RiskManager method
        # stop = min(swing_low - 0.5*ATR, VWAP - 1*ATR)
        if 'Recent_Swing_Low' in df.columns and 'ATR20' in df.columns and 'VWAP' in df.columns:
            swing_stop = df['Recent_Swing_Low'].iloc[-1] - (0.5 * df['ATR20'].iloc[-1])
            vwap_stop = df['VWAP'].iloc[-1] - (1.0 * df['ATR20'].iloc[-1])
            stop_price = min(swing_stop, vwap_stop)
            
            # Calculate position size
            risk_pct = 0.75  # 0.75% risk per trade
            risk_amount = account_value * (risk_pct / 100)
            risk_per_share = current_price - stop_price
            
            if risk_per_share > 0:
                position_size = int(risk_amount / risk_per_share)
                risk_dollars = position_size * risk_per_share
                total_cost = position_size * current_price  # Total capital required
                
                # Calculate profit targets
                r_distance = risk_per_share
                target_2r = current_price + (2 * r_distance)
                
                position_sizing = {
                    'shares': position_size,
                    'entry_price': current_price,
                    'stop_price': stop_price,
                    'risk_per_share': risk_per_share,
                    'risk_dollars': risk_dollars,
                    'total_cost': total_cost,  # NEW: Total transaction cost
                    'target_2r': target_2r,
                    'r_multiple_distance': r_distance
                }
    
    return {
        # OPTIMAL ENTRY - Moderate Buy (empirically validated: ≥6.5 threshold for 64.3% win rate)
        'moderate_buy_score': current_moderate_score,
        'moderate_exceeds_threshold': moderate_exceeds_threshold,
        'moderate_threshold': moderate_threshold,
        'moderate_signal_active': moderate_signal_active,
        'strong_signal_active': strong_signal_active,
        'confluence_signal_active': confluence_signal_active,
        'is_new_entry_signal': is_new_entry_signal,  # NEW: Is this signal's first occurrence?
        'recent_moderate_count': recent_moderate_count,
        'total_moderate_signals': df['Moderate_Buy'].sum(),
        
        # OPTIMAL EXIT - Profit Taking (empirically validated: ≥7.0 threshold for 96.1% win rate)
        'profit_taking_score': current_profit_score,
        'profit_exceeds_threshold': profit_exceeds_threshold,
        'profit_threshold': profit_threshold,
        'profit_signal_active': profit_signal_active,
        'recent_profit_count': recent_profit_count,
        'total_profit_signals': df['Profit_Taking'].sum(),
        
        # SECONDARY ENTRY - Stealth Accumulation (empirically validated: ≥4.5 threshold for 58.7% win rate)
        'stealth_score': current_stealth_score,
        'stealth_exceeds_threshold': stealth_exceeds_threshold,
        'stealth_threshold': stealth_threshold,
        'stealth_signal_active': stealth_signal_active,
        'recent_stealth_count': recent_stealth_count,
        'price_change_pct': price_change_pct,
        'total_stealth_signals': df['Stealth_Accumulation'].sum(),
        
        # Additional context
        'total_days': len(df),
        'latest_phase': df['Phase'].iloc[-1],
        'exit_score': df['Exit_Score'].iloc[-1] if 'Exit_Score' in df.columns else 0,
        
        # Position sizing for actionable execution
        'position_sizing': position_sizing
    }


def generate_html_summary(results: List[Dict], errors: List[Dict], period: str, 
                         output_dir: str, timestamp: str,
                         chart_backend: str = 'matplotlib', ticker_file_base: str = 'batch') -> str:
    """
    Generate interactive HTML summary with clickable charts focused on optimal strategies.
    
    Args:
        results (List[Dict]): Processed ticker results
        errors (List[Dict]): Processing errors  
        period (str): Analysis period
        output_dir (str): Output directory path
        timestamp (str): Timestamp for filename
        chart_backend (str): Chart engine to determine embed type/extension
        ticker_file_base (str): Base name of ticker file (e.g., "ibd21-nov-17" from "ibd21-nov-17.txt")
        
    Returns:
        str: HTML filename
    """
    normalized_backend = (chart_backend or 'matplotlib').lower()
    is_plotly_backend = normalized_backend == 'plotly'
    chart_extension = 'html' if is_plotly_backend else 'png'
    
    # Check for data staleness
    staleness = check_data_staleness(results)
    
    # Filter for ACTIVE signals only, then sort by score
    active_moderate = [r for r in results if r['moderate_signal_active']]
    active_profit = [r for r in results if r['profit_signal_active']]
    active_stealth = [r for r in results if r['stealth_signal_active']]
    
    sorted_moderate_buy_results = sorted(active_moderate, key=lambda x: x['moderate_buy_score'], reverse=True)
    sorted_profit_taking_results = sorted(active_profit, key=lambda x: x['profit_taking_score'], reverse=True)
    sorted_stealth_results = sorted(active_stealth, key=lambda x: x['stealth_score'], reverse=True)
    
    def build_chart_filename(result_entry: Dict[str, Any]) -> Optional[str]:
        """Construct the expected chart filename (PNG or HTML) from the analysis filename."""
        filename = result_entry.get('filename')
        if not filename:
            return None
        parts = filename.split('_')
        if len(parts) < 4:
            return None
        return f"{result_entry['ticker']}_{period}_{parts[2]}_{parts[3]}_chart.{chart_extension}"
    
    stealth_display = STEALTH_DISPLAY
    moderate_display = MODERATE_DISPLAY
    profit_display = PROFIT_DISPLAY

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Volume Analysis Batch Summary - {period}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            margin: 20px;
            background-color: #f8f9fa;
            color: #333;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 3px solid #007acc;
        }}
        
        .header h1 {{
            color: #007acc;
            margin: 0;
            font-size: 2.2em;
        }}
        
        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        
        .stat-card h3 {{
            margin: 0 0 10px 0;
            font-size: 2em;
        }}
        
        .rankings {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 40px;
            margin-bottom: 40px;
        }}
        
        .ranking-section h2 {{
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }}
        
        .ticker-row {{
            display: grid;
            grid-template-columns: 40px 80px 1fr;
            gap: 15px;
            padding: 12px;
            margin-bottom: 8px;
            background: #f8f9fa;
            border-radius: 6px;
            border-left: 4px solid #007acc;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        
        .ticker-row:hover {{
            background: #e3f2fd;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        
        .rank {{
            font-weight: bold;
            color: #007acc;
            text-align: center;
        }}
        
        .ticker-symbol {{
            font-weight: bold;
            font-size: 1.1em;
            color: #333;
        }}
        
        .ticker-details {{
            font-size: 0.9em;
            color: #666;
        }}
        
        .chart-container {{
            margin-top: 15px;
            padding: 20px;
            background: white;
            border-radius: 8px;
            border: 1px solid #ddd;
            display: none;
        }}
        
        .chart-container.active {{
            display: block;
            animation: slideDown 0.3s ease;
        }}
        
        @keyframes slideDown {{
            from {{ opacity: 0; transform: translateY(-20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .chart-image {{
            max-width: 100%;
            height: auto;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .chart-iframe {{
            width: 100%;
            height: 550px;
            border: none;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .chart-controls {{
            margin-bottom: 15px;
            text-align: center;
        }}
        
        .btn {{
            background: #007acc;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            margin: 0 5px;
            font-size: 0.9em;
            transition: background 0.2s ease;
        }}
        
        .btn:hover {{
            background: #005fa3;
        }}
        
        .error-section {{
            margin-top: 40px;
            padding: 20px;
            background: #fff3cd;
            border-radius: 6px;
            border-left: 4px solid #f39c12;
        }}
        
        .emoji {{
            font-size: 1.2em;
            margin-right: 5px;
        }}
        
        .timestamp {{
            text-align: center;
            color: #666;
            margin-top: 30px;
            font-size: 0.9em;
        }}
        
        @media (max-width: 768px) {{
            .rankings {{
                grid-template-columns: 1fr;
            }}
            .summary-stats {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Volume Analysis Batch Summary</h1>
            <p>Interactive Report for {period} Analysis Period</p>
        </div>
        
        <div class="summary-stats">
            <div class="stat-card">
                <h3>{len(results)}</h3>
                <p>Tickers Processed</p>
            </div>
            <div class="stat-card">
                <h3>{len(active_moderate)}</h3>
                <p>Active {moderate_display} Signals</p>
            </div>
            <div class="stat-card">
                <h3>{len(active_profit)}</h3>
                <p>Active {profit_display} Signals</p>
            </div>
            <div class="stat-card">
                <h3>{len(active_stealth)}</h3>
                <p>Active {stealth_display} Signals</p>
            </div>
        </div>"""
    
    # Add data staleness warning banner if present
    if staleness['has_stale_data']:
        html_content += f"""
        
        <div style="background: #ff4444; color: white; padding: 20px; border-radius: 8px; margin-bottom: 30px; border-left: 6px solid #cc0000;">
            <h2 style="margin: 0 0 10px 0; color: white;">⚠️ DATA STALENESS WARNING</h2>
            <p style="margin: 5px 0; font-size: 1.1em;">
                <strong>{staleness['stale_count']} tickers have data older than 24 hours</strong>
            </p>
            <p style="margin: 5px 0;">
                Oldest data: {staleness['max_age_hours']} hours ({staleness['max_age_days']} days) old
            </p>
            <p style="margin: 10px 0 5px 0; font-weight: bold;">Stale Tickers:</p>
            <ul style="margin: 5px 0;">"""
        for ticker_info in staleness['stale_tickers'][:20]:  # Show up to 20 in HTML
            html_content += f"<li>{ticker_info['ticker']}: {ticker_info['data_date']} ({ticker_info['age_days']}d old)</li>\n"
        if len(staleness['stale_tickers']) > 20:
            html_content += f"<li>... and {len(staleness['stale_tickers']) - 20} more stale tickers</li>\n"
        html_content += """
            </ul>
        </div>"""
    
    html_content += """
        
        <div class="rankings">
            <div class="ranking-section">
                <h2>{stealth_display} Signals</h2>"""
    
    # Add stealth candidates
    for i, result in enumerate(sorted_stealth_results[:15], 1):
        stealth_score = result['stealth_score']
        stealth_active = result['stealth_signal_active']
        recent_count = result['recent_stealth_count']
        price_change = result['price_change_pct']
        
        score_emoji = "🎯" if stealth_score >= 7 else "💎" if stealth_score >= 5 else "👁️" if stealth_score >= 3 else "💤"
        signal_status = "💎 ACTIVE NOW" if stealth_active else "⚪ No Signal"
        
        # Check if chart exists
        chart_filename = build_chart_filename(result)
        chart_exists = chart_filename is not None and os.path.exists(os.path.join(output_dir, chart_filename))
        
        html_content += f"""
                <div class="ticker-row" onclick="toggleChart('stealth_{result['ticker']}')">
                    <div class="rank">#{i}</div>
                    <div class="ticker-symbol">{result['ticker']}</div>
                    <div class="ticker-details">
                        <div><span class="emoji">{score_emoji}</span>Stealth Score: <strong>{stealth_score:.1f}/10</strong></div>
                        <div>Status: {signal_status} | Recent (5d): {recent_count} | Price Change: {price_change:+.1f}%</div>
                    </div>
                </div>"""
        
        if chart_exists:
            chart_embed = (
                f'<iframe src="{chart_filename}" title="{result["ticker"]} Chart" class="chart-iframe"></iframe>'
                if is_plotly_backend
                else f'<img src="{chart_filename}" alt="{result["ticker"]} Chart" class="chart-image">'
            )
            html_content += f"""
                <div id="stealth_{result['ticker']}" class="chart-container">
                    <div class="chart-controls">
                        <button class="btn" onclick="openChart('{chart_filename}')">📊 Open Full Size</button>
                        <button class="btn" onclick="openAnalysis('{result['filename']}')">📋 View Analysis</button>
                    </div>
                    {chart_embed}
                </div>"""
    
    html_content += f"""
            </div>
            
            <div class="ranking-section">
                <h2>🚀 {moderate_display} Signals (Empirically Validated)</h2>"""
    
    # Add moderate buy candidates using empirically validated thresholds
    for i, result in enumerate(sorted_moderate_buy_results[:15], 1):
        moderate_score = result['moderate_buy_score']
        recent_count = result['recent_moderate_count']
        exceeds_threshold = result['moderate_exceeds_threshold']
        threshold = result['moderate_threshold']
        
        # Check for any active entry signal
        moderate_active = result['moderate_signal_active']
        strong_active = result['strong_signal_active']
        confluence_active = result['confluence_signal_active']
        
        score_emoji = "🔥" if moderate_score >= 8 else "⚡" if moderate_score >= 6.5 else "💪" if moderate_score >= 5 else "👁️"
        threshold_status = f"✅ Exceeds {threshold} threshold" if exceeds_threshold else f"❌ Below {threshold} threshold"
        
        # Show current signal status
        if strong_active:
            signal_status = "🟢 STRONG NOW"
        elif confluence_active:
            signal_status = "⭐ CONFLUENCE"
        elif moderate_active:
            signal_status = "🟡 ACTIVE NOW"
        else:
            signal_status = "⚪ No Signal"
        
        # Check if chart exists
        chart_filename = build_chart_filename(result)
        chart_exists = chart_filename is not None and os.path.exists(os.path.join(output_dir, chart_filename))
        
        html_content += f"""
                <div class="ticker-row" onclick="toggleChart('moderate_{result['ticker']}')">
                    <div class="rank">#{i}</div>
                    <div class="ticker-symbol">{result['ticker']}</div>
                    <div class="ticker-details">
                        <div><span class="emoji">{score_emoji}</span>{moderate_display}: <strong>{moderate_score:.1f}/10</strong></div>
                        <div>{threshold_status} | Status: {signal_status} | Recent (5d): {recent_count}</div>
                    </div>
                </div>"""
        
        if chart_exists:
            chart_embed = (
                f'<iframe src="{chart_filename}" title="{result["ticker"]} Chart" class="chart-iframe"></iframe>'
                if is_plotly_backend
                else f'<img src="{chart_filename}" alt="{result["ticker"]} Chart" class="chart-image">'
            )
            html_content += f"""
                <div id="moderate_{result['ticker']}" class="chart-container">
                    <div class="chart-controls">
                        <button class="btn" onclick="openChart('{chart_filename}')">📊 Open Full Size</button>
                        <button class="btn" onclick="openAnalysis('{result['filename']}')">📋 View Analysis</button>
                    </div>
                    {chart_embed}
                </div>"""
    
    html_content += """
            </div>
        </div>"""
    
    # Add errors section if there are any
    if errors:
        html_content += f"""
        <div class="error-section">
            <h3>⚠️ Processing Errors ({len(errors)})</h3>
            <ul>"""
        for error in errors:
            html_content += f"<li><strong>{error['ticker']}</strong>: {error['error']}</li>"
        html_content += """
            </ul>
        </div>"""
    
    # Add footer and JavaScript
    html_content += f"""
        <div class="timestamp">
            Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}
        </div>
    </div>
    
    <script>
        function toggleChart(elementId) {{
            const chart = document.getElementById(elementId);
            if (chart) {{
                chart.classList.toggle('active');
            }}
        }}
        
        function openChart(filename) {{
            // This will attempt to open the chart image in VS Code
            const fullPath = window.location.href.replace(/[^/]*$/, '') + filename;
            window.open(fullPath, '_blank');
        }}
        
        function openAnalysis(filename) {{
            // This will attempt to open the analysis text file
            const fullPath = window.location.href.replace(/[^/]*$/, '') + filename;
            window.open(fullPath, '_blank');
        }}
        
        // Add keyboard shortcuts
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') {{
                // Close all open charts
                document.querySelectorAll('.chart-container.active').forEach(chart => {{
                    chart.classList.remove('active');
                }});
            }}
        }});
    </script>
</body>
</html>"""
    
    # Save HTML file
    html_filename = f"batch_summary_{ticker_file_base}_{period}_{timestamp}.html"
    html_filepath = os.path.join(output_dir, html_filename)
    
    with open(html_filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return html_filename

def read_ticker_file(filepath: str) -> List[str]:
    """
    Read ticker symbols from a text file (one ticker per line).
    
    Args:
        filepath (str): Path to the file containing ticker symbols
        
    Returns:
        List[str]: List of ticker symbols
        
    Raises:
        FileOperationError: If file cannot be read
        DataValidationError: If no valid tickers found
    """
    with ErrorContext("reading ticker file", filepath=filepath):
        # Validate file path and permissions
        validate_file_path(filepath, check_exists=True, check_readable=True)
        
        tickers = []
        try:
            with open(filepath, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    ticker = line.strip().upper()
                    if ticker and not ticker.startswith('#'):  # Skip empty lines and comments
                        try:
                            validated_ticker = validate_ticker(ticker)
                            tickers.append(validated_ticker)
                        except DataValidationError as e:
                            logger = get_logger()
                            logger.warning(f"Invalid ticker on line {line_num}: {ticker} - {e}")
                            continue
        
        except Exception as e:
            raise FileOperationError(f"Error reading file '{filepath}': {str(e)}")
        
        if not tickers:
            raise DataValidationError(f"No valid tickers found in file '{filepath}'")
        
        logger = get_logger()
        logger.info(f"Successfully loaded {len(tickers)} ticker symbols from {filepath}")
        
        return tickers

def process_batch(ticker_file: str, period='12mo', output_dir='results_volume', 
                 save_charts=False, save_excel=False, text_only=False, generate_html=True, verbose=True,
                 chart_backend: str = 'matplotlib', data_source: str = 'yfinance', all_charts=False,
                 config_file: str = None):
    """
    Process multiple tickers from a file and save individual analysis reports.
    
    Args:
        ticker_file (str): Path to file containing ticker symbols
        period (str): Analysis period
        output_dir (str): Directory to save output files
        save_charts (bool): Whether to save chart images
        save_excel (bool): Whether to save Excel files with complete DataFrame data
        text_only (bool): If True, skip all chart generation and HTML summary (fastest mode)
        generate_html (bool): Whether to generate interactive HTML summary (ignored if text_only=True)
        verbose (bool): Print progress output during batch processing
        chart_backend (str): Chart engine ('matplotlib' PNG or 'plotly' HTML) passed to analyze_ticker
        data_source (str): Data source to use ('yfinance' or 'massive')
        all_charts (bool): If True, generate charts for ALL tickers instead of just actionable ones (default: False)
        config_file (str): Optional path to YAML config file (e.g., 'configs/conservative_config.yaml')
        
    Raises:
        DataValidationError: If input parameters are invalid
        FileOperationError: If file operations fail
    """
    # Import analyze_ticker function from vol_analysis
    from vol_analysis import analyze_ticker
    from config_loader import load_config
    
    with ErrorContext("batch processing tickers", ticker_file=ticker_file, period=period):
        # Validate inputs
        validate_file_path(ticker_file, check_exists=True, check_readable=True)
        validate_period(period)
        
        # Extract ticker list base name (e.g., "ibd21-nov-17" from "ticker_lists/ibd21-nov-17.txt")
        ticker_file_base = os.path.splitext(os.path.basename(ticker_file))[0]
        
        logger = get_logger()
        logger.info(f"Starting batch processing: {ticker_file} for period {period}")
        
        # Read tickers from file
        try:
            tickers = read_ticker_file(ticker_file)
        except (FileOperationError, DataValidationError) as e:
            # Re-raise our custom exceptions
            raise e
        except Exception as e:
            raise FileOperationError(f"Failed to read ticker file: {str(e)}")
        
        if not tickers:
            raise DataValidationError("No valid tickers found in file")
        
        # Create output directory if it doesn't exist
        try:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                logger.info(f"Created output directory: {output_dir}")
                if verbose:
                    print(f"📁 Created output directory: {output_dir}")
            
            # Validate output directory is writable
            validate_file_path(output_dir, check_exists=True, check_writable=True)
            
        except Exception as e:
            raise FileOperationError(f"Failed to create or access output directory '{output_dir}': {str(e)}")
    
    if verbose:
        print(f"\n🚀 BATCH PROCESSING {len(tickers)} TICKERS")
        print("="*50)
        print(f"📁 Output directory: {output_dir}")
        print(f"📅 Period: {period}")
        print(f"📊 Save charts: {'Yes' if save_charts else 'No'}")
        print(f"📊 Save Excel: {'Yes' if save_excel else 'No'}")
        print(f"🎨 Chart backend: {chart_backend}")
        print("="*50)
    
    # Load config if provided
    config = None
    if config_file:
        try:
            config_loader = load_config(config_file)
            config = config_loader.config
            if verbose:
                print(f"📋 Loaded config: {config.get('config_name', 'Unknown')}")
        except Exception as e:
            logger.warning(f"Could not load config file {config_file}: {e}")
            if verbose:
                print(f"⚠️  Could not load config: {e}")
    
    # Track results for summary
    results = []
    errors = []
    
    # ============================================================================
    # PASS 1: Analyze all tickers and calculate metrics (NO FILES, NO CHARTS)
    # ============================================================================
    if verbose:
        print(f"\n📊 PASS 1: Analyzing {len(tickers)} tickers (calculating metrics only, no files)...")
    
    for i, ticker in enumerate(tickers, 1):
        if verbose:
            print(f"[{i}/{len(tickers)}] {ticker}...", end=' ')
        
        try:
            # Use error context for individual ticker processing
            with ErrorContext("processing ticker", ticker=ticker, index=f"{i}/{len(tickers)}"):
                # Analyze ticker WITHOUT saving any files (just get DataFrame)
                df = analyze_ticker(
                    ticker=ticker,
                    period=period,
                    save_to_file=False,  # NO FILES in Pass 1
                    output_dir=output_dir,
                    save_chart=False,  # NO CHARTS in Pass 1
                    show_chart=False,
                    show_summary=False,
                    debug=False,  # Quiet mode for metrics calculation
                    chart_backend=chart_backend,
                    data_source=data_source,
                    config=config  # CRITICAL: Pass config for MA_Crossdown and other exit signal params
                )
                
                # Calculate metrics using empirically validated thresholds
                batch_metrics = calculate_batch_metrics(df)
                
                results.append({
                    'ticker': ticker,
                    'df': df,  # Store DataFrame for Pass 2
                    **batch_metrics
                })
                
                if verbose:
                    print(f"✅")
                    
        except DataDownloadError as e:
            # Handle data availability errors more gracefully
            if "No data available" in str(e) or "possibly delisted" in str(e):
                logger.warning(f"No data available for {ticker}: possibly delisted or invalid symbol")
                print(f"⚠️  {ticker}: No data available (possibly delisted or invalid symbol)")
                errors.append({'ticker': ticker, 'error': 'No data available (possibly delisted)'})
            else:
                logger.error(f"Data download failed for {ticker}: {str(e)}")
                print(f"❌ {ticker}: {str(e)}")
                errors.append({'ticker': ticker, 'error': str(e)})
            continue
            
        except (DataValidationError, CacheError, FileOperationError) as e:
            # Handle our custom exceptions
            logger.error(f"Processing failed for {ticker}: {str(e)}")
            print(f"❌ {ticker}: {str(e)}")
            errors.append({'ticker': ticker, 'error': str(e)})
            continue
            
        except Exception as e:
            # Handle any unexpected errors
            error_msg = f"Unexpected error processing {ticker}: {str(e)}"
            logger.error(error_msg)
            print(f"❌ {error_msg}")
            errors.append({'ticker': ticker, 'error': str(e)})
            continue
    
    # ============================================================================
    # PASS 2: Save files (text + charts + Excel) for selected tickers
    # ============================================================================
    # Filter tickers based on all_charts flag
    if all_charts:
        chart_results = results  # Process ALL tickers
        if verbose:
            print(f"\n📊 PASS 2: Creating files for ALL {len(chart_results)} tickers...")
            print(f"   (--all-charts mode: generating charts for every ticker)")
    else:
        # Default: Filter for actionable tickers only
        chart_results = [r for r in results if is_ticker_actionable(r)]
        if verbose:
            print(f"\n📊 PASS 2: Creating files for {len(chart_results)} actionable tickers...")
            print(f"   (Files only created for tickers with active + validated signals)")
            print(f"   Skipping {len(results) - len(chart_results)} non-actionable tickers")
    
    if chart_results:
        
        for i, result in enumerate(chart_results, 1):
            ticker = result['ticker']
            df = result['df']  # Get DataFrame from Pass 1
            
            if verbose:
                # Show signal type for context
                signal_types = []
                if result['strong_signal_active']:
                    signal_types.append('Strong Buy')
                elif result['confluence_signal_active']:
                    signal_types.append('Confluence')
                elif result['moderate_signal_active'] and result['moderate_exceeds_threshold']:
                    signal_types.append('Moderate Buy')
                if result['stealth_signal_active'] and result['stealth_exceeds_threshold']:
                    signal_types.append('Stealth')
                if result['profit_signal_active'] and result['profit_exceeds_threshold']:
                    signal_types.append('Profit Taking')
                
                signal_str = ', '.join(signal_types) if signal_types else 'Unknown'
                print(f"  [{i}/{len(chart_results)}] {ticker} ({signal_str})...", end=' ')
            
            try:
                # Generate filename with date range (same format as before)
                start_date = df.index[0].strftime('%Y%m%d')
                end_date = df.index[-1].strftime('%Y%m%d')
                
                # Save text analysis file
                from vol_analysis import generate_analysis_text
                analysis_text = generate_analysis_text(ticker, df, period)
                text_filename = f"{ticker}_{period}_{start_date}_{end_date}_analysis.txt"
                text_filepath = os.path.join(output_dir, text_filename)
                
                with open(text_filepath, 'w') as f:
                    f.write(analysis_text)
                
                # Update result with filename for HTML generation
                result['filename'] = text_filename
                
                # Save chart if requested
                if not text_only and (save_charts or generate_html):
                    # Respect the chart_backend parameter
                    normalized_backend = (chart_backend or 'matplotlib').lower()
                    is_plotly = normalized_backend == 'plotly'
                    
                    if is_plotly:
                        # Use plotly for HTML charts
                        from chart_builder_plotly import generate_analysis_chart as generate_chart_plotly
                        chart_filename = f"{ticker}_{period}_{start_date}_{end_date}_chart.html"
                        chart_path = os.path.join(output_dir, chart_filename)
                        generate_chart_plotly(df=df, ticker=ticker, period=period,
                                            save_path=chart_path, show=False, config=config)
                    else:
                        # Use matplotlib for PNG charts
                        from chart_builder import generate_analysis_chart
                        chart_filename = f"{ticker}_{period}_{start_date}_{end_date}_chart.png"
                        chart_path = os.path.join(output_dir, chart_filename)
                        generate_analysis_chart(df=df, ticker=ticker, period=period, 
                                              save_path=chart_path, show=False, config=config)
                
                # Save Excel if requested
                if save_excel:
                    try:
                        excel_filename = export_dataframe_to_excel(df, ticker, period, output_dir)
                        result['excel_filename'] = excel_filename
                    except Exception as e:
                        logger = get_logger()
                        logger.warning(f"Excel export failed for {ticker}: {str(e)}")
                
                if verbose:
                    print(f"✅")
                    
            except Exception as e:
                logger = get_logger()
                logger.error(f"File generation failed for {ticker}: {str(e)}")
                if verbose:
                    print(f"⚠️  Failed: {str(e)}")
    else:
        if verbose:
            print(f"\n📊 PASS 2: No actionable tickers found - no files will be created")
            print(f"   All {len(results)} tickers lack active signals meeting empirical thresholds")
    
    # Generate summary report
    if results:
        # Filter for ACTIVE signals that ALSO meet empirically validated thresholds
        # This ensures only actionable, statistically validated signals are shown
        active_moderate = [r for r in results if r['moderate_signal_active'] and r['moderate_exceeds_threshold']]
        sorted_moderate_results = sorted(active_moderate, key=lambda x: x['moderate_buy_score'], reverse=True)
        active_profit = [r for r in results if r['profit_signal_active'] and r['profit_exceeds_threshold']]
        sorted_profit_results = sorted(active_profit, key=lambda x: x['profit_taking_score'], reverse=True)
        active_stealth = [r for r in results if r['stealth_signal_active'] and r['stealth_exceeds_threshold']]
        sorted_stealth_results = sorted(active_stealth, key=lambda x: x['stealth_score'], reverse=True)
        
        # Check for data staleness
        staleness = check_data_staleness(results)
        
        if verbose:
            print(f"\n📋 BATCH PROCESSING SUMMARY")
            print("="*60)
            print(f"✅ Successfully processed: {len(results)}/{len(tickers)} tickers")
            
            # Display data staleness warning prominently if present
            if staleness['has_stale_data']:
                print(f"\n⚠️  DATA STALENESS WARNING")
                print("="*60)
                print(f"🔴 {staleness['stale_count']} tickers have data older than 24 hours")
                print(f"   Oldest data: {staleness['max_age_hours']} hours ({staleness['max_age_days']} days) old")
                print(f"\n   Stale tickers:")
                for ticker_info in staleness['stale_tickers'][:10]:  # Show first 10
                    print(f"   • {ticker_info['ticker']}: {ticker_info['data_date']} ({ticker_info['age_days']}d old)")
                if len(staleness['stale_tickers']) > 10:
                    print(f"   ... and {len(staleness['stale_tickers']) - 10} more")
                print()
            
            if errors:
                print(f"❌ Errors: {len(errors)}")
                for error in errors:
                    print(f"   • {error['ticker']}: {error['error']}")
            
            print(f"\n{MODERATE_DISPLAY} SIGNALS (Empirically validated - ≥6.5 threshold for 64.3% win rate):")
            if not sorted_moderate_results:
                print(f"  No active {MODERATE_DISPLAY} signals at this time.")
            else:
                for i, result in enumerate(sorted_moderate_results[:10], 1):
                    moderate_score = result['moderate_buy_score']
                    recent_count = result['recent_moderate_count']
                    total_moderate = result['total_moderate_signals']
                    exceeds_threshold = result['moderate_exceeds_threshold']
                    threshold = result['moderate_threshold']
                    moderate_active = result['moderate_signal_active']
                    strong_active = result['strong_signal_active']
                    confluence_active = result['confluence_signal_active']
                    
                    score_emoji = "🎯" if moderate_score >= 8 else "🟡" if moderate_score >= 6.5 else "👀" if moderate_score >= 4 else "💤"
                    threshold_emoji = "✅" if exceeds_threshold else "❌"
                    
                    if strong_active:
                        signal_status = "🟢 STRONG NOW"
                    elif confluence_active:
                        signal_status = "⭐ CONFLUENCE"
                    elif moderate_active:
                        signal_status = "🟡 ACTIVE NOW"
                    else:
                        signal_status = "⚪ No Signal"
                    
                    print(f"  {i:2d}. {result['ticker']:5s} - {MODERATE_DISPLAY}: {moderate_score:4.1f}/10 {score_emoji} {threshold_emoji} "
                          f"(≥{threshold} threshold, Status: {signal_status:13s}, Rec5d: {recent_count}, Total: {total_moderate})")
                    
                    # Add position sizing details if available
                    if result.get('position_sizing'):
                        pos = result['position_sizing']
                        print(f"       💰 Transaction: {pos['shares']:,} shares × ${pos['entry_price']:.2f} = ${pos['total_cost']:,.0f}")
                        print(f"       🛑 Stop: ${pos['stop_price']:.2f} | Risk: ${pos['risk_dollars']:.0f} | "
                              f"Target (+2R): ${pos['target_2r']:.2f}")
                
                # Calculate and display daily totals - ONLY for signals from most recent market day
                # Find the most recent data end date across all active signals
                results_with_dates = [(r, extract_data_end_date(r)) for r in sorted_moderate_results if r.get('position_sizing')]
                results_with_dates = [(r, d) for r, d in results_with_dates if d is not None]
                
                if results_with_dates:
                    most_recent_date = max(d for _, d in results_with_dates)
                    
                    # Split into fresh (same day) and stale (old data)
                    fresh_results = [r for r, d in results_with_dates if d == most_recent_date]
                    stale_results = [r for r, d in results_with_dates if d < most_recent_date]
                    
                    # Further filter fresh results to only NEW signals (matches backtest behavior)
                    new_results = [r for r in fresh_results if r.get('is_new_entry_signal', True)]
                    continuing_results = [r for r in fresh_results if not r.get('is_new_entry_signal', True)]
                    
                    # Calculate totals for NEW signals only (matches backtest: only enters on first occurrence)
                    total_capital_required = sum(r['position_sizing']['total_cost'] for r in new_results)
                    total_risk_exposure = sum(r['position_sizing']['risk_dollars'] for r in new_results)
                    num_new_positions = len(new_results)
                    
                    # Calculate amounts for continuing and stale signals
                    continuing_capital = sum(r['position_sizing']['total_cost'] for r in continuing_results)
                    num_continuing = len(continuing_results)
                    excluded_capital = sum(r['position_sizing']['total_cost'] for r in stale_results)
                    excluded_positions = len(stale_results)
                    
                    if num_new_positions > 0 or num_continuing > 0:
                        print(f"\n  {'━' * 70}")
                        if num_new_positions > 0:
                            print(f"  💵 NEW SIGNALS TODAY: ${total_capital_required:,.0f} ({num_new_positions} new positions)")
                            print(f"  📊 Total Risk: ${total_risk_exposure:,.0f} ({total_risk_exposure/500000*100:.2f}% of $500K)")
                            print(f"  📈 Capital Utilization: {total_capital_required/500000*100:.1f}%")
                        if num_continuing > 0:
                            print(f"  🔵 Continuing signals: ${continuing_capital:,.0f} ({num_continuing} already active)")
                        if excluded_positions > 0:
                            print(f"  ⏳ Stale data excluded: ${excluded_capital:,.0f} ({excluded_positions} positions)")
                        print(f"  {'━' * 70}")
            
            print(f"\n{PROFIT_DISPLAY} SIGNALS (Empirically validated - ≥7.0 threshold for 96.1% win rate):")
            if not sorted_profit_results:
                print(f"  No active {PROFIT_DISPLAY} signals at this time.")
            else:
                for i, result in enumerate(sorted_profit_results[:10], 1):
                    profit_score = result['profit_taking_score']
                    profit_active = result['profit_signal_active']
                    recent_count = result['recent_profit_count']
                    exceeds_threshold = result['profit_exceeds_threshold']
                    threshold = result['profit_threshold']
                    
                    score_emoji = "🔥" if profit_score >= 8 else "🟠" if profit_score >= 7.0 else "📈" if profit_score >= 4 else "💤"
                    threshold_emoji = "✅" if exceeds_threshold else "❌"
                    signal_status = "🔴 EXIT NOW!" if profit_active else "⚪ No Signal"
                    
                    print(f"  {i:2d}. {result['ticker']:5s} - {PROFIT_DISPLAY}: {profit_score:4.1f}/10 {score_emoji} {threshold_emoji} "
                          f"(≥{threshold} threshold, Status: {signal_status:13s}, Rec5d: {recent_count})")
            
            print(f"\n{STEALTH_DISPLAY} SIGNALS (Empirically validated - ≥4.5 threshold for 58.7% win rate):")
            if not sorted_stealth_results:
                print(f"  No active {STEALTH_DISPLAY} signals at this time.")
            else:
                for i, result in enumerate(sorted_stealth_results[:5], 1):
                    stealth_score = result['stealth_score']
                    stealth_active = result['stealth_signal_active']
                    recent_count = result['recent_stealth_count']
                    price_change = result['price_change_pct']
                    exceeds_threshold = result['stealth_exceeds_threshold']
                    threshold = result['stealth_threshold']
                    
                    score_emoji = "💎" if stealth_score >= 5 else "👁️" if stealth_score >= 4.5 else "💤"
                    threshold_emoji = "✅" if exceeds_threshold else "❌"
                    signal_status = "💎 ACTIVE NOW" if stealth_active else "⚪ No Signal"
                    
                    print(f"  {i:2d}. {result['ticker']:5s} - {STEALTH_DISPLAY}: {stealth_score:4.1f}/10 {score_emoji} {threshold_emoji} "
                          f"(≥{threshold} threshold, Status: {signal_status:13s}, Rec5d: {recent_count}, Price: {price_change:+4.1f}%)")
        
        summary_filename = f"batch_summary_{ticker_file_base}_{period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        summary_filepath = os.path.join(output_dir, summary_filename)
        
        try:
            with open(summary_filepath, 'w') as f:
                f.write("BATCH PROCESSING SUMMARY\n")
                f.write("="*60 + "\n\n")
                f.write(f"Processing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Period: {period}\n")
                f.write(f"Portfolio Size: $500K\n")
                f.write(f"Total Tickers: {len(tickers)}\n")
                f.write(f"Successfully Processed: {len(results)}\n")
                f.write(f"Errors: {len(errors)}\n\n")
                
                # Add data staleness warning if present
                if staleness['has_stale_data']:
                    f.write("\n⚠️  DATA STALENESS WARNING\n")
                    f.write("="*60 + "\n")
                    f.write(f"🔴 {staleness['stale_count']} TICKERS HAVE STALE DATA (>24h old)\n")
                    f.write(f"   Oldest data is {staleness['max_age_hours']} hours ({staleness['max_age_days']} days) old\n\n")
                    f.write("   Stale tickers:\n")
                    for ticker_info in staleness['stale_tickers']:
                        f.write(f"   • {ticker_info['ticker']}: {ticker_info['data_date']} ({ticker_info['age_days']}d old)\n")
                    f.write("\n" + "="*60 + "\n\n")
                
                if errors:
                    f.write("ERRORS:\n")
                    for error in errors:
                        f.write(f"  • {error['ticker']}: {error['error']}\n")
                    f.write("\n")
                
                f.write(f"{MODERATE_DISPLAY} SIGNALS (Empirically validated - ≥6.5 threshold for 64.3% win rate):\n")
                f.write("-" * 120 + "\n")
                
                if not active_moderate:
                    f.write(f"  No active {MODERATE_DISPLAY} signals at this time.\n\n")
                else:
                    f.write(f"{'Rank':<4} {'Ticker':<6} {MODERATE_DISPLAY:<15} {'Threshold':<9} {'Status':<13} {'Rec5d':<5} {'Total':<5} {'File'}\n")
                    f.write("-" * 120 + "\n")
                    for i, result in enumerate(active_moderate, 1):
                        if result['strong_signal_active']:
                            signal_status = "STRONG NOW"
                        elif result['confluence_signal_active']:
                            signal_status = "CONFLUENCE"
                        elif result['moderate_signal_active']:
                            signal_status = "ACTIVE NOW"
                        else:
                            signal_status = "No Signal"
                        
                        threshold_status = "✅" if result['moderate_exceeds_threshold'] else "❌"
                        filename = result.get('filename', 'N/A')
                        f.write(f"{i:<4} {result['ticker']:<6} {result['moderate_buy_score']:<7.1f} "
                               f"{threshold_status}≥{result['moderate_threshold']:<6.1f} {signal_status:<13} {result['recent_moderate_count']:<5} "
                               f"{result['total_moderate_signals']:<5} {filename}\n")
                        
                        # Add position sizing details if available
                        if result.get('position_sizing'):
                            pos = result['position_sizing']
                            f.write(f"     → Transaction: {pos['shares']:,} shares × ${pos['entry_price']:.2f} = ${pos['total_cost']:,.0f}\n")
                            f.write(f"     → Stop: ${pos['stop_price']:.2f} | Risk: ${pos['risk_dollars']:.0f} | "
                                   f"Target (+2R): ${pos['target_2r']:.2f}\n")
                    
                    # Calculate and display daily totals - ONLY for signals from most recent market day
                    # Find the most recent data end date across all active signals
                    results_with_dates = [(r, extract_data_end_date(r)) for r in active_moderate if r.get('position_sizing')]
                    results_with_dates = [(r, d) for r, d in results_with_dates if d is not None]
                    
                    if results_with_dates:
                        most_recent_date = max(d for _, d in results_with_dates)
                        
                        # Split into fresh (same day) and stale (old data)
                        fresh_results = [r for r, d in results_with_dates if d == most_recent_date]
                        stale_results = [r for r, d in results_with_dates if d < most_recent_date]
                        
                        # Further filter fresh results to only NEW signals (matches backtest behavior)
                        new_results = [r for r in fresh_results if r.get('is_new_entry_signal', True)]
                        continuing_results = [r for r in fresh_results if not r.get('is_new_entry_signal', True)]
                        
                        # Calculate totals for NEW signals only (matches backtest: only enters on first occurrence)
                        total_capital_required = sum(r['position_sizing']['total_cost'] for r in new_results)
                        total_risk_exposure = sum(r['position_sizing']['risk_dollars'] for r in new_results)
                        num_new_positions = len(new_results)
                        
                        # Calculate amounts for continuing and stale signals
                        continuing_capital = sum(r['position_sizing']['total_cost'] for r in continuing_results)
                        num_continuing = len(continuing_results)
                        excluded_capital = sum(r['position_sizing']['total_cost'] for r in stale_results)
                        excluded_positions = len(stale_results)
                        
                        if num_new_positions > 0 or num_continuing > 0:
                            f.write(f"\n{'━' * 80}\n")
                            if num_new_positions > 0:
                                f.write(f"💵 NEW SIGNALS TODAY: ${total_capital_required:,.0f} ({num_new_positions} new positions)\n")
                                f.write(f"📊 Total Risk: ${total_risk_exposure:,.0f} ({total_risk_exposure/500000*100:.2f}% of $500K)\n")
                                f.write(f"📈 Capital Utilization: {total_capital_required/500000*100:.1f}%\n")
                            if num_continuing > 0:
                                f.write(f"🔵 Continuing signals: ${continuing_capital:,.0f} ({num_continuing} already active)\n")
                            if excluded_positions > 0:
                                f.write(f"⏳ Stale data excluded: ${excluded_capital:,.0f} ({excluded_positions} positions)\n")
                            f.write(f"{'━' * 80}\n")
                
                f.write(f"\n{PROFIT_DISPLAY} SIGNALS (Empirically validated - ≥7.0 threshold for 96.1% win rate):\n")
                f.write("-" * 110 + "\n")
                
                if not active_profit:
                    f.write(f"  No active {PROFIT_DISPLAY} signals at this time.\n\n")
                else:
                    f.write(f"{'Rank':<4} {'Ticker':<6} {PROFIT_DISPLAY:<15} {'Threshold':<9} {'Status':<13} {'Rec5d':<5} {'File'}\n")
                    f.write("-" * 110 + "\n")
                    for i, result in enumerate(active_profit, 1):
                        signal_status = "EXIT NOW!" if result['profit_signal_active'] else "No Signal"
                        threshold_status = "✅" if result['profit_exceeds_threshold'] else "❌"
                        filename = result.get('filename', 'N/A')
                        f.write(f"{i:<4} {result['ticker']:<6} {result['profit_taking_score']:<7.1f} "
                               f"{threshold_status}≥{result['profit_threshold']:<6.1f} {signal_status:<13} {result['recent_profit_count']:<5} "
                               f"{filename}\n")
                
                f.write(f"\n{STEALTH_DISPLAY} SIGNALS (Empirically validated - ≥4.5 threshold for 58.7% win rate):\n")
                f.write("-" * 110 + "\n")
                
                if not active_stealth:
                    f.write(f"  No active {STEALTH_DISPLAY} signals at this time.\n\n")
                else:
                    f.write(f"{'Rank':<4} {'Ticker':<6} {STEALTH_DISPLAY:<15} {'Threshold':<9} {'Status':<13} {'Rec5d':<5} {'Price%':<7} {'Total':<5} {'File'}\n")
                    f.write("-" * 110 + "\n")
                    for i, result in enumerate(active_stealth, 1):
                        signal_status = "ACTIVE NOW" if result['stealth_signal_active'] else "No Signal"
                        threshold_status = "✅" if result['stealth_exceeds_threshold'] else "❌"
                        filename = result.get('filename', 'N/A')
                        f.write(f"{i:<4} {result['ticker']:<6} {result['stealth_score']:<7.1f} "
                               f"{threshold_status}≥{result['stealth_threshold']:<6.1f} {signal_status:<13} {result['recent_stealth_count']:<5} "
                               f"{result['price_change_pct']:<+7.1f} {result['total_stealth_signals']:<5} {filename}\n")
                
                logger.info(f"Batch summary saved to {summary_filename}")
        
        except Exception as e:
            logger.error(f"Failed to write batch summary file: {str(e)}")
            print(f"⚠️ Warning: Could not save summary file: {str(e)}")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Generate HTML summary if requested (charts already created in Pass 2)
        if generate_html and not text_only:
            html_filename = generate_html_summary(
                results, errors, period, output_dir, timestamp, chart_backend=chart_backend, ticker_file_base=ticker_file_base
            )
            if verbose:
                print(f"\n🌐 Interactive HTML summary generated: {html_filename}")
                print(f"   📂 Open in VS Code for clickable charts and analysis links")
        elif text_only and verbose:
            print(f"\n⚡ Text-only mode: Skipped chart and HTML generation for maximum speed")
        
        if verbose:
            print(f"\n📄 Summary report saved: {summary_filename}")
            print(f"📁 All files saved to: {os.path.abspath(output_dir)}")
    
    else:
        print(f"\n❌ No tickers were successfully processed.")
