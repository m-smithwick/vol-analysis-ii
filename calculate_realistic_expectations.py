#!/usr/bin/env python3
"""
Comprehensive Expected Value Calculator
========================================

Calculates ACTUAL expected returns by analyzing the full entry-exit flow distribution.

This script:
1. Parses all individual backtest files
2. Extracts every trade's entry signal → exit signal path
3. Builds frequency matrix showing common vs rare paths
4. Calculates weighted average returns (what you'll ACTUALLY get)
5. Provides portfolio-level performance estimates
"""

import pandas as pd
import numpy as np
from pathlib import Path
import re
from collections import defaultdict


def parse_individual_backtest_files(backtest_dir: str = 'backtest_results'):
    """
    Parse all individual ticker backtest files to extract trade-level data.
    
    Returns:
        List[Dict]: All trades with entry signal, exit signal, and return
    """
    backtest_path = Path(backtest_dir)
    
    # Find all individual ticker files (not AGGREGATE)
    ticker_files = [f for f in backtest_path.glob('*_24mo_backtest_*.txt')
                   if not f.name.startswith('AGGREGATE')]
    
    print(f"📁 Found {len(ticker_files)} individual backtest files\n")
    
    all_trades = []
    
    for filepath in ticker_files:
        ticker = filepath.name.split('_')[0]
        
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Parse trades from the file
            lines = content.split('\n')
            
            current_trade = None
            
            for i, line in enumerate(lines):
                # Look for trade entries
                if line.strip().startswith('Trade #'):
                    current_trade = {
                        'ticker': ticker,
                        'entry_signal': None,
                        'exit_signal': None,
                        'return_pct': None
                    }
                
                # Extract entry signal (look for emoji markers)
                elif current_trade and 'Entry:' in line:
                    # Look ahead for entry signals
                    for j in range(i, min(i+10, len(lines))):
                        if '🟢' in lines[j] or 'Strong Buy' in lines[j]:
                            current_trade['entry_signal'] = 'Strong_Buy'
                        elif '🟡' in lines[j] or 'Moderate Buy' in lines[j]:
                            current_trade['entry_signal'] = 'Moderate_Buy'
                        elif '💎' in lines[j] or 'Stealth' in lines[j]:
                            current_trade['entry_signal'] = 'Stealth_Accumulation'
                        elif '⭐' in lines[j] or 'Confluence' in lines[j]:
                            current_trade['entry_signal'] = 'Confluence_Signal'
                        elif '🔥' in lines[j] or 'Volume Breakout' in lines[j] or 'Breakout' in lines[j]:
                            current_trade['entry_signal'] = 'Volume_Breakout'
                
                # Extract exit signal
                elif current_trade and 'Exit:' in line:
                    # Look at this line and next few for exit type
                    for j in range(i, min(i+5, len(lines))):
                        if 'Momentum_Exhaustion' in lines[j] or 'Momentum Exhaustion' in lines[j]:
                            current_trade['exit_signal'] = 'Momentum_Exhaustion'
                        elif 'Profit_Taking' in lines[j] or 'Profit Taking' in lines[j]:
                            current_trade['exit_signal'] = 'Profit_Taking'
                        elif 'Distribution_Warning' in lines[j] or 'Distribution Warning' in lines[j]:
                            current_trade['exit_signal'] = 'Distribution_Warning'
                        elif 'Sell_Signal' in lines[j] or 'Sell Signal' in lines[j]:
                            current_trade['exit_signal'] = 'Sell_Signal'
                        elif 'Stop_Loss' in lines[j] or 'Stop Loss' in lines[j] or 'HARD_STOP' in lines[j]:
                            current_trade['exit_signal'] = 'Stop_Loss'
                        elif 'TIME_STOP' in lines[j]:
                            current_trade['exit_signal'] = 'Time_Stop'
                        elif 'TRAIL_STOP' in lines[j]:
                            current_trade['exit_signal'] = 'Trailing_Stop'
                
                # Extract return percentage
                elif current_trade and 'Result:' in line:
                    match = re.search(r'([-+]?\d+\.\d+)%', line)
                    if match:
                        current_trade['return_pct'] = float(match.group(1))
                        
                        # Save complete trade
                        if current_trade['entry_signal'] and current_trade['exit_signal']:
                            all_trades.append(current_trade)
                        
                        current_trade = None
        
        except Exception as e:
            print(f"  ⚠️ Error parsing {ticker}: {e}")
    
    print(f"✅ Extracted {len(all_trades)} complete trades\n")
    
    return all_trades


