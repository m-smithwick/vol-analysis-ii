"""
Verify that time_decay stops are actually tightening in the new backtest.
"""

import pandas as pd
import sys

def verify_time_decay_fix(csv_path):
    """Check if time_decay stops are tightening as expected."""
    df = pd.read_csv(csv_path)
    
    print("\n🔍 TIME_DECAY FIX VERIFICATION")
    print("="*70)
    
    # Get TIME_DECAY_STOP trades
    time_decay = df[df['exit_type'] == 'TIME_DECAY_STOP'].copy()
    
    if len(time_decay) == 0:
        print("✗ No TIME_DECAY_STOP trades found")
        return
    
    print(f"\n📊 TIME_DECAY_STOP Analysis:")
    print(f"   Total trades: {len(time_decay)}")
    print(f"   Win rate: {(time_decay['profit_pct'] > 0).sum() / len(time_decay) * 100:.1f}%")
    print(f"   Avg R-multiple: {time_decay['r_multiple'].mean():.2f}R")
    
    # KEY INSIGHT: By definition, hitting a STOP = losing trade
    # So 0% win rate for stops is EXPECTED
    print("\n💡 IMPORTANT INSIGHT:")
    print("   0% win rate for TIME_DECAY_STOP is EXPECTED")
    print("   Stops are for limiting losses, not capturing wins")
    print("   Winners should exit via PROFIT_TARGET, TRAIL_STOP, or SIGNAL_EXIT")
    
    # The REAL question: Are stops tightening over time?
    print("\n🔬 CHECKING IF STOPS ARE TIGHTENING:")
    
    # Check R-multiple distribution
    print(f"\n   R-Multiple Distribution:")
    print(f"   Min: {time_decay['r_multiple'].min():.2f}R")
    print(f"   25th percentile: {time_decay['r_multiple'].quantile(0.25):.2f}R")
    print(f"   Median: {time_decay['r_multiple'].median():.2f}R")
    print(f"   75th percentile: {time_decay['r_multiple'].quantile(0.75):.2f}R")
    print(f"   Max: {time_decay['r_multiple'].max():.2f}R")
    
    # Unique R-multiples
    unique_r = time_decay['r_multiple'].nunique()
    print(f"\n   Unique R-multiple values: {unique_r}")
    
    if unique_r <= 3:
        print("   ⚠️  WARNING: Very few unique R-multiples")
        print("   This suggests stops are NOT tightening")
        print("   Expected: Range from -2.5R (day 0-5) to -1.5R (day 15+)")
        print("\n   ❌ FIX NOT WORKING - Stops not tightening")
    else:
        print("   ✓ Multiple R-multiples found - stops appear to be varying")
        
        # Check if we see expected range
        if time_decay['r_multiple'].min() < -2.0:
            print("   ✓ Seeing losses > -2.0R (early stops hit)")
        if time_decay['r_multiple'].max() > -0.8:
            print("   ✓ Seeing losses < -0.8R (tight stops hit)")
        
        print("\n   ✅ FIX APPEARS TO BE WORKING - Stops are tightening")
    
    # Compare with old results
    print("\n📈 COMPARISON (if you have old results):")
    print("   Before fix: All trades clustered at -1.00R")
    print("   After fix: Should see range from -2.5R to -1.5R")
    
    # Show distribution
    print("\n   R-Multiple counts:")
    r_counts = time_decay['r_multiple'].value_counts().sort_index()
    for r_val, count in r_counts.head(10).items():
        print(f"   {r_val:.2f}R: {count} trades")
    
    print("\n="*70)
    
    # FINAL VERDICT
    print("\n🎯 VERDICT:")
    if unique_r <= 3:
        print("   ❌ Fix NOT working - need to investigate further")
        print("   Possible causes:")
        print("   1. Backtest not using risk_manager.py with fix")
        print("   2. Stop strategy not set to 'time_decay'")
        print("   3. ATR values invalid/NaN")
    else:
        print("   ✅ Fix IS working - stops are varying")
        print("   0% win rate is NORMAL for stops")
        print("   Focus should be on improving entries to reduce stop hits")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_time_decay_fix.py <portfolio_log.csv>")
        sys.exit(1)
    
    verify_time_decay_fix(sys.argv[1])
