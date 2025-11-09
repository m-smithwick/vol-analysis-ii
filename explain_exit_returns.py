#!/usr/bin/env python3
"""
Exit Signal Return Explanation
===============================

Directly addresses the confusion:
"Why do exit signals show 90% win rates with +68% returns,
while entry signals show 56% win rates with +18% returns?"

Answer: They measure different things!
"""

import re
from pathlib import Path


def parse_aggregate_report(filepath: str):
    """Extract key numbers from aggregate report."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    print(f"{'='*70}")
    print("📊 UNDERSTANDING YOUR BACKTEST RESULTS")
    print(f"{'='*70}\n")
    
    # Extract entry signal data
    print("ENTRY SIGNALS (What Gets You INTO Trades):")
    print("-"*70)
    
    entry_pattern = r'(\d+)\. (.+?)\n.*?Total Trades: (\d+) \((\d+) closed.*?Win Rate: ([\d.]+)%.*?Average Return: ([-+][\d.]+)%.*?Median Return: ([-+][\d.]+)%'
    
    entries = re.findall(entry_pattern, content, re.DOTALL)
    
    entry_data = {}
    
    for match in entries[:5]:  # First 5 are entry signals
        rank, name, total, closed, win_rate, avg_ret, median_ret = match
        name_clean = name.strip()
        
        entry_data[name_clean] = {
            'total': int(total),
            'closed': int(closed),
            'win_rate': float(win_rate),
            'avg_return': float(avg_ret),
            'median_return': float(median_ret)
        }
        
        print(f"\n{rank}. {name_clean}")
        print(f"   Trades: {closed} closed out of {total}")
        print(f"   Win Rate: {win_rate}%")
        print(f"   Average Return: {avg_ret}%")
        print(f"   Median Return: {median_ret}%")
    
    # Extract exit signal data
    print(f"\n\n{'='*70}")
    print("EXIT SIGNALS (What Gets You OUT OF Trades):")
    print("-"*70)
    
    exit_data = {}
    
    for match in entries[5:]:  # Remaining are exit signals
        rank, name, total, closed, win_rate, avg_ret, median_ret = match
        name_clean = name.strip()
        
        exit_data[name_clean] = {
            'total': int(total),
            'closed': int(closed),
            'win_rate': float(win_rate),
            'avg_return': float(avg_ret),
            'median_return': float(median_ret)
        }
        
        print(f"\n{rank}. {name_clean}")
        print(f"   Times Used: {closed} exits")
        print(f"   Win Rate: {win_rate}%")
        print(f"   Average Return: {avg_ret}%")
        print(f"   Median Return: {median_ret}%")
    
    return entry_data, exit_data


def explain_the_confusion(entry_data: dict, exit_data: dict):
    """Explain why exit returns look higher than entry returns."""
    
    print(f"\n\n{'='*70}")
    print("💡 THE KEY INSIGHT YOU'RE MISSING")
    print(f"{'='*70}\n")
    
    print("Exit signal returns are NOT independent from entry returns!")
    print("They're the SAME trades, just grouped by how they exited.\n")
    
    # Get Stealth data
    stealth_name = [k for k in entry_data.keys() if 'Stealth' in k][0]
    stealth = entry_data[stealth_name]
    
    # Get exit data
    momentum_name = [k for k in exit_data.keys() if 'Momentum' in k][0] if exit_data else None
    profit_name = [k for k in exit_data.keys() if 'Profit' in k][0] if exit_data else None
    
    momentum = exit_data.get(momentum_name, {}) if momentum_name else {}
    profit = exit_data.get(profit_name, {}) if profit_name else {}
    
    total_closed_trades = sum(e['closed'] for e in entry_data.values())
    
    print("ENTRY SIGNAL (Stealth Accumulation):")
    print(f"  • {stealth['closed']} trades entered")
    print(f"  • {stealth['win_rate']:.1f}% win rate")
    print(f"  • {stealth['median_return']:+.2f}% median return")
    print(f"  → This measures ALL Stealth trades, regardless of exit\n")
    
    if momentum:
        momentum_pct = (momentum['closed'] / total_closed_trades) * 100
        print(f"EXIT SIGNAL (Momentum Exhaustion):")
        print(f"  • {momentum['closed']} trades exited this way")
        print(f"  • {momentum['win_rate']:.1f}% win rate")
        print(f"  • {momentum.get('median_return', momentum['avg_return']):+.2f}% return")
        print(f"  → This measures trades that EXITED via Momentum")
        print(f"  → These could have entered via ANY entry signal\n")
        
        print(f"THE CATCH:")
        print(f"  • Only {momentum_pct:.1f}% of ALL trades exit via Momentum")
        print(f"  • That's {momentum['closed']} out of {total_closed_trades} total trades")
        print(f"  • If you enter on Stealth {stealth['closed']} times...")
        print(f"  • You'll only get Momentum exit ~{stealth['closed'] * momentum_pct / 100:.0f} times")
        print(f"  • The other ~{stealth['closed'] * (100 - momentum_pct) / 100:.0f} trades exit via other signals")
    
    if profit:
        profit_pct = (profit['closed'] / total_closed_trades) * 100
        print(f"\n  • {profit_pct:.1f}% exit via Profit Taking ({profit['closed']} times)")
    
    # Show what really happens
    print(f"\n\n{'='*70}")
    print("📊 WHAT ACTUALLY HAPPENS (Example)")
    print(f"{'='*70}\n")
    
    print(f"If you enter 100 Stealth Accumulation trades:")
    
    if momentum:
        momentum_count = int(100 * momentum_pct / 100)
        print(f"  • ~{momentum_count} will exit via Momentum ({momentum.get('median_return', momentum['avg_return']):+.2f}% each)")
    
    if profit:
        profit_count = int(100 * profit_pct / 100)
        print(f"  • ~{profit_count} will exit via Profit Taking (~{profit.get('median_return', profit['avg_return']):+.2f}% each)")
    
    # Estimate remaining exits
    if momentum and profit:
        other_count = 100 - momentum_count - profit_count
        print(f"  • ~{other_count} will exit via other signals (Distribution, Sell, Stops)")
        print(f"    These typically return -5% to +5%")
    
    # Calculate weighted expectation
    if momentum and profit:
        weighted = (momentum_count * momentum.get('median_return', momentum['avg_return']) + 
                   profit_count * profit.get('median_return', profit['avg_return']) +
                   other_count * 0) / 100
        
        print(f"\n  💰 Weighted Expected Return: {weighted:+.2f}%")
        print(f"     (This is closer to reality than cherry-picked exit returns)")


def show_critical_insight():
    """Show the main insight about entry vs exit returns."""
    
    print(f"\n\n{'='*70}")
    print("🎯 CRITICAL INSIGHT")
    print(f"{'='*70}\n")
    
    print("You CANNOT choose between:")
    print("  ❌ Stealth Entry (56% win, +3% return)")
    print("  ❌ Momentum Exit (90% win, +68% return)")
    print()
    print("You MUST use BOTH:")
    print("  ✅ Stealth Entry (gets you in)")
    print("  ✅ Momentum Exit (gets you out, when it fires)")
    print()
    print("The question is: How OFTEN does Momentum fire?")
    print()
    print("Answer: RARELY!")
    print("  • Momentum fires ~20% of the time")
    print("  • Profit Taking fires ~13% of the time")
    print("  • Other exits (Distribution, Sell, Stops): ~67% of the time")
    print()
    print("So your ACTUAL returns are:")
    print("  • 20% of trades: Get Momentum's great returns")
    print("  • 13% of trades: Get Profit Taking's good returns")
    print("  • 67% of trades: Get mediocre returns or losses")
    print()
    print("Weighted average = Much lower than cherry-picked exit returns")


if __name__ == "__main__":
    import sys
    
    # Find most recent aggregate file
    results_dir = Path('backtest_results')
    aggregate_files = list(results_dir.glob('AGGREGATE_optimization_*.txt'))
    
    if not aggregate_files:
        print("❌ No aggregate backtest file found")
        print("Run: python batch_backtest.py ibd.txt -p 24mo")
        sys.exit(1)
    
    filepath = str(max(aggregate_files, key=lambda p: p.stat().st_mtime))
    
    print(f"\n🔍 EXPLAINING YOUR BACKTEST RESULTS")
    print(f"📁 File: {Path(filepath).name}\n")
    
    # Parse and explain
    entry_data, exit_data = parse_aggregate_report(filepath)
    
    # Explain the confusion
    explain_the_confusion(entry_data, exit_data)
    
    # Show critical insight
    show_critical_insight()
    
    print(f"\n\n{'='*70}")
    print("✅ EXPLANATION COMPLETE")
    print(f"{'='*70}\n")
    
    print("📝 BOTTOM LINE:")
    print("   Exit signals with high returns are RARE")
    print("   Most of your trades will exit via common signals")
    print("   Expected return = weighted average of all exit paths")
    print("   NOT the best-case scenario you see in exit rankings")
