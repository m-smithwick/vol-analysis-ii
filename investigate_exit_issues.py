"""
Phase 1: Exit Type Investigation Script

Investigates TIME_DECAY_STOP (0% WR) and SIGNAL_EXIT (high R-multiple) issues.
"""

import pandas as pd
import sys
import os

def investigate_time_decay_stop(csv_path: str):
    """Investigate TIME_DECAY_STOP trades."""
    print("\n" + "="*80)
    print("🔍 INVESTIGATING TIME_DECAY_STOP (0% Win Rate)")
    print("="*80)
    
    df = pd.read_csv(csv_path)
    
    # Filter TIME_DECAY_STOP trades
    time_decay = df[df['exit_type'] == 'TIME_DECAY_STOP'].copy()
    
    if len(time_decay) == 0:
        print("⚠️  No TIME_DECAY_STOP trades found in log")
        return
    
    print(f"\n📊 TIME_DECAY_STOP Trades: {len(time_decay)}")
    print(f"   Win Rate: {(time_decay['profit_pct'] > 0).sum() / len(time_decay) * 100:.1f}%")
    print(f"   Avg R-Multiple: {time_decay['r_multiple'].mean():.2f}R")
    print(f"   Avg Profit %: {time_decay['profit_pct'].mean():.2f}%")
    
    # Check for calculation issues
    print("\n🔬 DIAGNOSTIC CHECKS:")
    
    # Check 1: Are all truly losses?
    winners = time_decay[time_decay['profit_pct'] > 0]
    print(f"\n1. Winning TIME_DECAY_STOP trades: {len(winners)} ({len(winners)/len(time_decay)*100:.1f}%)")
    if len(winners) > 0:
        print("   ⚠️  ANOMALY: Win rate should be 0% but found winners!")
        print(f"   Sample winner R-multiples: {winners['r_multiple'].head(3).tolist()}")
    
    # Check 2: R-multiple distribution
    print(f"\n2. R-Multiple Distribution:")
    print(f"   Min: {time_decay['r_multiple'].min():.2f}R")
    print(f"   25th percentile: {time_decay['r_multiple'].quantile(0.25):.2f}R")
    print(f"   Median: {time_decay['r_multiple'].median():.2f}R")
    print(f"   75th percentile: {time_decay['r_multiple'].quantile(0.75):.2f}R")
    print(f"   Max: {time_decay['r_multiple'].max():.2f}R")
    
    # Check 3: Sample trades
    print(f"\n3. Sample TIME_DECAY_STOP Trades:")
    sample = time_decay.sample(min(5, len(time_decay)))
    for idx, row in sample.iterrows():
        print(f"   {row['ticker']} - Entry: ${row.get('entry_price', 'N/A'):.2f}, "
              f"Exit: ${row.get('exit_price', 'N/A'):.2f}, "
              f"R: {row['r_multiple']:.2f}R, "
              f"Profit: {row['profit_pct']:.2f}%")
    
    # Check 4: Bars held distribution
    print(f"\n4. Holding Period Analysis:")
    bars_col = 'bars_held' if 'bars_held' in time_decay.columns else 'holding_days'
    if bars_col in time_decay.columns:
        print(f"   Min bars: {time_decay[bars_col].min()}")
        print(f"   Avg bars: {time_decay[bars_col].mean():.1f}")
        print(f"   Max bars: {time_decay[bars_col].max()}")
        print(f"   (Time-decay should tighten after 5, 10, 15 bars)")
    else:
        print(f"   ⚠️  No bars_held or holding_days column found")
    
    # Check 5: Entry/Exit signal analysis
    if 'entry_signals' in time_decay.columns:
        print(f"\n5. Entry Signals for TIME_DECAY_STOP trades:")
        # This is a list, need to flatten
        all_signals = []
        for signals in time_decay['entry_signals'].dropna():
            if isinstance(signals, str):
                # May be stringified list
                import ast
                try:
                    signals = ast.literal_eval(signals)
                except:
                    pass
            if isinstance(signals, list):
                all_signals.extend(signals)
        
        if all_signals:
            from collections import Counter
            signal_counts = Counter(all_signals)
            print(f"   Most common: {signal_counts.most_common(3)}")
    
    return time_decay


