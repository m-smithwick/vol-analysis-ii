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

# Import empirically validated thresholds
from threshold_config import OPTIMAL_THRESHOLDS, get_threshold_summary, get_threshold_quality
import signal_generator
from signal_metadata import get_display_name

STEALTH_DISPLAY = get_display_name('Stealth_Accumulation')
MODERATE_DISPLAY = get_display_name('Moderate_Buy')
PROFIT_DISPLAY = get_display_name('Profit_Taking')

def calculate_batch_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate batch processing metrics using empirically validated thresholds.
    
    Uses signal_generator functions with OPTIMAL_THRESHOLDS from threshold_config.py
    to ensure consistent scoring methodology across the system.
    
    Args:
        df (pd.DataFrame): Analysis results dataframe with required score columns
        
    Returns:
        Dict[str, Any]: Dictionary with all signal metrics and threshold compliance
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
    
    return {
        # OPTIMAL ENTRY - Moderate Buy (empirically validated: ≥6.5 threshold for 64.3% win rate)
        'moderate_buy_score': current_moderate_score,
        'moderate_exceeds_threshold': moderate_exceeds_threshold,
        'moderate_threshold': moderate_threshold,
        'moderate_signal_active': moderate_signal_active,
        'strong_signal_active': strong_signal_active,
        'confluence_signal_active': confluence_signal_active,
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
        'exit_score': df['Exit_Score'].iloc[-1] if 'Exit_Score' in df.columns else 0
    }


