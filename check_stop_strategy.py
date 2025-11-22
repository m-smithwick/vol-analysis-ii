"""
Quick diagnostic to determine which stop strategy was used in backtest.
"""

import pandas as pd
import sys

def check_stop_strategy(csv_path):
    """Check which stop strategy was used based on exit type distribution."""
    df = pd.read_csv(csv_path)
    
    print("\n🔍 STOP STRATEGY DIAGNOSTIC")
    print("="*60)
    
    # Check exit type distribution
    print("\nExit Type Distribution:")
    for exit_type in df['exit_type'].unique():
        if pd.isna(exit_type):
            continue
        count = (df['exit_type'] == exit_type).sum()
        pct = count / len(df) * 100
        print(f"  {exit_type}: {count} ({pct:.1f}%)")
    
    # Key diagnostic: Check for stop strategy markers
    print("\n🔬 Stop Strategy Indicators:")
    
    # Check 1: Presence of time_decay stops
    time_decay = df[df['exit_type'] == 'TIME_DECAY_STOP']
    if len(time_decay) > 0:
        print(f"  ✓ TIME_DECAY_STOP found: {len(time_decay)} trades")
        print(f"    R-multiple range: {time_decay['r_multiple'].min():.2f}R to {time_decay['r_multiple'].max():.2f}R")
        
        # Check if stops are actually varying
        unique_r = time_decay['r_multiple'].nunique()
        if unique_r <= 3:
            print(f"    ⚠️  WARNING: Only {unique_r} unique R-multiples")
            print(f"    This suggests stops are NOT tightening over time")
            print(f"    Expected: Range from -2.5R to -1.0R")
            print(f"    Actual: Mostly -1.00R")
    else:
        print("  ✗ TIME_DECAY_STOP not found")
    
    # Check 2: Look for other variable stop types
    for stop_type in ['VOL_REGIME_STOP', 'ATR_DYNAMIC_STOP', 'PCT_TRAIL_STOP']:
        if (df['exit_type'] == stop_type).any():
            count = (df['exit_type'] == stop_type).sum()
            print(f"  ✓ {stop_type} found: {count} trades")
    
    # Check 3: Presence of HARD_STOP (static strategy marker)
    hard_stop = df[df['exit_type'] == 'HARD_STOP']
    if len(hard_stop) > 0:
        print(f"  ✓ HARD_STOP found: {len(hard_stop)} trades")
        print(f"    (Used with static stop strategy)")
    
    # Diagnosis
    print("\n💡 DIAGNOSIS:")
    if len(time_decay) > 0:
        print("  Stop strategy WAS set to 'time_decay'")
        print("  BUT stops are not tightening correctly")
        print("\n  Possible causes:")
        print("  1. Bug in _calculate_time_decay_stop() logic")
        print("  2. Stop updates not persisting across bars")
        print("  3. bars_in_trade calculation issue")
        print("  4. ATR values invalid/NaN")
    else:
        print("  Stop strategy was likely 'static' (not time_decay)")
        print("  Variable stops were never enabled")
    
    print("\n📋 RECOMMENDED ACTION:")
    if len(time_decay) > 0:
        print("  1. Add debug logging to _calculate_time_decay_stop()")
        print("  2. Verify stop updates persist in update_position()")
        print("  3. Check ATR20 column for NaN/invalid values")
        print("  4. Re-run with logging enabled")
    else:
        print("  Re-run backtest with stop_strategy='time_decay'")
        print("  Example: risk_mgr = RiskManager(100000, 0.75, 'time_decay')")
    
    print("="*60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_stop_strategy.py <portfolio_log.csv>")
        sys.exit(1)
    
    check_stop_strategy(sys.argv[1])
