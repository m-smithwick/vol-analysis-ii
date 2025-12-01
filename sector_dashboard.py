#!/usr/bin/env python3
"""
Sector Rotation Dashboard

Command-line tool for analyzing sector strength and generating
rotation recommendations. Integrates with the volume analysis
backtesting system to provide comprehensive sector insights.

Usage:
    python sector_dashboard.py                    # Basic 3-month analysis
    python sector_dashboard.py -p 6mo             # 6-month analysis
    python sector_dashboard.py --compare          # Compare to previous run
    python sector_dashboard.py --top 5            # Show only top 5 sectors
    python sector_dashboard.py -o sector_reports  # Save detailed report
"""

import argparse
import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

# Import sector rotation module
import sector_rotation
import batch_backtest


def create_output_directory(output_dir: str) -> None:
    """Create output directory if it doesn't exist."""
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")


def format_score_visual(score: int, max_score: int = 14) -> str:
    """
    Generate visual representation of score.
    
    Args:
        score: Current score
        max_score: Maximum possible score
        
    Returns:
        Visual string (stars/arrows)
    """
    if score >= 10:
        return "⭐⭐⭐"
    elif score >= 8:
        return "⭐⭐"
    elif score >= 6:
        return "⭐"
    elif score >= 4:
        return "→"
    else:
        return "⚠️"


def display_sector_detail(sector_data: Dict) -> str:
    """
    Generate detailed breakdown of a sector's score.
    
    Args:
        sector_data: Sector analysis dictionary
        
    Returns:
        Formatted string for display
    """
    lines = []
    ticker = sector_data['ticker']
    sector_name = sector_data['sector']
    score = sector_data['total_score']
    max_score = sector_data['max_score']
    rank = sector_data.get('rank', '?')
    
    visual = format_score_visual(score, max_score)
    
    lines.append(f"\n{'🥇' if rank == 1 else '🥈' if rank == 2 else '🥉' if rank == 3 else f'#{rank}'} "
                f"RANK #{rank}: {ticker} ({sector_name}) - Score: {score}/{max_score} {visual}")
    lines.append("   " + "─" * 70)
    
    # Momentum score details
    momentum = sector_data.get('momentum', {})
    mom_score = momentum.get('score', 0)
    mom_max = momentum.get('max_score', 6)
    lines.append(f"   Momentum Score: {mom_score}/{mom_max}")
    
    mom_details = momentum.get('details', {})
    if 'above_50ma' in mom_details:
        detail = mom_details['above_50ma']
        check = '✅' if detail['passed'] else '❌'
        lines.append(f"     • Above 50-day MA: {check} +{detail['points']} "
                    f"(Price: {detail['price']}, MA: {detail['ma']})")
    
    if 'above_200ma' in mom_details:
        detail = mom_details['above_200ma']
        check = '✅' if detail['passed'] else '❌'
        lines.append(f"     • Above 200-day MA: {check} +{detail['points']} "
                    f"(Price: {detail['price']}, MA: {detail['ma']})")
    
    if 'return_20d' in mom_details:
        detail = mom_details['return_20d']
        check = '✅' if detail['passed'] else '❌'
        lines.append(f"     • 20-day Return: {check} +{detail['points']} ({detail['return']})")
    
    # Volume score details
    volume = sector_data.get('volume', {})
    vol_score = volume.get('score', 0)
    vol_max = volume.get('max_score', 6)
    lines.append(f"\n   Volume Score: {vol_score}/{vol_max}")
    
    vol_details = volume.get('details', {})
    if 'win_rate' in vol_details:
        detail = vol_details['win_rate']
        check = '✅' if detail['passed'] else '❌'
        lines.append(f"     • Win Rate: {check} +{detail['points']} "
                    f"({detail['value']} vs {detail['threshold']} threshold)")
    
    if 'expectancy' in vol_details:
        detail = vol_details['expectancy']
        check = '✅' if detail['passed'] else '❌'
        lines.append(f"     • Expectancy: {check} +{detail['points']} ({detail['value']})")
    
    if 'recent_signals' in vol_details:
        detail = vol_details['recent_signals']
        check = '✅' if detail['passed'] else '❌'
        if 'days_ago' in detail:
            lines.append(f"     • Recent Signals: {check} +{detail['points']} "
                        f"({detail['days_ago']} days ago)")
        else:
            lines.append(f"     • Recent Signals: {check} +{detail['points']} "
                        f"({detail.get('reason', 'N/A')})")
    elif 'no_data' in vol_details:
        lines.append(f"     • {vol_details['no_data']}")
    
    # Relative strength details
    rs = sector_data.get('relative_strength', {})
    rs_score = rs.get('score', 0)
    rs_max = rs.get('max_score', 2)
    lines.append(f"\n   Relative Strength: {rs_score}/{rs_max}")
    
    rs_details = rs.get('details', {})
    if 'vs_spy' in rs_details:
        detail = rs_details['vs_spy']
        check = '✅' if detail['passed'] else '❌'
        perf_key = 'outperformance' if detail['passed'] else 'underperformance'
        lines.append(f"     • vs SPY: {check} +{detail['points']} "
                    f"({detail['sector_return']} vs SPY {detail['spy_return']}, "
                    f"{detail.get(perf_key, 'N/A')})")
    
    if 'top_sector_bonus' in rs_details:
        detail = rs_details['top_sector_bonus']
        lines.append(f"     • Top-3 Bonus: ✅ +{detail['points']} (Rank #{detail['rank']})")
    
    # Recommendation
    recommendation = sector_data.get('recommendation', 'N/A')
    allocation_range = sector_data.get('allocation_range', (0, 0))
    
    lines.append(f"\n   💡 RECOMMENDATION: {recommendation}")
    if allocation_range[1] > 0:
        lines.append(f"   📊 Target Allocation: {allocation_range[0]*100:.0f}-{allocation_range[1]*100:.0f}% of portfolio")
    else:
        lines.append(f"   📊 Target Allocation: 0% (Avoid)")
    
    return "\n".join(lines)