def generate_html_summary(results: List[Dict], errors: List[Dict], period: str, 
                         output_dir: str, timestamp: str,
                         chart_backend: str = 'matplotlib') -> str:
    """
    Generate interactive HTML summary with clickable charts focused on optimal strategies.
    
    Args:
        results (List[Dict]): Processed ticker results
        errors (List[Dict]): Processing errors  
        period (str): Analysis period
        output_dir (str): Output directory path
        timestamp (str): Timestamp for filename
        chart_backend (str): Chart engine to determine embed type/extension
        
    Returns:
        str: HTML filename
    """
    normalized_backend = (chart_backend or 'matplotlib').lower()
    is_plotly_backend = normalized_backend == 'plotly'
    chart_extension = 'html' if is_plotly_backend else 'png'
    
    # Filter for ACTIVE signals only, then sort by score
    active_moderate = [r for r in results if r['moderate_signal_active']]
    active_profit = [r for r in results if r['profit_signal_active']]
    active_stealth = [r for r in results if r['stealth_signal_active']]
    
    sorted_moderate_buy_results = sorted(active_moderate, key=lambda x: x['moderate_buy_score'], reverse=True)
    sorted_profit_taking_results = sorted(active_profit, key=lambda x: x['profit_taking_score'], reverse=True)
    sorted_stealth_results = sorted(active_stealth, key=lambda x: x['stealth_score'], reverse=True)
    
    def build_chart_filename(result_entry: Dict[str, Any]) -> Optional[str]:
        """Construct the expected chart filename (PNG or HTML) from the analysis filename."""
        parts = result_entry['filename'].split('_')
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
        </div>
        
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
    html_filename = f"batch_summary_{period}_{timestamp}.html"
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
                 save_charts=False, generate_html=True, verbose=True,
                 chart_backend: str = 'matplotlib'):
    """
    Process multiple tickers from a file and save individual analysis reports.
    
    Args:
        ticker_file (str): Path to file containing ticker symbols
        period (str): Analysis period
        output_dir (str): Directory to save output files
        save_charts (bool): Whether to save chart images
        generate_html (bool): Whether to generate interactive HTML summary
        verbose (bool): Print progress output during batch processing
        chart_backend (str): Chart engine ('matplotlib' PNG or 'plotly' HTML) passed to analyze_ticker
        
    Raises:
        DataValidationError: If input parameters are invalid
        FileOperationError: If file operations fail
    """
    # Import analyze_ticker function from vol_analysis
    from vol_analysis import analyze_ticker
    
    with ErrorContext("batch processing tickers", ticker_file=ticker_file, period=period):
        # Validate inputs
        validate_file_path(ticker_file, check_exists=True, check_readable=True)
        validate_period(period)
        
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
        print(f"🎨 Chart backend: {chart_backend}")
        print("="*50)
    
    # Track results for summary
    results = []
    errors = []
    
    for i, ticker in enumerate(tickers, 1):
        if verbose:
            print(f"\n[{i}/{len(tickers)}] Processing {ticker}...")
        
        try:
            # Use error context for individual ticker processing
            with ErrorContext("processing ticker", ticker=ticker, index=f"{i}/{len(tickers)}"):
                # Analyze ticker with file output (no interactive chart display in batch mode)
                result = analyze_ticker(
                    ticker=ticker,
                    period=period,
                    save_to_file=True,
                    output_dir=output_dir,
                    save_chart=True,  # Always save charts in batch mode (can't display interactively)
                    show_chart=False,  # Don't display charts interactively in batch mode
                    show_summary=False,  # Don't print verbose summaries in batch mode
                    debug=verbose,
                    chart_backend=chart_backend
                )
                
                if isinstance(result, tuple):
                    df, filepath = result
                    filename = os.path.basename(filepath)
                    logger.info(f"Successfully processed {ticker}: {filename}")
                    if verbose:
                        print(f"✅ {ticker}: Analysis saved to {filename}")
                    
                    # Calculate metrics using empirically validated thresholds
                    batch_metrics = calculate_batch_metrics(df)
                    
                    results.append({
                        'ticker': ticker,
                        'filename': filename,
                        **batch_metrics  # Unpack all calculated metrics with threshold compliance
                    })
                    
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
    
    # Generate summary report
    if results:
        active_moderate = [r for r in results if r['moderate_signal_active']]
        sorted_moderate_results = sorted(active_moderate, key=lambda x: x['moderate_buy_score'], reverse=True)
        active_profit = [r for r in results if r['profit_signal_active']]
        sorted_profit_results = sorted(active_profit, key=lambda x: x['profit_taking_score'], reverse=True)
        active_stealth = [r for r in results if r['stealth_signal_active']]
        sorted_stealth_results = sorted(active_stealth, key=lambda x: x['stealth_score'], reverse=True)
        
        if verbose:
            print(f"\n📋 BATCH PROCESSING SUMMARY")
            print("="*60)
            print(f"✅ Successfully processed: {len(results)}/{len(tickers)} tickers")
            
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
        
        summary_filename = f"batch_summary_{period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        summary_filepath = os.path.join(output_dir, summary_filename)
        
        try:
            with open(summary_filepath, 'w') as f:
                f.write("BATCH PROCESSING SUMMARY\n")
                f.write("="*60 + "\n\n")
                f.write(f"Processing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Period: {period}\n")
                f.write(f"Total Tickers: {len(tickers)}\n")
                f.write(f"Successfully Processed: {len(results)}\n")
                f.write(f"Errors: {len(errors)}\n\n")
                
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
                        f.write(f"{i:<4} {result['ticker']:<6} {result['moderate_buy_score']:<7.1f} "
                               f"{threshold_status}≥{result['moderate_threshold']:<6.1f} {signal_status:<13} {result['recent_moderate_count']:<5} "
                               f"{result['total_moderate_signals']:<5} {result['filename']}\n")
                
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
                        f.write(f"{i:<4} {result['ticker']:<6} {result['profit_taking_score']:<7.1f} "
                               f"{threshold_status}≥{result['profit_threshold']:<6.1f} {signal_status:<13} {result['recent_profit_count']:<5} "
                               f"{result['filename']}\n")
                
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
                        f.write(f"{i:<4} {result['ticker']:<6} {result['stealth_score']:<7.1f} "
                               f"{threshold_status}≥{result['stealth_threshold']:<6.1f} {signal_status:<13} {result['recent_stealth_count']:<5} "
                               f"{result['price_change_pct']:<+7.1f} {result['total_stealth_signals']:<5} {result['filename']}\n")
                
                logger.info(f"Batch summary saved to {summary_filename}")
        
        except Exception as e:
            logger.error(f"Failed to write batch summary file: {str(e)}")
            print(f"⚠️ Warning: Could not save summary file: {str(e)}")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if generate_html:
            if not save_charts:
                if verbose:
                    print(f"\n📊 HTML requested - generating charts for interactive summary...")
                for i, ticker in enumerate([r['ticker'] for r in results[:5]], 1):
                    if verbose:
                        print(f"  Generating chart {i}/5: {ticker}...")
                    try:
                        analyze_ticker(
                            ticker=ticker,
                            period=period,
                            save_to_file=False,
                            output_dir=output_dir,
                            save_chart=True,
                            force_refresh=False,
                            show_chart=False,
                            show_summary=False,
                            debug=verbose,
                            chart_backend=chart_backend
                        )
                    except Exception as e:
                        print(f"    ⚠️ Chart generation failed for {ticker}: {str(e)}")
            
            html_filename = generate_html_summary(
                results, errors, period, output_dir, timestamp, chart_backend=chart_backend
            )
            if verbose:
                print(f"\n🌐 Interactive HTML summary generated: {html_filename}")
                print(f"   📂 Open in VS Code for clickable charts and analysis links")
        
        if verbose:
            print(f"\n📄 Summary report saved: {summary_filename}")
            print(f"📁 All files saved to: {os.path.abspath(output_dir)}")
    
    else:
        print(f"\n❌ No tickers were successfully processed.")