def build_entry_exit_matrix(trades: list):
    """
    Build matrix showing frequency and performance of each entry-exit combination.
    
    Returns:
        DataFrame with entry-exit paths and their statistics
    """
    matrix = defaultdict(lambda: {
        'count': 0,
        'returns': [],
        'wins': 0,
        'losses': 0
    })
    
    for trade in trades:
        entry = trade['entry_signal']
        exit = trade['exit_signal']
        return_pct = trade['return_pct']
        
        key = (entry, exit)
        matrix[key]['count'] += 1
        matrix[key]['returns'].append(return_pct)
        
        if return_pct > 0:
            matrix[key]['wins'] += 1
        else:
            matrix[key]['losses'] += 1
    
    # Convert to DataFrame for easier analysis
    rows = []
    
    for (entry, exit), data in matrix.items():
        if data['count'] > 0:
            returns = data['returns']
            
            rows.append({
                'Entry': entry,
                'Exit': exit,
                'Count': data['count'],
                'Win_Rate': (data['wins'] / data['count']) * 100,
                'Mean_Return': np.mean(returns),
                'Median_Return': np.median(returns),
                'Std_Dev': np.std(returns),
                'Best': max(returns),
                'Worst': min(returns)
            })
    
    df = pd.DataFrame(rows)
    
    if not df.empty:
        df = df.sort_values(['Entry', 'Count'], ascending=[True, False])
    
    return df