def display_recommendation_summary(sectors: List[Dict]) -> str:
    """
    Generate concise recommendation summary for all sectors.
    
    Args:
        sectors: List of sector analysis dicts (sorted by score)
        
    Returns:
        Formatted summary table
    """
    lines = []
    lines.append("\n" + "=" * 80)
    lines.append("📋 SECTOR RECOMMENDATION SUMMARY")
    lines.append("=" * 80)
    lines.append("\nQuick reference for all sector recommendations:\n")
    
    for sector in sectors:
        ticker = sector['ticker']
        sector_name = sector['sector']
        score = sector['total_score']
        recommendation = sector['recommendation']
        allocation_range = sector['allocation_range']
        
        # Format allocation
        if allocation_range[1] > 0:
            alloc_str = f"{allocation_range[0]*100:.0f}-{allocation_range[1]*100:.0f}%"
        else:
            alloc_str = "0%"
        
        # Add visual indicator
        if score >= 8:
            indicator = "⭐"
        elif score >= 6:
            indicator = "→"
        elif score >= 4:
            indicator = "○"
        else:
            indicator = "⚠️"
        
        # Format line with proper spacing for alignment
        line = f"{indicator} {ticker:5} ({sector_name:25}): {recommendation:15} | Allocation: {alloc_str:6} | Score: {score:2}/14"
        lines.append(line)
    
    return "\n".join(lines)


