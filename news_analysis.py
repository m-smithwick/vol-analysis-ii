#!/usr/bin/env python3
"""
News & Research Influence Analysis Tool

This tool analyzes whether daily price increases after market open
are influenced by news or research reports.
"""

import argparse
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Any, Optional, Union
import concurrent.futures

# Import from our modules
from data_manager import get_smart_data, get_intraday_data, read_ticker_file
from utils import (
    generate_output_directory, 
    format_date_range, 
    handle_errors, 
    parse_date_string,
    format_percentage,
    create_filename,
    summarize_results,
    print_progress_bar
)
from news_influence import (
    calculate_news_influence_score, 
    fetch_financial_news,
    detect_intraday_price_jumps,
    analyze_multiple_days,
    batch_analyze_tickers,
    clear_news_cache
)

def analyze_news_influence(
    ticker: str, 
    date_str: str = None,
    days_back: int = 30,
    interval: str = "1h",
    save_to_file: bool = False,
    output_dir: str = "results",
    news_dir: str = None,
    volume_dir: str = None,
    save_chart: bool = False
):
    """
    Analyze if price increases were influenced by news/research.
    
    Args:
        ticker (str): Stock symbol
        date_str (str, optional): Specific date to analyze (YYYY-MM-DD)
        days_back (int): Days to analyze if no specific date
        interval (str): Data interval for intraday analysis
        save_to_file (bool): Whether to save analysis to file
        output_dir (str): Directory for output files
        save_chart (bool): Whether to save charts
    """
    print(f"\n🔍 ANALYZING NEWS INFLUENCE FOR {ticker}")
    print("="*60)
    
    # Determine analysis date(s)
    if date_str:
        target_date = parse_date_string(date_str)
        if not target_date:
            return
        dates_to_analyze = [target_date]
    else:
        end_date = datetime.now()
        dates_to_analyze = [end_date - timedelta(days=i) for i in range(days_back)]
    
    results = []
    
    for i, analysis_date in enumerate(dates_to_analyze):
        print(f"\n📅 Analyzing {analysis_date.strftime('%Y-%m-%d')} [{i+1}/{len(dates_to_analyze)}]...")
        
        try:
            # Get intraday data for this date +/- 1 day
            date_from = analysis_date - timedelta(days=1)
            date_to = analysis_date + timedelta(days=1)
            
            # Calculate total days needed (consistent with analyze_multiple_days)
            total_days_needed = days_back  # Use the days_back parameter directly
            
            # Fetch data
            intraday_data = get_intraday_data(
                ticker=ticker,
                days=total_days_needed,
                interval=interval
            )
            
            # Filter to relevant date range
            mask = (intraday_data.index >= date_from) & (intraday_data.index <= date_to)
            df = intraday_data.loc[mask]
            
            if df.empty:
                print(f"⚠️  No data available for {analysis_date.strftime('%Y-%m-%d')}")
                continue
            
            # Calculate news influence score
            influence_data = calculate_news_influence_score(df, ticker, analysis_date)
            
            # Print summary
            confidence = influence_data['confidence'] * 100
            emoji = "📰" if influence_data['classification'] == "News Influenced" else "📊"
            
            print(f"  {emoji} Classification: {influence_data['classification']}")
            print(f"  ⚖️  Confidence Score: {confidence:.1f}%")
            print(f"  🔍 Primary Factor: {influence_data['primary_factor']}")
            print(f"  📊 News Count: {influence_data['news_count']}")
            
            if influence_data['news_details']:
                print("\n  📰 TOP NEWS IMPACTS:")
                for idx, news in enumerate(sorted(influence_data['news_details'], 
                                              key=lambda x: abs(x['impact']), reverse=True)[:3]):
                    print(f"    {idx+1}. [{news['time'].strftime('%H:%M')}] {news['headline'][:60]}...")
                    print(f"       Impact: {format_percentage(news['impact'])}")
            
            # Add to results
            results.append(influence_data)
            
            # Generate chart if requested
            if save_chart:
                chart_dir = news_dir if news_dir else output_dir
                generate_news_influence_chart(
                    df=df,
                    ticker=ticker,
                    analysis_date=analysis_date,
                    news_details=influence_data['news_details'],
                    output_dir=chart_dir
                )
                
        except Exception as e:
            handle_errors(e, ticker)
    
    # Generate summary report
    if results:
        # Count influenced vs. non-influenced days
        influenced_count = sum(1 for r in results if r['classification'] == "News Influenced")
        total_count = len(results)
        influence_rate = (influenced_count / total_count) * 100 if total_count > 0 else 0
        
        print("\n📋 NEWS INFLUENCE SUMMARY")
        print("="*60)
        print(f"Ticker: {ticker}")
        print(f"Period: {format_date_range(dates_to_analyze[-1], dates_to_analyze[0])}")
        print(f"Days Analyzed: {total_count}")
        print(f"News Influenced Days: {influenced_count} ({influence_rate:.1f}%)")
        print(f"Technical/Organic Days: {total_count - influenced_count} ({100 - influence_rate:.1f}%)")
        
        # Show top influence days
        if influenced_count > 0:
            print("\n🔝 TOP NEWS INFLUENCED DAYS:")
            for i, result in enumerate(sorted(results, key=lambda x: x['confidence'], reverse=True)[:5]):
                if result['classification'] == "News Influenced":
                    print(f"  {i+1}. {result['date']} - Confidence: {result['confidence']*100:.1f}%")
                    print(f"     Primary Factor: {result['primary_factor']}")
        
        # Save to file if requested
        if save_to_file:
            report_dir = news_dir if news_dir else output_dir
            save_influence_report(results, ticker, report_dir)
    
    return results

