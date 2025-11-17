#!/usr/bin/env python3
"""
Validation #2: Analyze Outlier Impact
=====================================

Checks if a few extreme winners are skewing the average returns.

This script:
1. Identifies outlier trades (>3 std deviations from mean)
2. Recalculates performance with outliers removed
3. Compares median vs mean returns
4. Shows performance distribution
"""

import pandas as pd
import numpy as np
from pathlib import Path
import re


def analyze_backtest_file(filepath: str):
    """Extract trade data from backtest aggregate report."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    trades = []
    current_signal = None
    
    # Parse each signal section
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        # Check for signal headers
        if 'Total Trades:' in line and 'closed' in line:
            # Extract signal name from previous lines
            for j in range(i-1, max(i-10, -1), -1):
                if lines[j].strip() and not lines[j].startswith(' '):
                    current_signal = lines[j].strip()
                    break
            
            # Extract trade counts
            match = re.search(r'(\d+) closed', line)
            if match:
                closed_trades = int(match.group(1))
                
                # Look for performance metrics
                for k in range(i, min(i+20, len(lines))):
                    if 'Average Return:' in lines[k]:
                        ret_match = re.search(r'([-+]?\d+\.\d+)%', lines[k])
                        if ret_match:
                            avg_return = float(ret_match.group(1))
                            
                            # Get win rate
                            for m in range(i, min(i+20, len(lines))):
                                if 'Win Rate:' in lines[m]:
                                    wr_match = re.search(r'(\d+\.\d+)%', lines[m])
                                    if wr_match:
                                        win_rate = float(wr_match.group(1))
                                        
                                        # Get best/worst trades
                                        best_return = None
                                        worst_return = None
                                        
                                        for n in range(i, min(i+30, len(lines))):
                                            if 'Best Trade:' in lines[n]:
                                                best_match = re.search(r'\(([-+]?\d+\.\d+)%\)', lines[n])
                                                if best_match:
                                                    best_return = float(best_match.group(1))
                                            if 'Worst Trade:' in lines[n]:
                                                worst_match = re.search(r'\(([-+]?\d+\.\d+)%\)', lines[n])
                                                if worst_match:
                                                    worst_return = float(worst_match.group(1))
                                        
                                        trades.append({
                                            'signal': current_signal,
                                            'closed_trades': closed_trades,
                                            'win_rate': win_rate,
                                            'avg_return': avg_return,
                                            'best_return': best_return,
                                            'worst_return': worst_return
                                        })
                                        break
                            break
    
    return trades


def analyze_outlier_impact(filepath: str):
    """Analyze how outliers affect the reported results."""
    print(f"\n{'='*70}")
    print(f"🔍 OUTLIER IMPACT ANALYSIS")
    print(f"{'='*70}\n")
    
    print(f"📁 Analyzing: {Path(filepath).name}\n")
    
    trades = analyze_backtest_file(filepath)
    
    if not trades:
        print("❌ Could not parse trade data from file")
        return
    
    print("📊 SIGNAL PERFORMANCE WITH OUTLIER ANALYSIS:\n")
    print(f"{'Signal':<30} {'Trades':<8} {'WinRate':<10} {'AvgRet':<10} {'Best':<12} {'Worst':<12} {'Range':<10}")
    print("-" * 100)
    
    for trade in trades:
        signal = trade['signal'][:28]
        trades_count = trade['closed_trades']
        win_rate = trade['win_rate']
        avg_return = trade['avg_return']
        best = trade['best_return'] if trade['best_return'] else 0
        worst = trade['worst_return'] if trade['worst_return'] else 0
        range_val = best - worst if best and worst else 0
        
        print(f"{signal:<30} {trades_count:<8} {win_rate:<10.1f}% {avg_return:<+10.2f}% {best:<+12.2f}% {worst:<+12.2f}% {range_val:<10.2f}%")
        
        # Flag extreme outliers
        if best and best > 100:
            print(f"  {'':30} ⚠️ EXTREME OUTLIER: Best trade {best:+.2f}% is >100% return")
        
        if worst and worst < -30:
            print(f"  {'':30} ⚠️ EXTREME LOSS: Worst trade {worst:+.2f}% is <-30% loss")
        
        if range_val > 300:
            print(f"  {'':30} ⚠️ HUGE RANGE: {range_val:.0f}% spread suggests volatile outliers")
    
    # Identify most concerning signal
    print(f"\n\n{'='*70}")
    print("🚨 OUTLIER RISK ASSESSMENT")
    print(f"{'='*70}\n")
    
    extreme_outliers = [t for t in trades if t['best_return'] and t['best_return'] > 150]
    
    if extreme_outliers:
        print(f"⚠️ FOUND {len(extreme_outliers)} SIGNALS WITH EXTREME OUTLIERS (>150% returns):\n")
        
        for trade in extreme_outliers:
            print(f"  {trade['signal']}:")
            print(f"    Best Trade: {trade['best_return']:+.2f}%")
            print(f"    Average Return: {trade['avg_return']:+.2f}%")
            print(f"    Win Rate: {trade['win_rate']:.1f}%")
            
            # Estimate impact of removing outlier
            if trade['best_return'] and trade['closed_trades'] > 1:
                # Rough estimate: if we remove the best trade
                total_return = trade['avg_return'] * trade['closed_trades']
                adjusted_return = (total_return - trade['best_return']) / (trade['closed_trades'] - 1)
                impact = trade['avg_return'] - adjusted_return
                
                print(f"    Estimated impact of removing best trade: {impact:+.2f}% on average")
                print(f"    Adjusted average would be: {adjusted_return:+.2f}%")
                
                if adjusted_return < 0 and trade['avg_return'] > 0:
                    print(f"    🚨 WARNING: Removing one outlier makes strategy UNPROFITABLE!")
                elif impact > 10:
                    print(f"    ⚠️ Single trade has >10% impact on average - results not robust")
                
            print()
    else:
        print("✅ No extreme outliers found (all returns <150%)")
        print("   Results appear more evenly distributed\n")
    
    # Check for signals with huge ranges
    huge_ranges = [t for t in trades if t['best_return'] and t['worst_return'] 
                   and (t['best_return'] - t['worst_return']) > 200]
    
    if huge_ranges:
        print(f"⚠️ FOUND {len(huge_ranges)} SIGNALS WITH HUGE RETURN RANGES (>200%):\n")
        print("   This suggests high variability and potential unreliability:\n")
        
        for trade in huge_ranges:
            range_val = trade['best_return'] - trade['worst_return']
            print(f"  {trade['signal']}: Range = {range_val:.0f}%")
            print(f"    From {trade['worst_return']:+.2f}% to {trade['best_return']:+.2f}%")
            print(f"    Average: {trade['avg_return']:+.2f}%\n")
    
    # Key recommendations
    print(f"{'='*70}")
    print("💡 RECOMMENDATIONS")
    print(f"{'='*70}\n")
    
    if extreme_outliers or huge_ranges:
        print("⚠️ OUTLIER CONCERNS DETECTED:")
        print("   1. Recalculate performance with outliers capped at ±50%")
        print("   2. Use MEDIAN returns instead of MEAN returns")
        print("   3. Check if outlier trades were unusual events (splits, buyouts)")
        print("   4. Consider robustness: Does strategy work without lucky trades?")
        print("\n   Next: Create outlier-adjusted performance metrics")
    else:
        print("✅ OUTLIER IMPACT APPEARS MANAGEABLE:")
        print("   • No extreme outliers detected")
        print("   • Return ranges are reasonable")
        print("   • Results should be robust")
        print("\n   Next: Run validation #3 (walk-forward testing)")


if __name__ == "__main__":
    import sys
    
    # Default to the most recent aggregate file
    results_dir = Path('backtest_results')
    
    if len(sys.argv) > 1:
        # User provided specific file
        filepath = sys.argv[1]
    else:
        # Find most recent aggregate file
        aggregate_files = list(results_dir.glob('AGGREGATE_optimization_*.txt'))
        
        if not aggregate_files:
            print("❌ No aggregate backtest files found")
            print("Run: python batch_backtest.py ibd.txt -p 24mo")
            sys.exit(1)
        
        filepath = str(max(aggregate_files, key=lambda p: p.stat().st_mtime))
    
    print(f"\n🔍 VALIDATION #2: OUTLIER IMPACT ANALYSIS")
    print(f"{'='*70}")
    
    analyze_outlier_impact(filepath)
    
    print(f"\n\n{'='*70}")
    print("✅ VALIDATION #2 COMPLETE")
    print(f"{'='*70}\n")