def display_allocation_summary(sectors: List[Dict]) -> str:
    """
    Generate portfolio allocation recommendations.
    
    Args:
        sectors: List of sector analysis dicts (sorted by score)
        
    Returns:
        Formatted allocation summary
    """
    lines = []
    lines.append("\n" + "=" * 80)
    lines.append("📈 RECOMMENDED PORTFOLIO ALLOCATION")
    lines.append("=" * 80)
    lines.append("\nBased on current sector strength scores:\n")
    
    # Group by recommendation category
    leading = [s for s in sectors if s['total_score'] >= 8]
    strong = [s for s in sectors if 6 <= s['total_score'] < 8]
    neutral = [s for s in sectors if 4 <= s['total_score'] < 6]
    weak = [s for s in sectors if s['total_score'] < 4]
    
    if leading:
        total_pct = sum([s['allocation_range'][0] for s in leading]) * 100
        lines.append(f"LEADING SECTORS (Score 8-10): {total_pct:.0f}% Total Allocation")
        for s in leading:
            pct = (s['allocation_range'][0] + s['allocation_range'][1]) / 2 * 100
            lines.append(f"  • {s['ticker']} ({s['sector']}): {pct:.0f}%")
    
    if strong:
        total_pct = sum([s['allocation_range'][0] for s in strong]) * 100
        lines.append(f"\nSTRONG SECTORS (Score 6-7): {total_pct:.0f}% Total Allocation")
        for s in strong:
            pct = (s['allocation_range'][0] + s['allocation_range'][1]) / 2 * 100
            lines.append(f"  • {s['ticker']} ({s['sector']}): {pct:.0f}%")
    
    if neutral:
        total_pct = sum([s['allocation_range'][0] for s in neutral]) * 100
        lines.append(f"\nOPPORTUNISTIC (Score 4-5): {total_pct:.0f}% Total Allocation")
        for s in neutral:
            pct = (s['allocation_range'][0] + s['allocation_range'][1]) / 2 * 100
            lines.append(f"  • {s['ticker']} ({s['sector']}): {pct:.0f}%")
    
    if weak:
        lines.append(f"\nAVOID (Score 0-3): 0% Allocation")
        for s in weak:
            lines.append(f"  • {s['ticker']} ({s['sector']})")
    
    return "\n".join(lines)


def display_rotation_alerts(current: List[Dict], previous: Optional[List[Dict]] = None) -> str:
    """
    Generate rotation alert summary.
    
    Args:
        current: Current sector scores
        previous: Previous sector scores (optional)
        
    Returns:
        Formatted alert summary
    """
    lines = []
    lines.append("\n" + "=" * 80)
    lines.append("⚠️ ROTATION ALERTS")
    lines.append("=" * 80)
    
    if not previous:
        lines.append("\nNo previous data available for comparison.")
        lines.append("Run again next week to see rotation alerts.")
        return "\n".join(lines)
    
    alerts = sector_rotation.detect_rotation_alerts(current, previous)
    
    if not alerts:
        lines.append("\n✅ No significant sector rotations detected.")
        lines.append("All sectors maintaining similar strength levels.")
        return "\n".join(lines)
    
    lines.append(f"\n🚨 {len(alerts)} SIGNIFICANT CHANGES DETECTED:\n")
    
    for alert in alerts:
        alert_type = alert['type']
        ticker = alert['ticker']
        sector = alert['sector']
        prev_score = alert['previous_score']
        curr_score = alert['current_score']
        change = alert['change']
        action = alert['action']
        
        if alert_type == 'STRENGTH_IMPROVING':
            emoji = "📈"
        elif alert_type == 'STRENGTH_DETERIORATING':
            emoji = "📉"
        elif alert_type == 'CROSSING_INTO_STRONG':
            emoji = "🔥"
        else:
            emoji = "⚠️"
        
        lines.append(f"{emoji} {ticker} ({sector}): {prev_score}/14 → {curr_score}/14 ({change:+d} points)")
        lines.append(f"   💡 Action: {action}\n")
    
    return "\n".join(lines)