def calculate_realistic_expectations(trades: list):
    """
    Calculate what you'll ACTUALLY experience trading this system.
    """
    print(f"{'='*70}")
    print("💰 REALISTIC EXPECTED VALUE CALCULATION")
    print(f"{'='*70}\n")
    
    # Build entry-exit matrix
    matrix_df = build_entry_exit_matrix(trades)
    
    if matrix_df.empty:
        print("❌ No trades to analyze")
        return
    
    # Analyze by entry signal
    entry_signals = matrix_df['Entry'].unique()
    
    for entry in entry_signals:
        entry_trades = matrix_df[matrix_df['Entry'] == entry]
        total_entry_count = entry_trades['Count'].sum()
        
        print(f"\n{'='*70}")
        print(f"📊 {entry} ENTRY SIGNAL")
        print(f"{'='*70}")
        print(f"Total Trades: {total_entry_count}\n")
        
        print(f"{'Exit Signal':<25} {'Count':<8} {'%':<6} {'WinRate':<10} {'Mean':<10} {'Median':<10}")
        print("-"*75)
        
        weighted_mean = 0
        weighted_median = 0
        
        for _, row in entry_trades.iterrows():
            exit_sig = row['Exit']
            count = row['Count']
            pct_of_total = (count / total_entry_count) * 100
            win_rate = row['Win_Rate']
            mean_ret = row['Mean_Return']
            median_ret = row['Median_Return']
            
            # Weight by frequency
            weighted_mean += mean_ret * (count / total_entry_count)
            weighted_median += median_ret * (count / total_entry_count)
            
            # Truncate exit signal name if too long
            exit_display = exit_sig[:23] if len(exit_sig) > 23 else exit_sig
            
            print(f"{exit_display:<25} {count:<8} {pct_of_total:<6.1f} {win_rate:<10.1f}% {mean_ret:<+10.2f}% {median_ret:<+10.2f}%")
        
        print("-"*75)
        print(f"{'WEIGHTED AVERAGE':<25} {total_entry_count:<8} {'100.0':<6} {'':<10} {weighted_mean:<+10.2f}% {weighted_median:<+10.2f}%")
        
        print(f"\n💡 INTERPRETATION FOR {entry}:")
        print(f"   • You'll enter {total_entry_count} trades")
        print(f"   • Expected return: {weighted_median:+.2f}% (median) or {weighted_mean:+.2f}% (mean)")
        print(f"   • Most common exit: {entry_trades.nlargest(1, 'Count')['Exit'].iloc[0]} ({entry_trades.nlargest(1, 'Count')['Count'].iloc[0]} times)")
        
        # Show exit path distribution
        print(f"\n   Exit Path Distribution:")
        for _, row in entry_trades.iterrows():
            pct = (row['Count'] / total_entry_count) * 100
            if pct >= 10:
                emoji = "🎯" if pct >= 30 else "✓"
                print(f"     {emoji} {row['Exit']}: {pct:.1f}% of trades ({row['Count']})")
    
    # Overall system expectation
    print(f"\n\n{'='*70}")
    print("🎯 OVERALL SYSTEM EXPECTATIONS")
    print(f"{'='*70}\n")
    
    all_returns = [t['return_pct'] for t in trades]
    all_wins = [r for r in all_returns if r > 0]
    
    system_mean = np.mean(all_returns)
    system_median = np.median(all_returns)
    system_win_rate = len(all_wins) / len(all_returns) * 100
    
    print(f"Total Trades Analyzed: {len(trades)}")
    print(f"System Win Rate: {system_win_rate:.1f}%")
    print(f"System Mean Return: {system_mean:+.2f}%")
    print(f"System Median Return: {system_median:+.2f}%")
    print(f"\n💡 Use MEDIAN ({system_median:+.2f}%) for realistic expectations")
    
    # Calculate by percentiles
    p25 = np.percentile(all_returns, 25)
    p50 = np.percentile(all_returns, 50)
    p75 = np.percentile(all_returns, 75)
    
    print(f"\nReturn Distribution:")
    print(f"  25th percentile: {p25:+.2f}% (1 in 4 trades worse than this)")
    print(f"  50th percentile: {p50:+.2f}% (median - typical trade)")
    print(f"  75th percentile: {p75:+.2f}% (1 in 4 trades better than this)")
    
    # Portfolio-level calculation
    print(f"\n\n{'='*70}")
    print("💼 PORTFOLIO-LEVEL EXPECTATIONS")
    print(f"{'='*70}\n")
    
    trades_per_year = len(trades) / 2  # 24mo period
    
    print(f"Trades per Year (across all tickers): {trades_per_year:.0f}")
    print(f"Expected Median Return per Trade: {system_median:+.2f}%")
    print(f"\nIf trading with 5% of portfolio per trade:")
    print(f"  Annual Expectation: {trades_per_year * system_median * 0.05:.2f}% portfolio gain")
    print(f"\nIf trading with 10% of portfolio per trade:")
    print(f"  Annual Expectation: {trades_per_year * system_median * 0.10:.2f}% portfolio gain")
    print(f"\nIf trading with 20% of portfolio per trade:")
    print(f"  Annual Expectation: {trades_per_year * system_median * 0.20:.2f}% portfolio gain")
    
    print(f"\n⚠️ This assumes:")
    print(f"   • You trade all signals as they appear")
    print(f"   • No position sizing adjustments")
    print(f"   • No correlation between simultaneous trades")
    print(f"   • Future performs similar to past 24 months")