def batch_process_tickers(ticker_file: str, days_back: int = 30, interval: str = "1h", 
                         output_dir: str = "results", news_dir: str = None, volume_dir: str = None,
                         save_charts: bool = False, max_workers: int = 5):
    """
    Process multiple tickers from a file and generate reports.
    
    Args:
        ticker_file (str): Path to file containing ticker symbols
        days_back (int): Number of days to analyze
        interval (str): Data interval for intraday analysis
        output_dir (str): Directory for output files
        save_charts (bool): Whether to save charts
        max_workers (int): Maximum number of parallel workers
    """
    # Read tickers from file
    try:
        tickers = read_ticker_file(ticker_file)
    except Exception as e:
        handle_errors(e)
        return
    
    if not tickers:
        print("❌ No valid tickers found in file.")
        return
    
    # Create output directories if they don't exist
    output_dir = generate_output_directory(output_dir)
    
    if news_dir:
        news_dir = generate_output_directory(news_dir)
    else:
        news_dir = generate_output_directory("results_news")
    
    if volume_dir:
        volume_dir = generate_output_directory(volume_dir)
    else:
        volume_dir = generate_output_directory("results_volume")
    
    print(f"\n🚀 BATCH PROCESSING {len(tickers)} TICKERS")
    print("="*50)
    print(f"📁 Main output directory: {output_dir}")
    print(f"📁 News results directory: {news_dir}")
    print(f"📁 Volume results directory: {volume_dir}")
    print(f"📅 Days back: {days_back}")
    print(f"⏱️ Interval: {interval}")
    print(f"📊 Save charts: {'Yes' if save_charts else 'No'}")
    print("="*50)
    
    # Prepare dates
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    # Use batch analysis function with parallel processing
    all_results = {}
    
    # Process each ticker individually (easier to show progress)
    for i, ticker in enumerate(tickers):
        print(f"\n[{i+1}/{len(tickers)}] Processing {ticker}...")
        
        try:
            # Analyze ticker
            results = analyze_multiple_days(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                interval=interval
            )
            
            if results:
                all_results[ticker] = results
                
                # Save individual ticker report
                save_influence_report(results, ticker, news_dir)
                
                # Generate charts if requested
                if save_charts:
                    for result in results:
                        date = datetime.strptime(result['date'], '%Y-%m-%d')
                        
                        # Get intraday data for this date
                        try:
                            intraday_data = get_intraday_data(
                                ticker=ticker,
                                days=days_back,  # Use the days_back parameter instead of hardcoded 3
                                interval=interval
                            )
                            
                            # Filter to relevant date range
                            date_from = date - timedelta(days=1)
                            date_to = date + timedelta(days=1)
                            mask = (intraday_data.index >= date_from) & (intraday_data.index <= date_to)
                            df = intraday_data.loc[mask]
                            
                            if not df.empty and result['classification'] == "News Influenced":
                                generate_news_influence_chart(
                                    df=df,
                                    ticker=ticker,
                                    analysis_date=date,
                                    news_details=result.get('news_details', []),
                                    output_dir=news_dir
                                )
                        except Exception as e:
                            print(f"⚠️  Error generating chart: {str(e)}")
            
        except Exception as e:
            handle_errors(e, ticker)
    
    # Generate summary report for all tickers
    if all_results:
        generate_batch_summary_report(all_results, news_dir, start_date, end_date)
        print(f"\n✅ Batch processing complete! News results saved to {news_dir}")
        print(f"✅ Volume results saved to {volume_dir}")
    else:
        print("\n❌ No results generated.")

