#!/usr/bin/env python3
"""
Validation #3: Deep Dive into Signal Performance
=================================================

Examines individual trades for a specific signal to understand
the return distribution and verify calculations.

Focus: Momentum Exhaustion exit (90.6% win rate, +68.22% avg seems impossible)
"""

import pandas as pd
import numpy as np
from pathlib import Path


def analyze_momentum_exhaustion_trades():
    """
    Analyze all individual ticker backtest files to extract Momentum Exhaustion trades.
    """
    print(f"\n{'='*70}")
    print("🔍 MOMENTUM EXHAUSTION DETAILED ANALYSIS")
    print(f"{'='*70}\n")
    
    backtest_dir = Path('backtest_results')
    
    # Find all individual ticker backtest files (not aggregate)
    ticker_files = [f for f in backtest_dir.glob('*_24mo_backtest_*.txt') 
                   if not f.name.startswith('AGGREGATE')]
    
    if not ticker_files:
        print("❌ No individual backtest files found")
        print("   Run: python batch_backtest.py ibd.txt -p 24mo")
        return
    
    print(f"📁 Found {len(ticker_files)} individual backtest files\n")
    
    all_momentum_trades = []
    tickers_with_momentum = []
    
    # Parse each file for Momentum Exhaustion exit trades
    for filepath in ticker_files:
        ticker = filepath.name.split('_')[0]
        
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Look for trades that exited via Momentum Exhaustion
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                if 'Momentum_Exhaustion' in line or 'Momentum Exhaustion' in line:
                    # Look backwards for return percentage
                    for j in range(max(0, i-10), i):
                        if 'Return:' in lines[j] or 'Profit:' in lines[j]:
                            # Extract percentage
                            import re
                            match = re.search(r'([-+]?\d+\.\d+)%', lines[j])
                            if match:
                                return_pct = float(match.group(1))
                                all_momentum_trades.append({
                                    'ticker': ticker,
                                    'return_pct': return_pct
                                })
                                
                                if ticker not in tickers_with_momentum:
                                    tickers_with_momentum.append(ticker)
                                break
        
        except Exception as e:
            print(f"  ⚠️ Error reading {ticker}: {e}")
    
    if not all_momentum_trades:
        print("❌ No Momentum Exhaustion trades found in files")
        print("   Files may use different exit signal names")
        return
    
    # Analyze the distribution
    returns = [t['return_pct'] for t in all_momentum_trades]
    
    print(f"📊 MOMENTUM EXHAUSTION TRADE DISTRIBUTION:")
    print(f"   Total Trades Found: {len(returns)}")
    print(f"   From {len(tickers_with_momentum)} tickers: {', '.join(tickers_with_momentum[:10])}")
    if len(tickers_with_momentum) > 10:
        print(f"   (and {len(tickers_with_momentum)-10} more)")
    print()
    
    # Calculate statistics
    mean_return = np.mean(returns)
    median_return = np.median(returns)
    std_return = np.std(returns)
    
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    
    print(f"   Mean Return: {mean_return:+.2f}%")
    print(f"   Median Return: {median_return:+.2f}%")
    print(f"   Std Deviation: {std_return:.2f}%")
    print(f"   Min: {min(returns):+.2f}%")
    print(f"   Max: {max(returns):+.2f}%")
    print()
    
    print(f"   Wins: {len(wins)} ({len(wins)/len(returns)*100:.1f}%)")
    print(f"   Losses: {len(losses)} ({len(losses)/len(returns)*100:.1f}%)")
    print(f"   Avg Win: {np.mean(wins):+.2f}% | Avg Loss: {np.mean(losses):+.2f}%")
    print()
    
    # Return distribution
    print("   Return Distribution:")
    bins = [-100, -20, -10, 0, 10, 20, 50, 100, 500]
    hist, _ = np.histogram(returns, bins=bins)
    
    for i in range(len(bins)-1):
        count = hist[i]
        pct = (count / len(returns)) * 100
        print(f"     {bins[i]:+5.0f}% to {bins[i+1]:+5.0f}%: {count:3d} trades ({pct:4.1f}%)")
    
    # Identify outliers (>3 std dev)
    outlier_threshold = 3 * std_return
    outliers = [t for t in all_momentum_trades if abs(t['return_pct'] - mean_return) > outlier_threshold]
    
    print(f"\n   Outliers (>3σ from mean): {len(outliers)}")
    if outliers:
        print("   Outlier trades:")
        for out in sorted(outliers, key=lambda x: abs(x['return_pct']), reverse=True)[:5]:
            print(f"     {out['ticker']}: {out['return_pct']:+.2f}%")
    
    # Check median vs mean difference
    print(f"\n{'='*70}")
    print("🎯 MEAN vs MEDIAN COMPARISON")
    print(f"{'='*70}\n")
    
    diff = mean_return - median_return
    
    print(f"   Mean Return: {mean_return:+.2f}%")
    print(f"   Median Return: {median_return:+.2f}%")
    print(f"   Difference: {diff:+.2f}%")
    print()
    
    if abs(diff) < 5:
        print("   ✅ Mean and median are close - distribution is symmetric")
        print("      Results are likely robust and not skewed by outliers")
    elif diff > 5:
        print("   ⚠️ Mean > Median by {diff:.1f}% - positive skew from outliers")
        print("      A few large winners are inflating the average")
        print("      MEDIAN is more representative of typical performance")
    else:
        print("   ⚠️ Median > Mean - negative skew from large losses")
        print("      A few large losses are dragging down the average")
    
    # Adjusted performance without outliers
    if outliers:
        non_outlier_returns = [r for r in returns if abs(r - mean_return) <= outlier_threshold]
        
        if non_outlier_returns:
            adjusted_mean = np.mean(non_outlier_returns)
            adjusted_wins = [r for r in non_outlier_returns if r > 0]
            adjusted_win_rate = len(adjusted_wins) / len(non_outlier_returns) * 100
            
            print(f"\n📊 PERFORMANCE WITHOUT OUTLIERS:")
            print(f"   Trades: {len(non_outlier_returns)} (removed {len(outliers)})")
            print(f"   Adjusted Mean: {adjusted_mean:+.2f}% (was {mean_return:+.2f}%)")
            print(f"   Adjusted Win Rate: {adjusted_win_rate:.1f}%")
            print(f"   Impact: {mean_return - adjusted_mean:+.2f}% difference")
            
            if abs(mean_return - adjusted_mean) > 10:
                print(f"\n   🚨 MAJOR CONCERN: Outliers change average by >10%!")
                print(f"      Strategy performance is NOT ROBUST")
                print(f"      Do not rely on mean returns - use median instead")


if __name__ == "__main__":
    print(f"\n🔍 VALIDATION #3: SIGNAL DETAIL ANALYSIS")
    print(f"{'='*70}")
    print("\nFocusing on Momentum Exhaustion exit...")
    print("(This signal shows 90.6% win rate with +68.22% avg return)\n")
    
    analyze_momentum_exhaustion_trades()
    
    print(f"\n\n{'='*70}")
    print("✅ VALIDATION #3 COMPLETE")
    print(f"{'='*70}\n")