def generate_dashboard_report(period: str = '3mo', 
                             output_dir: Optional[str] = None,
                             compare: bool = False,
                             top_n: Optional[int] = None,
                             sectors_file: str = 'ticker_lists/sector_etfs.txt') -> str:
    """
    Generate complete sector rotation dashboard.
    
    Args:
        period: Analysis period
        output_dir: Output directory for saving reports
        compare: Whether to compare with previous run
        top_n: Show only top N sectors (optional)
        sectors_file: Path to file containing sector ETF tickers
        
    Returns:
        Complete dashboard report as string
    """
    report_lines = []
    
    # Header
    report_lines.append("=" * 80)
    report_lines.append("🎯 SECTOR ROTATION DASHBOARD")
    report_lines.append("=" * 80)
    report_lines.append(f"\nAnalysis Period: {period}")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Benchmark: SPY (S&P 500)")
    
    # Analyze sectors
    print(f"\n🔄 Analyzing sectors from {sectors_file}...")
    sectors = sector_rotation.rank_sectors(period=period, sectors_file=sectors_file)
    
    if not sectors:
        report_lines.append("\n❌ Failed to analyze sectors. Check data availability.")
        return "\n".join(report_lines)
    
    # Add recommendation summary at the top
    report_lines.append(display_recommendation_summary(sectors))
    
    # Filter to top N if requested
    display_sectors = sectors[:top_n] if top_n else sectors
    
    # Sector rankings
    report_lines.append("\n" + "=" * 80)
    report_lines.append("📊 SECTOR STRENGTH RANKING")
    report_lines.append("=" * 80)
    
    for sector in display_sectors:
        report_lines.append(display_sector_detail(sector))
    
    if top_n and len(sectors) > top_n:
        report_lines.append(f"\n... and {len(sectors) - top_n} more sectors")
        report_lines.append(f"(Run without --top flag to see all sectors)")
    
    # Allocation recommendations
    report_lines.append(display_allocation_summary(sectors))
    
    # Rotation alerts (if comparison requested)
    if compare:
        previous = load_previous_scores(period)
        report_lines.append(display_rotation_alerts(sectors, previous))
    
    # Summary statistics
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
        if isinstance(sector_return, str):
            report_lines.append(f"  {i}. {s['ticker']}: Score {s['total_score']}/14")
        else:
            report_lines.append(f"  {i}. {s['ticker']}: {sector_return:+.2f}% "
                              f"(vs SPY {spy_return:+.2f}%) - Score {s['total_score']}/14")
    
    report_lines.append(f"\nBottom Performers:")
    for i, s in enumerate(sectors[-3:], 1):
        rs = s.get('relative_strength', {})
        sector_return = rs.get('sector_return', 0)
        spy_return = rs.get('spy_return', 0)
        if isinstance(sector_return, str):
            report_lines.append(f"  {i}. {s['ticker']}: Score {s['total_score']}/14")
        else:
            report_lines.append(f"  {i}. {s['ticker']}: {sector_return:+.2f}% "
                              f"(vs SPY {spy_return:+.2f}%) - Score {s['total_score']}/14")
    
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


def save_report(report: str, period: str, output_dir: str) -> None:
    """Save dashboard report to file."""
    create_output_directory(output_dir)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"sector_dashboard_{period}_{timestamp}.txt"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w') as f:
        f.write(report)
    
    print(f"\n💾 Report saved: {filepath}")


def save_current_scores(sectors: List[Dict], period: str) -> None:
    """Save current sector scores for future comparison."""
    cache_dir = 'sector_cache'
    create_output_directory(cache_dir)
    
    filename = f"scores_{period}_latest.json"
    filepath = os.path.join(cache_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(sectors, f, indent=2, default=str)
    
    print(f"💾 Scores cached for future comparison")


def load_previous_scores(period: str) -> Optional[List[Dict]]:
    """Load previous sector scores for comparison."""
    cache_dir = 'sector_cache'
    filename = f"scores_{period}_latest.json"
    filepath = os.path.join(cache_dir, filename)
    
    if not os.path.exists(filepath):
        return None
    
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Could not load previous scores: {e}")
        return None


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Sector Rotation Dashboard - Analyze sector strength and generate rotation recommendations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                     # Basic 3-month analysis
  %(prog)s -p 6mo              # 6-month analysis  
  %(prog)s --compare           # Compare to previous run
  %(prog)s --top 5             # Show only top 5 sectors
  %(prog)s -o sector_reports   # Save detailed report
        """
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
        help='Compare with previous run to detect rotations'
    )
    
    parser.add_argument(
        '--top',
        type=int,
        metavar='N',
        help='Show only top N sectors'
    )
    
    parser.add_argument(
        '--sectors-file',
        default='ticker_lists/sector_etfs.txt',
        help='Path to file containing sector ETF tickers (default: ticker_lists/sector_etfs.txt)'
    )
    
    args = parser.parse_args()
    
    try:
        # Generate dashboard
        report = generate_dashboard_report(
            period=args.period,
            output_dir=args.output_dir,
            compare=args.compare,
            top_n=args.top,
            sectors_file=args.sectors_file
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
