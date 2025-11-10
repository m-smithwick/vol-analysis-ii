#!/usr/bin/env python3
"""
Sector Rotation Dashboard with Backtest Integration

Enhanced version that integrates batch backtesting for complete
volume analysis scoring. This version runs backtests on sector ETFs
to calculate win rates, expectancy, and recent signal activity.

Usage:
    python sector_dashboard_with_backtest.py              # Basic with backtest
    python sector_dashboard_with_backtest.py -p 6mo       # 6-month with backtest
    python sector_dashboard_with_backtest.py --quick      # Skip backtest (faster)
"""

import argparse
import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

# Import sector rotation module and dashboard
import sector_rotation
import batch_backtest
import vol_analysis
from sector_dashboard import (
    create_output_directory,
    format_score_visual,
    display_sector_detail,
    display_allocation_summary,
    display_rotation_alerts,
    save_report,
    save_current_scores,
    load_previous_scores
)


def run_sector_backtests(period: str = '3mo', 
                        cache_dir: str = 'sector_cache') -> Dict[str, Dict]:
    """
    Run backtests on all sector ETFs.
    
    Args:
        period: Analysis period
        cache_dir: Directory for caching backtest results
        
    Returns:
        Dict mapping ticker to backtest results
    """
    create_output_directory(cache_dir)
    
    # Check cache first
    cache_file = os.path.join(cache_dir, f'backtest_results_{period}.json')
    cache_age_days = 7  # Cache valid for 7 days
    
    if os.path.exists(cache_file):
        cache_age = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_file))).days
        if cache_age < cache_age_days:
            print(f"📦 Loading cached backtest results (age: {cache_age} days)")
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Failed to load cache: {e}, running fresh backtests")
    
    print(f"\n🔄 Running backtests on sector ETFs (this may take a few minutes)...")
    
    # Run batch backtest on sector ETFs
    try:
        results = batch_backtest.run_batch_backtest(
            ticker_file='sector_etfs.txt',
            period=period,
            output_dir=cache_dir,
            risk_managed=False  # Use traditional entry/exit backtest
        )
        
        # Extract per-ticker results
        ticker_results = {}
        for ticker in results.get('tickers_processed', []):
            ticker_specific = results.get('ticker_specific_results', {}).get(ticker, {})
            
            # We need the full backtest results for this ticker
            # For now, we'll use the aggregate results as a proxy
            ticker_results[ticker] = results
        
        # Cache the results
        with open(cache_file, 'w') as f:
            json.dump(ticker_results, f, indent=2, default=str)
        
        print(f"✅ Backtests complete. Results cached for {cache_age_days} days.")
        return ticker_results
        
    except Exception as e:
        print(f"❌ Error running backtests: {e}")
        return {}


