"""
Debug Regime Chart Creation

Add diagnostic output to see what happens to regime data
during the chart creation process.
"""

import pandas as pd
import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)


def debug_regime_shading(df):
    """
    Replicate the regime shading logic from chart_builder_plotly.py
    with debug output to see what's happening.
    """
    print("\n" + "="*80)
    print("DEBUGGING REGIME SHADING LOGIC")
    print("="*80)
    
    # Check if regime column exists
    if 'Overall_Regime_OK' not in df.columns:
        print("❌ Overall_Regime_OK column not found!")
        return
    
    print(f"\n📊 DataFrame info:")
    print(f"   Total rows: {len(df)}")
    print(f"   Date range: {df.index[0]} to {df.index[-1]}")
    
    # Check last 5 days
    print(f"\n📅 Last 5 days regime values:")
    for idx in df.tail(5).index:
        val = df.loc[idx, 'Overall_Regime_OK']
        print(f"   {idx.strftime('%Y-%m-%d')}: {val} ({'GREEN' if val else 'RED'})")
    
    # Find regime change points (same logic as chart_builder_plotly.py)
    regime_changes = df['Overall_Regime_OK'].ne(df['Overall_Regime_OK'].shift()).fillna(True)
    change_positions = [i for i, idx in enumerate(df.index) if idx in df[regime_changes].index]
    
    print(f"\n🔄 Regime change detection:")
    print(f"   Total changes found: {len(change_positions)}")
    print(f"   Change positions: {change_positions}")
    
    # Show the last few change segments
    print(f"\n📍 Last 3 regime segments:")
    for i in range(max(0, len(change_positions) - 3), len(change_positions)):
        start_pos = change_positions[i]
        end_pos = change_positions[i + 1] if i + 1 < len(change_positions) else len(df)
        
        regime_ok = df.iloc[start_pos]['Overall_Regime_OK']
        start_date = df.index[start_pos]
        
        # CRITICAL: This is what the chart rendering uses
        print(f"\n   Segment {i+1}:")
        print(f"     Start position: {start_pos}")
        print(f"     End position: {end_pos} (EXCLUSIVE in Plotly add_shape)")
        print(f"     Start date: {start_date.strftime('%Y-%m-%d')}")
        print(f"     Regime value at start: {regime_ok} ({'GREEN' if regime_ok else 'RED'})")
        print(f"     X-axis range: x0={start_pos}, x1={end_pos}")
        
        # Show which dates are actually covered
        if end_pos <= len(df):
            covered_dates = df.index[start_pos:end_pos]
            print(f"     Dates covered: {covered_dates[0].strftime('%Y-%m-%d')} to {covered_dates[-1].strftime('%Y-%m-%d')}")
            print(f"     Number of days: {len(covered_dates)}")
    
    # Check the specific case of the last data point
    print(f"\n🎯 CRITICAL: Last data point analysis:")
    last_pos = len(df) - 1
    last_date = df.index[last_pos]
    last_regime = df.iloc[last_pos]['Overall_Regime_OK']
    
    print(f"   Last position: {last_pos}")
    print(f"   Last date: {last_date.strftime('%Y-%m-%d')}")
    print(f"   Last regime value: {last_regime} ({'GREEN' if last_regime else 'RED'})")
    
    # Check if there's a regime change at the last position
    if last_pos in change_positions:
        print(f"   ⚠️  REGIME CHANGE at last position!")
        print(f"   This creates a segment: x0={last_pos}, x1={len(df)}")
        print(f"   x1={len(df)} means the shape extends from position {last_pos} to {len(df)}")
        print(f"   In Plotly, x1 is EXCLUSIVE, so this covers index {last_pos} only")
    else:
        # Find which segment contains the last position
        for i in range(len(change_positions) - 1, -1, -1):
            start_pos = change_positions[i]
            end_pos = change_positions[i + 1] if i + 1 < len(change_positions) else len(df)
            if start_pos <= last_pos < end_pos:
                regime_value = df.iloc[start_pos]['Overall_Regime_OK']
                print(f"   Last position is in segment starting at {start_pos}")
                print(f"   Segment range: x0={start_pos}, x1={end_pos}")
                print(f"   Segment regime: {regime_value} ({'GREEN' if regime_value else 'RED'})")
                break


def main():
    # Load SPY Excel data
    excel_path = os.path.join(parent_dir, 'results_volume/SPY_6mo_20221208_20251125_data.xlsx')
    
    print(f"📂 Loading: {excel_path}")
    df = pd.read_excel(excel_path, sheet_name='Analysis_Data')
    
    # Set Date as index
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    
    print(f"✅ Loaded {len(df)} days")
    
    # Run debug
    debug_regime_shading(df)


if __name__ == "__main__":
    main()