def show_best_vs_typical_scenarios(matrix_df: pd.DataFrame):
    """
    Compare best-case (optimal exits) vs typical-case (common exits).
    """
    print(f"\n\n{'='*70}")
    print("🎯 BEST-CASE VS TYPICAL-CASE COMPARISON")
    print(f"{'='*70}\n")
    
    # Find most common entry
    entry_counts = matrix_df.groupby('Entry')['Count'].sum().sort_values(ascending=False)
    primary_entry = entry_counts.index[0]
    
    primary_entry_data = matrix_df[matrix_df['Entry'] == primary_entry].sort_values('Count', ascending=False)
    
    print(f"Primary Entry Signal: {primary_entry}")
    print(f"Total {primary_entry} Trades: {entry_counts[primary_entry]}\n")
    
    # Best case: Gets optimal exit (Momentum or Profit Taking)
    optimal_exits = primary_entry_data[primary_entry_data['Exit'].isin(['Momentum_Exhaustion', 'Profit_Taking'])]
    
    if not optimal_exits.empty:
        optimal_count = optimal_exits['Count'].sum()
        optimal_return = (optimal_exits['Median_Return'] * optimal_exits['Count']).sum() / optimal_count
        optimal_pct = (optimal_count / entry_counts[primary_entry]) * 100
        
        print(f"✨ BEST CASE (Optimal Exits): {optimal_pct:.1f}% of trades")
        print(f"   Exits: {', '.join(optimal_exits['Exit'].values)}")
        print(f"   Frequency: {optimal_count}/{entry_counts[primary_entry]} trades")
        print(f"   Median Return: {optimal_return:+.2f}%")
    
    # Typical case: Most common exit paths
    top_3_exits = primary_entry_data.nlargest(3, 'Count')
    
    print(f"\n📊 TYPICAL CASE (Most Common Paths): {(top_3_exits['Count'].sum() / entry_counts[primary_entry] * 100):.1f}% of trades")
    
    for _, row in top_3_exits.iterrows():
        pct = (row['Count'] / entry_counts[primary_entry]) * 100
        print(f"   {row['Exit']}: {pct:.1f}% ({row['Count']} trades)")
        print(f"      Win Rate: {row['Win_Rate']:.1f}%, Median: {row['Median_Return']:+.2f}%")
    
    # Calculate typical weighted return
    typical_weighted = (top_3_exits['Median_Return'] * top_3_exits['Count']).sum() / top_3_exits['Count'].sum()
    
    print(f"\n   Typical Weighted Return: {typical_weighted:+.2f}%")
    
    # Show the gap
    if not optimal_exits.empty:
        gap = optimal_return - typical_weighted
        print(f"\n💡 REALITY CHECK:")
        print(f"   Best Case: {optimal_return:+.2f}% (but only {optimal_pct:.0f}% chance)")
        print(f"   Typical Case: {typical_weighted:+.2f}% (happens {(top_3_exits['Count'].sum() / entry_counts[primary_entry] * 100):.0f}% of time)")
        print(f"   Gap: {gap:.2f}%")
        print(f"\n   You're much more likely to experience the TYPICAL case.")


if __name__ == "__main__":
    print(f"\n{'='*70}")
    print("🔍 COMPREHENSIVE EXPECTED VALUE ANALYSIS")
    print(f"{'='*70}\n")
    
    print("Calculating REAL expected returns across all entry-exit combinations...\n")
    
    # Parse all trades
    trades = parse_individual_backtest_files()
    
    if not trades:
        print("❌ No trades found. Ensure backtest files exist.")
        print("   Run: python batch_backtest.py ibd.txt -p 24mo")
        exit(1)
    
    # Build matrix
    matrix_df = build_entry_exit_matrix(trades)
    
    # Calculate expectations
    calculate_realistic_expectations(trades)
    
    # Show best vs typical scenarios
    show_best_vs_typical_scenarios(matrix_df)
    
    print(f"\n\n{'='*70}")
    print("✅ EXPECTED VALUE CALCULATION COMPLETE")
    print(f"{'='*70}\n")
    
    print("📝 KEY TAKEAWAYS:")
    print("   • Exit signal returns are measured from ENTRY to EXIT")
    print("   • High-return exits are rare - most trades exit via common signals")
    print("   • Weighted median gives you realistic expectation")
    print("   • Plan for typical case, not best case")