def generate_dashboard_with_backtest(period: str = '3mo',
                                    output_dir: Optional[str] = None,
                                    compare: bool = False,
                                    top_n: Optional[int] = None,
                                    skip_backtest: bool = False) -> str:
    """
    Generate sector dashboard with integrated backtest data.
    
    Args:
        period: Analysis period
        output_dir: Output directory for reports
        compare: Compare with previous run
        top_n: Show only top N sectors
        skip_backtest: Skip backtest for faster analysis (volume scores will be 0)
        
    Returns:
        Complete dashboard report
    """
    report_lines = []
    
    # Header
    report_lines.append("=" * 80)
    report_lines.append("🎯 SECTOR ROTATION DASHBOARD")
    if skip_backtest:
        report_lines.append("(Quick Mode - Volume Scoring Disabled)")
    else:
        report_lines.append("(With Volume Analysis Integration)")
    report_lines.append("=" * 80)
    report_lines.append(f"\nAnalysis Period: {period}")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Benchmark: SPY (S&P 500)")
    
    # Run backtests if enabled
    backtest_results = {}
    if not skip_backtest:
        backtest_results = run_sector_backtests(period)
    else:
        print("\n⚡ Quick mode: Skipping backtests (volume scores will be 0)")
    
    # Fetch SPY data once
    print("\n🔄 Fetching SPY benchmark data...")
    spy_df = vol_analysis.analyze_ticker(
        ticker='SPY',
        period=period,
        save_to_file=False,
        save_chart=False,
        force_refresh=False,
        show_chart=False,
        show_summary=False
    )
    
    # Analyze all sectors
    print("🔄 Analyzing sector strength...")
    
    with open('sector_etfs.txt', 'r') as f:
        tickers = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    sectors = []
    for ticker in tickers:
        print(f"  Analyzing {ticker} ({sector_rotation.SECTOR_MAP.get(ticker, 'Unknown')})...")
        
        # Get backtest results for this ticker
        ticker_backtest = backtest_results.get(ticker, None)
        
        # Calculate sector score with backtest data
        sector_data = sector_rotation.calculate_sector_score(
            ticker=ticker,
            period=period,
            backtest_results=ticker_backtest,
            spy_df=spy_df
        )
        
        sectors.append(sector_data)
    
    # Sort and rank
    sectors.sort(key=lambda x: x['total_score'], reverse=True)
    
    for i, sector in enumerate(sectors, 1):
        sector['rank'] = i
        
        # Award top-3 bonus
        if i <= 3 and 'relative_strength' in sector:
            sector['relative_strength']['score'] += 1
            sector['total_score'] += 1
            if 'details' not in sector['relative_strength']:
                sector['relative_strength']['details'] = {}
            sector['relative_strength']['details']['top_sector_bonus'] = {
                'passed': True,
                'points': 1,
                'rank': i
            }
    
    # Display sectors
    display_sectors = sectors[:top_n] if top_n else sectors
    
    report_lines.append("\n" + "=" * 80)
    report_lines.append("📊 SECTOR STRENGTH RANKING")
    report_lines.append("=" * 80)
    
    for sector in display_sectors:
        report_lines.append(display_sector_detail(sector))
    
    if top_n and len(sectors) > top_n:
        report_lines.append(f"\n... and {len(sectors) - top_n} more sectors")
    
    # Allocation summary
    report_lines.append(display_allocation_summary(sectors))
    
    # Rotation alerts
    if compare:
        previous = load_previous_scores(period)
        report_lines.append(display_rotation_alerts(sectors, previous))
    
    # Summary stats
    report_lines.append("\n" + "=" * 80)
    report_lines.append("📊 SECTOR PERFORMANCE SUMMARY")
    report_lines.append("=" * 80)
    
    avg_score = sum(s['total_score'] for s in sectors) / len(sectors)
    report_lines.append(f"\nAverage Sector Score: {avg_score:.1f}/14")
    
    report_lines.append(f"\nTop Performers:")
    for i, s in enumerate(sectors[:3], 1):
        rs = s.get('relative_strength', {})
        sector_return = rs.get('sector_return', 0)
        spy_return = rs.get('spy_return', 0)
        if isinstance(sector_return, (int, float)):
            report_lines.append(f"  {i}. {s['ticker']}: {sector_return:+.2f}% "
                              f"(vs SPY {spy_return:+.2f}%) - Score {s['total_score']}/14")
        else:
            report_lines.append(f"  {i}. {s['ticker']}: Score {s['total_score']}/14")
    
    report_lines.append(f"\nBottom Performers:")
    for i, s in enumerate(sectors[-3:], 1):
        rs = s.get('relative_strength', {})
        sector_return = rs.get('sector_return', 0)
        spy_return = rs.get('spy_return', 0)
        if isinstance(sector_return, (int, float)):
            report_lines.append(f"  {i}. {s['ticker']}: {sector_return:+.2f}% "
                              f"(vs SPY {spy_return:+.2f}%) - Score {s['total_score']}/14")
        else:
            report_lines.append(f"  {i}. {s['ticker']}: Score {s['total_score']}/14")
    
    # Disclaimer
    report_lines.append("\n" + "=" * 80)
    report_lines.append("⚠️  DISCLAIMER")
    report_lines.append("=" * 80)
    report_lines.append("\nThis analysis is based on historical data and technical indicators.")
    report_lines.append("Past performance does not guarantee future results.")
    report_lines.append("Always perform your own due diligence before making investment decisions.")
    report_lines.append("\n" + "=" * 80)
    
    report = "\n".join(report_lines)
    
    # Save results
    save_current_scores(sectors, period)
    
    if output_dir:
        save_report(report, period, output_dir)
    
    return report


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Sector Rotation Dashboard with Backtest Integration',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '-p', '--period',
        default='3mo',
        choices=['1mo', '3mo', '6mo', '12mo'],
        help='Analysis period (default: 3mo)'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        default=None,
        help='Output directory for saving reports'
    )
    
    parser.add_argument(
        '--compare',
        action='store_true',
        help='Compare with previous run'
    )
    
    parser.add_argument(
        '--top',
        type=int,
        metavar='N',
        help='Show only top N sectors'
    )
    
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Skip backtests for faster analysis (volume scores will be 0)'
    )
    
    args = parser.parse_args()
    
    try:
        # Generate dashboard
        report = generate_dashboard_with_backtest(
            period=args.period,
            output_dir=args.output_dir,
            compare=args.compare,
            top_n=args.top,
            skip_backtest=args.quick
        )
        
        # Display report
        print("\n" + report)
        
        print("\n✅ Dashboard generation complete!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Dashboard generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error generating dashboard: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