def generate_news_influence_chart(
    df: pd.DataFrame,
    ticker: str,
    analysis_date: datetime,
    news_details: List[Dict],
    output_dir: str
):
    """
    Generate chart showing price action and news events.
    
    Args:
        df (pd.DataFrame): Intraday price data
        ticker (str): Stock symbol
        analysis_date (datetime): Date to analyze
        news_details (List[Dict]): News details with timestamps and headlines
        output_dir (str): Directory to save chart
    """
    # Filter to trading hours on the analysis date
    day_start = datetime(analysis_date.year, analysis_date.month, analysis_date.day, 9, 30)
    day_end = datetime(analysis_date.year, analysis_date.month, analysis_date.day, 16, 0)
    
    mask = (df.index >= day_start) & (df.index <= day_end)
    day_df = df.loc[mask]
    
    if day_df.empty:
        print("⚠️  Not enough data points for chart")
        return
    
    # Create figure
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 1]}, sharex=True)
    
    # Plot price
    ax1.plot(day_df.index, day_df['Close'], label='Price', color='black', linewidth=2)
    
    # Calculate and plot VWAP if we have both price and volume
    if 'Volume' in day_df.columns:
        vwap = (day_df['Close'] * day_df['Volume']).cumsum() / day_df['Volume'].cumsum()
        ax1.plot(day_df.index, vwap, label='VWAP', color='purple', linestyle='--', alpha=0.7)
    
    # Mark news events
    news_times = []
    for news in news_details:
        try:
            news_time = news['time']
            if day_start <= news_time <= day_end:
                news_times.append(news_time)
                
                # Determine impact color (green for positive, red for negative)
                impact = news.get('impact', 0)
                color = 'green' if impact > 0 else 'red' if impact < 0 else 'blue'
                
                ax1.axvline(x=news_time, color=color, linestyle='--', alpha=0.7)
                
                # Find closest price point to news time for annotation placement
                closest_idx = day_df.index[day_df.index.get_indexer([news_time], method='nearest')[0]]
                price_at_news = day_df.loc[closest_idx, 'Close']
                
                # Add emoji based on impact
                emoji = "📈" if impact > 1.0 else "📉" if impact < -1.0 else "📰"
                
                # Add annotation with headline
                headline = news.get('headline', '')[:40] + "..." if len(news.get('headline', '')) > 40 else news.get('headline', '')
                
                # Alternate placement to avoid overlap
                y_offset = 0.02 * (1 + news_times.index(news_time) % 3)
                
                ax1.annotate(
                    f"{emoji} {news_time.strftime('%H:%M')}",
                    xy=(news_time, price_at_news),
                    xytext=(0, 25 + 20 * (news_times.index(news_time) % 3)),
                    textcoords="offset points",
                    ha='center',
                    va='bottom',
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.8),
                    arrowprops=dict(arrowstyle="->", color=color)
                )
                
                # Add headline as text at bottom of chart
                headline_y = day_df['Close'].min() * (0.97 - y_offset)
                ax1.text(
                    news_time, 
                    headline_y,
                    headline,
                    fontsize=8,
                    color=color,
                    ha='center',
                    va='top',
                    rotation=45,
                    bbox=dict(boxstyle="round,pad=0.1", fc="white", alpha=0.7)
                )
        except Exception as e:
            print(f"⚠️  Error adding news marker: {str(e)}")
    
    # Add volume bars in the bottom panel
    if 'Volume' in day_df.columns:
        # Normalize volume
        max_vol = day_df['Volume'].max()
        normalized_vol = day_df['Volume'] / max_vol if max_vol > 0 else day_df['Volume']
        
        # Color volume bars based on price change
        colors = ['green' if close >= open else 'red' for close, open in zip(day_df['Close'], day_df['Open'])]
        
        ax2.bar(day_df.index, normalized_vol, color=colors, alpha=0.7)
        ax2.set_ylabel('Relative Volume')
        
        # Add average volume line
        avg_vol = day_df['Volume'].mean() / max_vol if max_vol > 0 else 0
        ax2.axhline(y=avg_vol, color='black', linestyle='--', alpha=0.5, label='Avg Volume')
    
    # Set title and labels
    title = f"{ticker} - News Influence Analysis - {analysis_date.strftime('%Y-%m-%d')}"
    if news_times:
        title += f" ({len(news_times)} news events)"
    ax1.set_title(title)
    
    ax1.set_ylabel('Price ($)')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left')
    
    # Format x-axis to show hours
    plt.gcf().autofmt_xdate()
    
    # Adjust layout
    plt.tight_layout()
    
    # Save chart
    chart_filename = create_filename(
        ticker=ticker,
        analysis_type="news_chart",
        start_date=analysis_date.strftime("%Y%m%d"),
        extension="png"
    )
    
    chart_path = os.path.join(output_dir, chart_filename)
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"📊 Chart saved: {chart_filename}")

