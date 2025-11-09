"""
Verify trade counting between aggregate and individual reports.

This script analyzes the trade counting logic to identify discrepancies.
"""

import os
import re
from collections import defaultdict


def extract_counts_from_aggregate(filepath):
    """Extract exit signal counts from aggregate report."""
    counts = {}
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Find exit strategy section
    exit_section = re.search(r'🛑 EXIT STRATEGY EFFECTIVENESS.*?(?=\n={50,})', content, re.DOTALL)
    
    if exit_section:
        section_text = exit_section.group(0)
        
        # Extract counts for each exit signal
        patterns = [
            (r'💜 Momentum Exhaustion.*?Total Trades: (\d+)', 'Momentum_Exhaustion'),
            (r'🟠 Profit Taking.*?Total Trades: (\d+)', 'Profit_Taking'),
            (r'⚠️ Distribution Warning.*?Total Trades: (\d+)', 'Distribution_Warning'),
            (r'🔴 Sell Signal.*?Total Trades: (\d+)', 'Sell_Signal'),
            (r'🛑 Stop Loss.*?Total Trades: (\d+)', 'Stop_Loss')
        ]
        
        for pattern, signal_name in patterns:
            match = re.search(pattern, section_text, re.DOTALL)
            if match:
                counts[signal_name] = int(match.group(1))
    
    return counts


def extract_counts_from_individual(directory):
    """Count exit signal occurrences from individual ticker reports."""
    counts = defaultdict(lambda: {'tickers': set(), 'total_mentions': 0, 'times_used': []})
    
    # Get all individual backtest files from recent run
    files = [f for f in os.listdir(directory) 
             if '_24mo_backtest_20251108_1348' in f and f.endswith('.txt')]
    
    for filename in sorted(files):
        filepath = os.path.join(directory, filename)
        ticker = filename.split('_')[0]
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Look for exit strategy section
        exit_section = re.search(r'🚪 EXIT STRATEGY COMPARISON:.*?(?=⭐ OPTIMAL|$)', content, re.DOTALL)
        
        if exit_section:
            section_text = exit_section.group(0)
            
            # Find "Times Used" for each signal
            signal_patterns = [
                (r'💜 Momentum Exhaustion:.*?Times Used: (\d+)', 'Momentum_Exhaustion'),
                (r'🟠 Profit Taking:.*?Times Used: (\d+)', 'Profit_Taking'),
                (r'⚠️ Distribution Warning:.*?Times Used: (\d+)', 'Distribution_Warning'),
                (r'🔴 Sell Signal:.*?Times Used: (\d+)', 'Sell_Signal'),
                (r'🛑 Stop Loss:.*?Times Used: (\d+)', 'Stop_Loss')
            ]
            
            for pattern, signal_name in signal_patterns:
                match = re.search(pattern, section_text, re.DOTALL)
                if match:
                    times_used = int(match.group(1))
                    counts[signal_name]['tickers'].add(ticker)
                    counts[signal_name]['total_mentions'] += 1
                    counts[signal_name]['times_used'].append((ticker, times_used))
    
    return counts


def main():
    directory = 'backtest_results'
    
    # Get latest aggregate report
    aggregate_files = sorted([f for f in os.listdir(directory) 
                             if f.startswith('AGGREGATE_optimization_24mo_20251108')],
                            reverse=True)
    
    if not aggregate_files:
        print("❌ No aggregate report found")
        return
    
    aggregate_path = os.path.join(directory, aggregate_files[0])
    
    print("="*80)
    print("🔍 TRADE COUNTING VERIFICATION")
    print("="*80)
    print(f"\nAnalyzing: {aggregate_files[0]}\n")
    
    # Extract counts
    aggregate_counts = extract_counts_from_aggregate(aggregate_path)
    individual_counts = extract_counts_from_individual(directory)
    
    print("📊 AGGREGATE REPORT COUNTS:")
    print("-"*80)
    for signal, count in sorted(aggregate_counts.items()):
        print(f"  {signal:.<30} {count:>5} trades")
    print()
    
    print("📄 INDIVIDUAL REPORT COUNTS (Sum of 'Times Used'):")
    print("-"*80)
    for signal, data in sorted(individual_counts.items()):
        total_times_used = sum(count for _, count in data['times_used'])
        ticker_count = len(data['tickers'])
        print(f"  {signal:.<30} {total_times_used:>5} times used across {ticker_count} tickers")
        
        # Show breakdown by ticker
        if data['times_used']:
            print(f"    Breakdown:")
            for ticker, count in sorted(data['times_used'], key=lambda x: x[1], reverse=True)[:5]:
                print(f"      {ticker}: {count}")
            if len(data['times_used']) > 5:
                print(f"      ... and {len(data['times_used']) - 5} more tickers")
    print()
    
    print("⚖️  COMPARISON:")
    print("-"*80)
    for signal in aggregate_counts:
        agg_count = aggregate_counts.get(signal, 0)
        ind_count = sum(count for _, count in individual_counts.get(signal, {}).get('times_used', []))
        
        diff = agg_count - ind_count
        diff_pct = (diff / agg_count * 100) if agg_count > 0 else 0
        
        status = "✅" if abs(diff) <= 5 else "⚠️" if abs(diff) <= 20 else "🚨"
        
        print(f"{status} {signal:.<30} Aggregate: {agg_count:>3} | Individual: {ind_count:>3} | Diff: {diff:>+4} ({diff_pct:>+6.1f}%)")
    print()
    
    print("💡 KEY INSIGHTS:")
    print("-"*80)
    print("If aggregate > individual:")
    print("  • May be counting same trade multiple times")
    print("  • May be counting all exit signal occurrences, not unique trades")
    print("  • Exit signals can overlap (trade can trigger multiple exits)")
    print()
    print("The discrepancy suggests aggregate is counting EXIT SIGNAL OCCURRENCES,")
    print("while individual reports show TRADES that used each exit.")
    print()
    print("📝 EXPLANATION:")
    print("A single trade can have MULTIPLE exit signals trigger simultaneously:")
    print("  Example: Trade exits with both 'Distribution Warning' AND 'Sell Signal'")
    print("  • Aggregate counts this as 1 Distribution + 1 Sell = 2 exit occurrences")
    print("  • Individual report counts this as 1 trade (using primary exit)")
    print()


if __name__ == "__main__":
    main()
