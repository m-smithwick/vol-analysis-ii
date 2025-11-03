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

def calculate_recent_stealth_score(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate recent stealth buying activity score focusing on recent signals.
    
    Args:
        df (pd.DataFrame): Analysis results dataframe
        
    Returns:
        Dict[str, float]: Dictionary with stealth metrics
    """
    # Focus on recent 10 days for stealth activity
    recent_df = df.tail(10)
    
    # 1. Recent Stealth Signal Count (0-4 points)
    recent_stealth_count = recent_df['Stealth_Accumulation'].sum()
    stealth_recency_score = min(recent_stealth_count * 2, 4)  # Max 4 points
    
    # 2. Days since last stealth signal (0-3 points)
    stealth_signals = df[df['Stealth_Accumulation'] == True]
    if not stealth_signals.empty:
        last_stealth_date = stealth_signals.index[-1]
        days_since_stealth = (df.index[-1] - last_stealth_date).days
        # More recent = higher score
        recency_score = max(3 - (days_since_stealth / 3), 0)  # Max 3 points
    else:
        recency_score = 0
        days_since_stealth = 999
    
    # 3. Price containment during stealth period (0-3 points)
    if not stealth_signals.empty:
        # Get price change from first stealth signal to now
        first_stealth_price = stealth_signals['Close'].iloc[0] if len(stealth_signals) > 1 else stealth_signals['Close'].iloc[-1]
        current_price = df['Close'].iloc[-1]
        price_change_pct = ((current_price - first_stealth_price) / first_stealth_price) * 100
        
        # Lower price appreciation = higher score (what user wants)
        if price_change_pct <= 2:  # Less than 2% gain
            containment_score = 3
        elif price_change_pct <= 5:  # Less than 5% gain
            containment_score = 2
        elif price_change_pct <= 10:  # Less than 10% gain
            containment_score = 1
        else:
            containment_score = 0
    else:
        containment_score = 0
        price_change_pct = 0
    
    # Total stealth score (0-10 scale)
    total_stealth_score = stealth_recency_score + recency_score + containment_score
    
    return {
        'stealth_score': min(total_stealth_score, 10),
        'recent_stealth_count': recent_stealth_count,
        'days_since_stealth': days_since_stealth,
        'price_change_pct': price_change_pct
    }

def calculate_recent_entry_score(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate recent strong entry signal activity score focusing on momentum signals.
    
    Args:
        df (pd.DataFrame): Analysis results dataframe
        
    Returns:
        Dict[str, float]: Dictionary with entry signal metrics
    """
    # Focus on recent 10 days for entry activity
    recent_df = df.tail(10)
    
    # Count different types of entry signals in recent period
    recent_strong_buy = recent_df['Strong_Buy'].sum()
    recent_confluence = recent_df['Confluence_Signal'].sum()
    recent_volume_breakout = recent_df['Volume_Breakout'].sum()
    
    # 1. Signal diversity and strength (0-4 points)
    signal_strength_score = 0
    if recent_strong_buy > 0:
        signal_strength_score += min(recent_strong_buy * 1.5, 2)  # Strong buy signals worth more
    if recent_confluence > 0:
        signal_strength_score += min(recent_confluence * 2, 2)  # Confluence signals are premium
    if recent_volume_breakout > 0:
        signal_strength_score += min(recent_volume_breakout * 1, 1)  # Volume breakouts
    signal_strength_score = min(signal_strength_score, 4)
    
    # 2. Days since last strong entry signal (0-3 points)
    entry_signals = df[(df['Strong_Buy'] == True) | (df['Confluence_Signal'] == True) | (df['Volume_Breakout'] == True)]
    if not entry_signals.empty:
        last_entry_date = entry_signals.index[-1]
        days_since_entry = (df.index[-1] - last_entry_date).days
        # More recent = higher score
        recency_score = max(3 - (days_since_entry / 2), 0)  # Max 3 points, faster decay than stealth
    else:
        recency_score = 0
        days_since_entry = 999
    
    # 3. Signal momentum - are signals increasing or decreasing? (0-3 points)
    # Compare recent 5 days vs previous 5 days
    if len(df) >= 10:
        recent_5 = df.tail(5)
        previous_5 = df.tail(10).head(5)
        
        recent_total = (recent_5['Strong_Buy'].sum() + 
                       recent_5['Confluence_Signal'].sum() + 
                       recent_5['Volume_Breakout'].sum())
        previous_total = (previous_5['Strong_Buy'].sum() + 
                         previous_5['Confluence_Signal'].sum() + 
                         previous_5['Volume_Breakout'].sum())
        
        if recent_total > previous_total:
            momentum_score = 3  # Increasing momentum
            momentum_direction = "up"
        elif recent_total == previous_total and recent_total > 0:
            momentum_score = 2  # Steady momentum
            momentum_direction = "steady"
        elif recent_total > 0:
            momentum_score = 1  # Some activity but declining
            momentum_direction = "down"
        else:
            momentum_score = 0  # No activity
            momentum_direction = "none"
    else:
        momentum_score = 0
        momentum_direction = "none"
    
    # Total entry score (0-10 scale)
    total_entry_score = signal_strength_score + recency_score + momentum_score
    
    return {
        'entry_score': min(total_entry_score, 10),
        'recent_strong_buy': recent_strong_buy,
        'recent_confluence': recent_confluence,
        'recent_volume_breakout': recent_volume_breakout,
        'days_since_entry': days_since_entry,
        'momentum_direction': momentum_direction,
        'total_recent_signals': recent_strong_buy + recent_confluence + recent_volume_breakout
    }

def generate_html_summary(results: List[Dict], errors: List[Dict], period: str, 
                         output_dir: str, timestamp: str) -> str:
    """
    Generate interactive HTML summary with clickable charts.
    
    Args:
        results (List[Dict]): Processed ticker results
        errors (List[Dict]): Processing errors  
        period (str): Analysis period
        output_dir (str): Output directory path
        timestamp (str): Timestamp for filename
        
    Returns:
        str: HTML filename
    """
    # Sort results for both rankings
    sorted_stealth_results = sorted(results, key=lambda x: x['stealth_score'], reverse=True)
    sorted_entry_results = sorted(results, key=lambda x: x['entry_score'], reverse=True)
    
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
                <h3>{len([r for r in results if r['stealth_score'] >= 5])}</h3>
                <p>Strong Stealth Candidates</p>
            </div>
            <div class="stat-card">
                <h3>{len([r for r in results if r['entry_score'] >= 5])}</h3>
                <p>Strong Entry Candidates</p>
            </div>
            <div class="stat-card">
                <h3>{len(errors)}</h3>
                <p>Processing Errors</p>
            </div>
        </div>
        
        <div class="rankings">
            <div class="ranking-section">
                <h2>🎯 Top Stealth Accumulation Candidates</h2>"""
    
    # Add stealth candidates
    for i, result in enumerate(sorted_stealth_results[:15], 1):
        stealth_score = result['stealth_score']
        recent_count = result['recent_stealth_count']
        days_since = result['days_since_stealth']
        price_change = result['price_change_pct']
        
        score_emoji = "🎯" if stealth_score >= 7 else "💎" if stealth_score >= 5 else "👁️" if stealth_score >= 3 else "💤"
        recency_text = "Recent" if days_since <= 2 else f"{days_since}d ago" if days_since < 999 else "None"
        
        # Check if chart exists
        chart_filename = f"{result['ticker']}_{period}_{result['filename'].split('_')[2]}_{result['filename'].split('_')[3]}_chart.png"
        chart_exists = os.path.exists(os.path.join(output_dir, chart_filename))
        
        html_content += f"""
                <div class="ticker-row" onclick="toggleChart('stealth_{result['ticker']}')">
                    <div class="rank">#{i}</div>
                    <div class="ticker-symbol">{result['ticker']}</div>
                    <div class="ticker-details">
                        <div><span class="emoji">{score_emoji}</span>Stealth Score: <strong>{stealth_score:.1f}/10</strong></div>
                        <div>Last Signal: {recency_text} | Recent Count: {recent_count} | Price Change: {price_change:+.1f}%</div>
                    </div>
                </div>"""
        
        if chart_exists:
            html_content += f"""
                <div id="stealth_{result['ticker']}" class="chart-container">
                    <div class="chart-controls">
                        <button class="btn" onclick="openChart('{chart_filename}')">📊 Open Full Size</button>
                        <button class="btn" onclick="openAnalysis('{result['filename']}')">📋 View Analysis</button>
                    </div>
                    <img src="{chart_filename}" alt="{result['ticker']} Chart" class="chart-image">
                </div>"""
    
    html_content += """
            </div>
            
            <div class="ranking-section">
                <h2>🚀 Top Recent Strong Entry Candidates</h2>"""
    
    # Add entry candidates
    for i, result in enumerate(sorted_entry_results[:15], 1):
        entry_score = result['entry_score']
        recent_strong = result['recent_strong_buy']
        recent_confluence = result['recent_confluence']
        recent_volume = result['recent_volume_breakout']
        momentum = result['momentum_direction']
        
        score_emoji = "🔥" if entry_score >= 9 else "⚡" if entry_score >= 7 else "💪" if entry_score >= 5 else "👁️"
        momentum_arrow = "↗️" if momentum == "up" else "→" if momentum == "steady" else "↘️" if momentum == "down" else "💤"
        
        # Check if chart exists
        chart_filename = f"{result['ticker']}_{period}_{result['filename'].split('_')[2]}_{result['filename'].split('_')[3]}_chart.png"
        chart_exists = os.path.exists(os.path.join(output_dir, chart_filename))
        
        html_content += f"""
                <div class="ticker-row" onclick="toggleChart('entry_{result['ticker']}')">
                    <div class="rank">#{i}</div>
                    <div class="ticker-symbol">{result['ticker']}</div>
                    <div class="ticker-details">
                        <div><span class="emoji">{score_emoji}</span>Entry Score: <strong>{entry_score:.1f}/10</strong></div>
                        <div>Strong: {recent_strong} | Confluence: {recent_confluence} | Volume: {recent_volume} | Momentum: {momentum_arrow}</div>
                    </div>
                </div>"""
        
        if chart_exists:
            html_content += f"""
                <div id="entry_{result['ticker']}" class="chart-container">
                    <div class="chart-controls">
                        <button class="btn" onclick="openChart('{chart_filename}')">📊 Open Full Size</button>
                        <button class="btn" onclick="openAnalysis('{result['filename']}')">📋 View Analysis</button>
                    </div>
                    <img src="{chart_filename}" alt="{result['ticker']} Chart" class="chart-image">
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
                 save_charts=False, generate_html=True):
    """
    Process multiple tickers from a file and save individual analysis reports.
    
    Args:
        ticker_file (str): Path to file containing ticker symbols
        period (str): Analysis period
        output_dir (str): Directory to save output files
        save_charts (bool): Whether to save chart images
        generate_html (bool): Whether to generate interactive HTML summary
        
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
                print(f"📁 Created output directory: {output_dir}")
            
            # Validate output directory is writable
            validate_file_path(output_dir, check_exists=True, check_writable=True)
            
        except Exception as e:
            raise FileOperationError(f"Failed to create or access output directory '{output_dir}': {str(e)}")
    
    print(f"\n🚀 BATCH PROCESSING {len(tickers)} TICKERS")
    print("="*50)
    print(f"📁 Output directory: {output_dir}")
    print(f"📅 Period: {period}")
    print(f"📊 Save charts: {'Yes' if save_charts else 'No'}")
    print("="*50)
    
    # Track results for summary
    results = []
    errors = []
    
    for i, ticker in enumerate(tickers, 1):
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
                    show_summary=False  # Don't print verbose summaries in batch mode
                )
                
                if isinstance(result, tuple):
                    df, filepath = result
                    filename = os.path.basename(filepath)
                    logger.info(f"Successfully processed {ticker}: {filename}")
                    print(f"✅ {ticker}: Analysis saved to {filename}")
                    
                    # Collect summary data using both stealth and entry scoring
                    phase_counts = df['Phase'].value_counts()
                    stealth_metrics = calculate_recent_stealth_score(df)
                    entry_metrics = calculate_recent_entry_score(df)
                    
                    results.append({
                        'ticker': ticker,
                        'filename': filename,
                        'stealth_score': stealth_metrics['stealth_score'],
                        'recent_stealth_count': stealth_metrics['recent_stealth_count'],
                        'days_since_stealth': stealth_metrics['days_since_stealth'],
                        'price_change_pct': stealth_metrics['price_change_pct'],
                        'entry_score': entry_metrics['entry_score'],
                        'recent_strong_buy': entry_metrics['recent_strong_buy'],
                        'recent_confluence': entry_metrics['recent_confluence'],
                        'recent_volume_breakout': entry_metrics['recent_volume_breakout'],
                        'days_since_entry': entry_metrics['days_since_entry'],
                        'momentum_direction': entry_metrics['momentum_direction'],
                        'total_recent_entry_signals': entry_metrics['total_recent_signals'],
                        'total_days': len(df),
                        'strong_signals': df['Strong_Buy'].sum(),
                        'moderate_signals': df['Moderate_Buy'].sum(),
                        'total_stealth_signals': df['Stealth_Accumulation'].sum(),
                        'latest_phase': df['Phase'].iloc[-1],
                        'exit_score': df['Exit_Score'].iloc[-1],
                        'profit_taking_signals': df['Profit_Taking'].sum(),
                        'sell_signals': df['Sell_Signal'].sum(),
                        'stop_loss_signals': df['Stop_Loss'].sum()
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
        print(f"\n📋 BATCH PROCESSING SUMMARY")
        print("="*60)
        print(f"✅ Successfully processed: {len(results)}/{len(tickers)} tickers")
        
        if errors:
            print(f"❌ Errors: {len(errors)}")
            for error in errors:
                print(f"   • {error['ticker']}: {error['error']}")
        
        print(f"\n🎯 TOP STEALTH ACCUMULATION CANDIDATES (by recent activity):")
        sorted_stealth_results = sorted(results, key=lambda x: x['stealth_score'], reverse=True)
        
        for i, result in enumerate(sorted_stealth_results[:10], 1):  # Top 10
            stealth_score = result['stealth_score']
            recent_count = result['recent_stealth_count']
            days_since = result['days_since_stealth']
            price_change = result['price_change_pct']
            total_stealth = result['total_stealth_signals']
            
            score_emoji = "🎯" if stealth_score >= 7 else "💎" if stealth_score >= 5 else "👁️" if stealth_score >= 3 else "💤"
            
            # Display days since or "Recent" if very recent
            recency_text = "Recent" if days_since <= 2 else f"{days_since}d ago" if days_since < 999 else "None"
            
            print(f"  {i:2d}. {result['ticker']:5s} - Stealth: {stealth_score:4.1f}/10 {score_emoji} "
                  f"(Last: {recency_text}, Recent: {recent_count}, Price: {price_change:+4.1f}%, Total: {total_stealth})")

        print(f"\n🚀 TOP RECENT STRONG ENTRY CANDIDATES (by signal strength):")
        sorted_entry_results = sorted(results, key=lambda x: x['entry_score'], reverse=True)
        
        for i, result in enumerate(sorted_entry_results[:10], 1):  # Top 10
            entry_score = result['entry_score']
            recent_strong = result['recent_strong_buy']
            recent_confluence = result['recent_confluence']
            recent_volume = result['recent_volume_breakout']
            days_since = result['days_since_entry']
            momentum = result['momentum_direction']
            
            score_emoji = "🔥" if entry_score >= 9 else "⚡" if entry_score >= 7 else "💪" if entry_score >= 5 else "👁️"
            
            # Display days since or "Recent" if very recent
            recency_text = "Recent" if days_since <= 2 else f"{days_since}d ago" if days_since < 999 else "None"
            
            # Momentum arrow
            momentum_arrow = "↗️" if momentum == "up" else "→" if momentum == "steady" else "↘️" if momentum == "down" else "💤"
            
            print(f"  {i:2d}. {result['ticker']:5s} - Entry: {entry_score:5.1f}/10 {score_emoji} "
                  f"(Last: {recency_text:7s}, Strong: {recent_strong}, Conf: {recent_confluence}, Vol: {recent_volume}, Momentum: {momentum_arrow})")
        
        # Generate consolidated summary file with error handling
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
                
                f.write("RESULTS RANKED BY STEALTH ACCUMULATION SCORE:\n")
                f.write("-" * 90 + "\n")
                f.write(f"{'Rank':<4} {'Ticker':<6} {'Stealth':<7} {'Recent':<6} {'DaysAgo':<7} {'Price%':<7} {'Total':<5} {'File'}\n")
                f.write("-" * 90 + "\n")
                
                for i, result in enumerate(sorted_stealth_results, 1):
                    days_text = "Recent" if result['days_since_stealth'] <= 2 else f"{result['days_since_stealth']}d" if result['days_since_stealth'] < 999 else "None"
                    f.write(f"{i:<4} {result['ticker']:<6} {result['stealth_score']:<7.1f} "
                           f"{result['recent_stealth_count']:<6} {days_text:<7} {result['price_change_pct']:<+7.1f} "
                           f"{result['total_stealth_signals']:<5} {result['filename']}\n")

                f.write("\n\nRESULTS RANKED BY RECENT STRONG ENTRY SCORE:\n")
                f.write("-" * 100 + "\n")
                f.write(f"{'Rank':<4} {'Ticker':<6} {'Entry':<6} {'Strong':<6} {'Conf':<4} {'Vol':<3} {'DaysAgo':<7} {'Momentum':<8} {'File'}\n")
                f.write("-" * 100 + "\n")
                
                for i, result in enumerate(sorted_entry_results, 1):
                    days_text = "Recent" if result['days_since_entry'] <= 2 else f"{result['days_since_entry']}d" if result['days_since_entry'] < 999 else "None"
                    momentum_text = "Up" if result['momentum_direction'] == "up" else "Steady" if result['momentum_direction'] == "steady" else "Down" if result['momentum_direction'] == "down" else "None"
                    f.write(f"{i:<4} {result['ticker']:<6} {result['entry_score']:<6.1f} "
                           f"{result['recent_strong_buy']:<6} {result['recent_confluence']:<4} {result['recent_volume_breakout']:<3} "
                           f"{days_text:<7} {momentum_text:<8} {result['filename']}\n")
                    
                logger.info(f"Batch summary saved to {summary_filename}")
                
        except Exception as e:
            logger.error(f"Failed to write batch summary file: {str(e)}")
            print(f"⚠️ Warning: Could not save summary file: {str(e)}")
        
        # Generate interactive HTML summary if requested and charts exist
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if generate_html:
            # Force chart generation if HTML is requested but charts weren't generated
            if not save_charts:
                print(f"\n📊 HTML requested - generating charts for interactive summary...")
                # Re-process with chart generation for HTML
                for i, ticker in enumerate([r['ticker'] for r in results[:5]], 1):  # Top 5 for charts
                    print(f"  Generating chart {i}/5: {ticker}...")
                    try:
                        analyze_ticker(
                            ticker=ticker,
                            period=period,
                            save_to_file=False,  # Don't overwrite analysis files
                            output_dir=output_dir,
                            save_chart=True,  # Force chart generation
                            force_refresh=False,
                            show_chart=False,  # Don't display charts interactively
                            show_summary=False  # Don't print verbose summaries
                        )
                    except Exception as e:
                        print(f"    ⚠️ Chart generation failed for {ticker}: {str(e)}")
            
            # Generate HTML summary
            html_filename = generate_html_summary(results, errors, period, output_dir, timestamp)
            print(f"\n🌐 Interactive HTML summary generated: {html_filename}")
            print(f"   📂 Open in VS Code for clickable charts and analysis links")
        
        print(f"\n📄 Summary report saved: {summary_filename}")
        print(f"📁 All files saved to: {os.path.abspath(output_dir)}")
    
    else:
        print(f"\n❌ No tickers were successfully processed.")