def save_influence_report(results: List[Dict], ticker: str, output_dir: str) -> str:
    """
    Save news influence analysis report to file.
    
    Args:
        results (List[Dict]): Analysis results
        ticker (str): Stock symbol
        output_dir (str): Directory to save report
        
    Returns:
        str: Path to the saved report
    """
    # Create output directory if needed
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Generate filename
    if results:
        start_date = min(datetime.strptime(r['date'], '%Y-%m-%d') for r in results).strftime('%Y%m%d')
        end_date = max(datetime.strptime(r['date'], '%Y-%m-%d') for r in results).strftime('%Y%m%d')
        
        filename = create_filename(
            ticker=ticker,
            analysis_type="news_analysis",
            start_date=start_date,
            end_date=end_date,
            extension="txt"
        )
    else:
        filename = create_filename(
            ticker=ticker,
            analysis_type="news_analysis",
            start_date=datetime.now().strftime("%Y%m%d"),
            extension="txt"
        )
    
    filepath = os.path.join(output_dir, filename)
    
    # Generate report content
    lines = []
    lines.append("="*80)
    lines.append(f"NEWS & RESEARCH INFLUENCE ANALYSIS FOR {ticker}")
    lines.append("="*80)
    lines.append("")
    
    # Summary statistics
    if results:
        influenced_count = sum(1 for r in results if r['classification'] == "News Influenced")
        total_count = len(results)
        influence_rate = (influenced_count / total_count) * 100
        
        start_date_obj = min(datetime.strptime(r['date'], '%Y-%m-%d') for r in results)
        end_date_obj = max(datetime.strptime(r['date'], '%Y-%m-%d') for r in results)
        
        lines.append(f"Analysis Period: {format_date_range(start_date_obj, end_date_obj)}")
        lines.append(f"Days Analyzed: {total_count}")
        lines.append(f"News Influenced Days: {influenced_count} ({influence_rate:.1f}%)")
        lines.append(f"Technical/Organic Days: {total_count - influenced_count} ({100 - influence_rate:.1f}%)")
        lines.append("")
        
        # Group by primary factor
        factors = {}
        for result in results:
            if result['classification'] != "News Influenced":
                continue
                
            factor = result['primary_factor']
            if factor not in factors:
                factors[factor] = 0
            factors[factor] += 1
        
        if factors:
            lines.append("PRIMARY INFLUENCE FACTORS:")
            for factor, count in sorted(factors.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / influenced_count) * 100
                lines.append(f"  • {factor}: {count} days ({percentage:.1f}%)")
            lines.append("")
        
        # Top influenced days
        if influenced_count > 0:
            lines.append("TOP NEWS INFLUENCED DAYS:")
            for i, result in enumerate(sorted(results, key=lambda x: x['confidence'], reverse=True)[:10]):
                if result['classification'] == "News Influenced":
                    lines.append(f"  {i+1}. {result['date']} - Confidence: {result['confidence']*100:.1f}%")
                    lines.append(f"     Primary Factor: {result['primary_factor']}")
                    
                    # Add top news if available
                    if result.get('news_details'):
                        top_news = sorted(result['news_details'], key=lambda x: abs(x['impact']), reverse=True)[0]
                        lines.append(f"     Top News: {top_news['headline']}")
                        lines.append(f"     Impact: {format_percentage(top_news['impact'])}")
                    lines.append("")
            lines.append("")
        
        # Detailed daily analysis
        lines.append("="*80)
        lines.append("DAILY ANALYSIS")
        lines.append("="*80)
        lines.append("")
        
        for result in sorted(results, key=lambda x: x['date'], reverse=True):
            date = result['date']
            classification = result['classification']
            confidence = result['confidence'] * 100
            
            emoji = "📰" if classification == "News Influenced" else "📊"
            lines.append(f"{date} - {emoji} {classification} (Confidence: {confidence:.1f}%)")
            lines.append(f"Primary Factor: {result['primary_factor']}")
            lines.append(f"News Count: {result['news_count']}")
            
            if result.get('news_details'):
                lines.append("News Impact:")
                for news in sorted(result['news_details'], key=lambda x: abs(x['impact']), reverse=True)[:3]:
                    lines.append(f"  • [{news['time'].strftime('%H:%M')}] {news['headline']}")
                    lines.append(f"    Impact: {format_percentage(news['impact'])}")
            
            lines.append("-"*40)
    else:
        lines.append("No analysis results available.")
    
    # Write to file
    with open(filepath, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"📄 Report saved: {filename}")
    return filepath