def investigate_signal_exit(csv_path: str):
    """Investigate SIGNAL_EXIT high R-multiples."""
    print("\n" + "="*80)
    print("🔍 INVESTIGATING SIGNAL_EXIT (High R-Multiples)")
    print("="*80)
    
    df = pd.read_csv(csv_path)
    
    # Filter SIGNAL_EXIT trades
    signal_exit = df[df['exit_type'] == 'SIGNAL_EXIT'].copy()
    
    if len(signal_exit) == 0:
        print("⚠️  No SIGNAL_EXIT trades found in log")
        return
    
    print(f"\n📊 SIGNAL_EXIT Trades: {len(signal_exit)}")
    print(f"   Win Rate: {(signal_exit['profit_pct'] > 0).sum() / len(signal_exit) * 100:.1f}%")
    print(f"   Avg R-Multiple: {signal_exit['r_multiple'].mean():.2f}R")
    print(f"   Avg Profit %: {signal_exit['profit_pct'].mean():.2f}%")
    
    print("\n🔬 DIAGNOSTIC CHECKS:")
    
    # Check 1: R-multiple distribution
    print(f"\n1. R-Multiple Distribution:")
    print(f"   Min: {signal_exit['r_multiple'].min():.2f}R")
    print(f"   25th percentile: {signal_exit['r_multiple'].quantile(0.25):.2f}R")
    print(f"   Median: {signal_exit['r_multiple'].median():.2f}R")
    print(f"   75th percentile: {signal_exit['r_multiple'].quantile(0.75):.2f}R")
    print(f"   Max: {signal_exit['r_multiple'].max():.2f}R")
    
    # Check 2: Compare with other exit types
    print(f"\n2. Comparison with Other Exit Types:")
    for exit_type in ['PROFIT_TARGET', 'TRAIL_STOP', 'TIME_STOP']:
        other = df[df['exit_type'] == exit_type]
        if len(other) > 0:
            print(f"   {exit_type}: Avg R = {other['r_multiple'].mean():.2f}R ({len(other)} trades)")
    
    # Check 3: Are these partial exits?
    if 'partial_exit' in signal_exit.columns:
        partial = signal_exit[signal_exit['partial_exit'] == True]
        print(f"\n3. Partial Exit Analysis:")
        print(f"   Partial exits: {len(partial)} ({len(partial)/len(signal_exit)*100:.1f}%)")
        print(f"   Full exits: {len(signal_exit) - len(partial)}")
    
    # Check 4: Manual R calculation for sample trades
    print(f"\n4. Manual R-Multiple Verification (Sample Trades):")
    sample = signal_exit.nlargest(3, 'r_multiple')  # Top 3 R-multiples
    
    if 'entry_price' in sample.columns and 'exit_price' in sample.columns:
        for idx, row in sample.iterrows():
            entry = row.get('entry_price', None)
            exit_p = row.get('exit_price', None)
            reported_r = row['r_multiple']
            
            # We need stop price to calculate R, but it's not in the CSV
            # Instead, calculate profit %
            if entry and exit_p:
                profit_pct = ((exit_p - entry) / entry) * 100
                print(f"\n   {row['ticker']}:")
                print(f"      Entry: ${entry:.2f}, Exit: ${exit_p:.2f}")
                print(f"      Profit: {profit_pct:.2f}%")
                bars_col = 'bars_held' if 'bars_held' in signal_exit.columns else 'holding_days'
                bars_held = row.get(bars_col, 'N/A')
                print(f"      Reported R: {reported_r:.2f}R")
                print(f"      Bars held: {bars_held}")
                
                # If R is very high, the stop must have been very tight
                # R = profit / risk, so risk = profit / R
                if reported_r > 0:
                    implied_stop = entry - ((exit_p - entry) / reported_r)
                    print(f"      Implied stop: ${implied_stop:.2f} (based on R-multiple)")
    
    # Check 5: Profit taken 50% flag
    if 'profit_taken_50pct' in signal_exit.columns:
        scaled = signal_exit[signal_exit['profit_taken_50pct'] == True]
        print(f"\n5. Profit Scaling Analysis:")
        print(f"   Trades with 50% scaled: {len(scaled)} ({len(scaled)/len(signal_exit)*100:.1f}%)")
        if len(scaled) > 0:
            print(f"   Avg R (scaled): {scaled['r_multiple'].mean():.2f}R")
        
        not_scaled = signal_exit[signal_exit['profit_taken_50pct'] == False]
        if len(not_scaled) > 0:
            print(f"   Avg R (not scaled): {not_scaled['r_multiple'].mean():.2f}R")
    
    return signal_exit


def compare_exit_types(csv_path: str):
    """Compare all exit types side by side."""
    print("\n" + "="*80)
    print("📊 EXIT TYPE COMPARISON")
    print("="*80)
    
    df = pd.read_csv(csv_path)
    
    print(f"\n{'Exit Type':<20} {'Count':<8} {'Win Rate':<10} {'Avg R':<10} {'Med R':<10}")
    print("-" * 70)
    
    for exit_type in df['exit_type'].unique():
        if pd.isna(exit_type):
            continue
        
        subset = df[df['exit_type'] == exit_type]
        win_rate = (subset['profit_pct'] > 0).sum() / len(subset) * 100
        avg_r = subset['r_multiple'].mean()
        med_r = subset['r_multiple'].median()
        
        print(f"{exit_type:<20} {len(subset):<8} {win_rate:<10.1f}% {avg_r:<+10.2f}R {med_r:<+10.2f}R")


def main():
    """Main investigation function."""
    if len(sys.argv) < 2:
        print("Usage: python investigate_exit_issues.py <portfolio_trade_log.csv>")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    
    if not os.path.exists(csv_path):
        print(f"❌ Error: File not found: {csv_path}")
        sys.exit(1)
    
    print(f"\n🎯 EXIT ISSUE INVESTIGATION")
    print(f"   File: {os.path.basename(csv_path)}")
    
    # Run investigations
    time_decay_trades = investigate_time_decay_stop(csv_path)
    signal_exit_trades = investigate_signal_exit(csv_path)
    compare_exit_types(csv_path)
    
    print("\n" + "="*80)
    print("✅ INVESTIGATION COMPLETE")
    print("="*80)
    print("\nNext Steps:")
    print("1. Review the diagnostic output above")
    print("2. Check for calculation errors or data corruption")
    print("3. Verify stop placement logic in risk_manager.py")
    print("4. Re-run backtest with fixes if issues found")


if __name__ == "__main__":
    main()
