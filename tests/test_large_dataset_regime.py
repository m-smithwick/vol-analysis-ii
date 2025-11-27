"""
Test Large Dataset with Last Position Regime Change

Replicate the exact SPY scenario: 809 days with regime change at position 808.
"""

import pandas as pd
import sys
import os
import numpy as np

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from chart_builder_plotly import generate_analysis_chart


def create_large_test_data():
    """
    Create 809 days of test data with regime change at position 808 (last position).
    This exactly replicates the SPY scenario.
    """
    # Load real SPY data as template
    excel_path = os.path.join(parent_dir, 'results_volume/SPY_6mo_20221208_20251125_data.xlsx')
    df = pd.read_excel(excel_path, sheet_name='Analysis_Data')
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    
    # Modify regime: All FALSE except last day TRUE
    df['Overall_Regime_OK'] = False
    df.iloc[-1, df.columns.get_loc('Overall_Regime_OK')] = True
    
    print("="*80)
    print(f"LARGE DATASET TEST: {len(df)} days")
    print("="*80)
    print(f"\n📊 Dataset size: {len(df)} days (same as SPY)")
    print(f"   Last position: {len(df) - 1}")
    print(f"   Regime pattern: ALL RED except LAST DAY GREEN")
    
    # Verify the setup
    print(f"\n📅 Last 5 days regime:")
    for idx in df.tail(5).index:
        val = df.loc[idx, 'Overall_Regime_OK']
        pos = df.index.get_loc(idx)
        print(f"   Position {pos}: {idx.strftime('%Y-%m-%d')} = {val} ({'GREEN' if val else 'RED'})")
    
    return df


def main():
    # Create test data
    df = create_large_test_data()
    
    # Generate chart
    output_path = os.path.join(parent_dir, 'results_volume/TEST_LARGE_809days_last_green.html')
    
    print(f"\n📈 Generating chart...")
    try:
        generate_analysis_chart(
            df=df,
            ticker="TEST_809days",
            period="809d",
            save_path=output_path,
            show=False
        )
        
        print(f"✅ Chart saved to: {output_path}")
        print(f"\n{'='*80}")
        print("🔍 VERIFICATION:")
        print("="*80)
        print(f"Data setup: 809 days, ALL RED except last day (position 808) GREEN")
        print(f"\n📂 Open: TEST_LARGE_809days_last_green.html")
        print(f"   Expected: Last bar (Nov 25) should be GREEN")
        print(f"   If last bar is RED → BUG CONFIRMED with large datasets")
        print(f"   If last bar is GREEN → Bug is specific to SPY data structure")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