def generate_batch_summary_report(
    results_dict: Dict[str, List[Dict]], 
    output_dir: str,
    start_date: datetime,
    end_date: datetime
) -> str:
    """
    Generate a summary report for batch analysis.
    
    Args:
        results_dict (Dict[str, List[Dict]]): Dictionary of ticker -> results
        output_dir (str): Directory to save report
        start_date (datetime): Start date of analysis
        end_date (datetime): End date of analysis
        
    Returns:
        str: Path to the saved report
    """
    # Create output directory if needed
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Generate filename
    filename = f"batch_news_analysis_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.txt"
    filepath = os.path.join(output_dir, filename)
    
    # Generate report content
    lines = []
    lines.append("="*80)
    lines.append("BATCH NEWS INFLUENCE ANALYSIS SUMMARY")
    lines.append("="*80)
    lines.append("")
    
    # Summary statistics
    lines.append(f"Analysis Period: {format_date_range(start_date, end_date)}")
    lines.append(f"Tickers Analyzed: {len(results_dict)}")
    lines.append("")
    
    # Create summary statistics
    ticker_stats = []
    for ticker, results in results_dict.items():
        if not results:
            continue
            
        influenced_count = sum(1 for r in results if r['classification'] == "News Influenced")
        total_count = len(results)
        influence_rate = (influenced_count / total_count) * 100 if total_count > 0 else 0
        
        # Calculate average confidence
        confidences = [r['confidence'] for r in results if r['classification'] == "News Influenced"]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        ticker_stats.append({
            'ticker': ticker,
            'days_analyzed': total_count,
            'influenced_days': influenced_count,
            'influence_rate': influence_rate,
            'avg_confidence': avg_confidence
        })
    
    # Sort by influence rate
    ticker_stats.sort(key=lambda x: x['influence_rate'], reverse=True)
    
    # Overall statistics
    if ticker_stats:
        total_days = sum(stat['days_analyzed'] for stat in ticker_stats)
        total_influenced = sum(stat['influenced_days'] for stat in ticker_stats)
        overall_rate = (total_influenced / total_days) * 100 if total_days > 0 else 0
        
        lines.append(f"Total Days Analyzed: {total_days}")
        lines.append(f"Total Influenced Days: {total_influenced} ({overall_rate:.1f}%)")
        lines.append("")
    
    # Ticker rankings
    lines.append("TICKER RANKINGS BY NEWS INFLUENCE RATE:")
    lines.append("-"*60)
    lines.append(f"{'Ticker':^8} | {'Days':^6} | {'Influenced':^10} | {'Rate':^8} | {'Avg Conf':^8}")
    lines.append("-"*60)
    
    for stat in ticker_stats:
        ticker = stat['ticker']
        days = stat['days_analyzed']
        influenced = stat['influenced_days']
        rate = stat['influence_rate']
        conf = stat['avg_confidence'] * 100
        
        lines.append(f"{ticker:^8} | {days:^6d} | {influenced:^10d} | {rate:^7.1f}% | {conf:^7.1f}%")
    
    # Find most news-reactive tickers
    if ticker_stats:
        lines.append("")
        lines.append("MOST NEWS-REACTIVE TICKERS:")
        for i, stat in enumerate(ticker_stats[:10]):  # Top 10
            lines.append(f"{i+1}. {stat['ticker']} - {stat['influence_rate']:.1f}% of days influenced by news")
        
        # Find least news-reactive tickers
        lines.append("")
        lines.append("LEAST NEWS-REACTIVE TICKERS:")
        for i, stat in enumerate(sorted(ticker_stats, key=lambda x: x['influence_rate'])[:10]):  # Bottom 10
            lines.append(f"{i+1}. {stat['ticker']} - {stat['influence_rate']:.1f}% of days influenced by news")
    
    # Write to file
    with open(filepath, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"📄 Batch summary saved: {filename}")
    return filepath

def main():
    """
    Main function to handle command-line arguments and run the analysis.
    """
    parser = argparse.ArgumentParser(
        description='📰 News & Research Influence Analysis Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a single ticker
  python news_analysis.py AAPL                     # Analyze AAPL for past 30 days
  python news_analysis.py TSLA --date 2023-06-15   # Analyze TESLA for specific date
  python news_analysis.py NVDA --interval 30m      # Use 30-minute intervals
  python news_analysis.py MSFT --days 10           # Look back 10 days
  
  # Batch processing
  python news_analysis.py --file stocks.txt        # Process all tickers in stocks.txt
        """
    )
    
    parser.add_argument(
        'ticker', 
        nargs='?',
        help='Stock ticker symbol. Ignored if --file is used.'
    )
    
    parser.add_argument(
        '-f', '--file',
        help='Path to file containing ticker symbols (one per line).'
    )
    
    parser.add_argument(
        '-d', '--date',
        help='Specific date to analyze (YYYY-MM-DD). If not provided, analyzes past --days days.'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to look back (default: 30).'
    )
    
    parser.add_argument(
        '-i', '--interval',
        default='1h',
        choices=['1h', '30m', '15m', '5m'],
        help='Intraday interval for analysis (default: 1h)'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        default='results',
        help='Main output directory for results (default: results)'
    )
    
    parser.add_argument(
        '--news-dir',
        help='Directory for news analysis results (default: results_news)'
    )
    
    parser.add_argument(
        '--volume-dir',
        help='Directory for volume analysis results (default: results_volume)'
    )
    
    parser.add_argument(
        '--save-charts',
        action='store_true',
        help='Save chart images as PNG files'
    )
    
    parser.add_argument(
        '--clear-cache',
        action='store_true',
        help='Clear news cache before running analysis'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=5,
        help='Maximum number of parallel workers for batch processing (default: 5)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.ticker and not args.file:
        parser.error("Either ticker symbol or --file must be provided")
        return
    
    # Clear news cache if requested
    if args.clear_cache:
        clear_news_cache()
    
    # Create output directory if needed
    output_dir = generate_output_directory(args.output_dir)
    
    try:
        if args.file:
            # Batch processing mode
            batch_process_tickers(
                ticker_file=args.file,
                days_back=args.days,
                interval=args.interval,
                output_dir=output_dir,
                news_dir=args.news_dir,
                volume_dir=args.volume_dir,
                save_charts=args.save_charts,
                max_workers=args.workers
            )
        else:
            # Single ticker mode
            analyze_news_influence(
                ticker=args.ticker.upper(),
                date_str=args.date,
                days_back=args.days,
                interval=args.interval,
                save_to_file=True,
                output_dir=output_dir,
                news_dir=args.news_dir,
                volume_dir=args.volume_dir,
                save_chart=args.save_charts
            )
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("Please check your inputs and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
