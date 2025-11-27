"""
Debug Buffer Day Test

See what happens to regime detection when we add buffer days.
"""

import pandas as pd
import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)


def debug_buffer_regime(df):
    """Debug regime change detection with buffer days."""
    
    print("\n" + "="*80)
    print("DEBUGGING REGIME WITH BUFFER DAYS")
    print("="*80)
    
    # Check if regime column exists
    if 'Overall_Regime_OK' not in df.columns:
        print("❌ Overall_Regime_OK column not found!")
        return
    
    print(f"\n📊 DataFrame info:")
    print(f"   Total rows: {len(df)}")
    print(f"   Date range: {df.index[0]} to {df.index[-1]}")
    
    # Check data types
    print(f"\n🔍 Data type check:")
    print(f"   Overall_Regime_OK dtype: {df['Overall_Regime_OK'].dtype}")
    print(f"   Contains NaN: {df['Overall_Regime_OK'].isna().any()}")
    
    # Show last 10 days
    print(f"\n📅 Last 10 days regime values:")
    for idx in df.tail(10).index:
        pos = df.index.get_loc(idx)
        val = df.loc[idx, 'Overall_Regime_OK']
        volume = df.loc[idx, 'Volume']
        is_buffer = volume == 0
        marker = "🔲 [BUFFER]" if is_buffer else "📅 [REAL]"
        print(f"   Position {pos}: {idx.strftime('%Y-%m-%d')} = {val} ({'GREEN' if val else 'RED'}) {marker}")
    
    # Replicate regime change detection from chart_builder_plotly.py
    print(f"\n🔄 Regime change detection (chart_builder_plotly.py logic):")
    regime_changes = df['Overall_Regime_OK'].ne(df['Overall_Regime_OK'].shift()).fillna(True)
    
    print(f"   Total change points: {regime_changes.sum()}")
    print(f"   Change detection dtype: {regime_changes.dtype}")
    
    # Show where changes occur
    change_indices = df[regime_changes].index
    print(f"\n   Change points:")
    for idx in change_indices:
        pos = df.index.get_loc(idx)
        val = df.loc[idx, 'Overall_Regime_OK']
        print(f"      Position {pos}: {idx.strftime('%Y-%m-%d')} = {val} ({'GREEN' if val else 'RED'})")
    
    # Get positions for rendering
    change_positions = [i for i, idx in enumerate(df.index) if idx in df[regime_changes].index]
    print(f"\n   Change positions for rendering: {change_positions}")
    
    # Show segments
    print(f"\n📍 Regime segments for chart:")
    for i in range(len(change_positions)):
        start_pos = change_positions[i]
        end_pos = change_positions[i + 1] if i + 1 < len(change_positions) else len(df)
        
        regime_ok = df.iloc[start_pos]['Overall_Regime_OK']
        start_date = df.index[start_pos]
        
        print(f"\n   Segment {i+1}:")
        print(f"     x0={start_pos}, x1={end_pos}")
        print(f"     Start: {start_date.strftime('%Y-%m-%d')}")
        print(f"     Regime: {regime_ok} ({'GREEN' if regime_ok else 'RED'})")
        print(f"     Covers positions {start_pos} to {end_pos-1}")


def main():
    # Load real SPY data
    excel_path = os.path.join(parent_dir, 'results_volume/SPY_6mo_20221208_20251125_data.xlsx')
    df = pd.read_excel(excel_path, sheet_name='Analysis_Data')
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    
    # Set regime: All FALSE except last day TRUE
    df['Overall_Regime_OK'] = False
    df.iloc[-1, df.columns.get_loc('Overall_Regime_OK')] = True
    
    print("="*80)
    print("ORIGINAL DATA (809 days)")
    print("="*80)
    debug_buffer_regime(df)
    
    # Now add buffer days
    last_real_date = df.index[-1]
    last_regime = df.iloc[-1]['Overall_Regime_OK']
    last_close = df.iloc[-1]['Close']
    
    buffer_dates = pd.date_range(
        start=last_real_date + pd.Timedelta(days=1), 
        periods=5, 
        freq='D'
    )
    
    buffer_rows = []
    for date in buffer_dates:
        row = df.iloc[-1].copy()
        row['Close'] = last_close
        row['High'] = last_close
        row['Low'] = last_close
        row['Open'] = last_close
        row['Overall_Regime_OK'] = last_regime
        row['Volume'] = 0
        row['VWAP'] = last_close
        buffer_rows.append(row)
    
    buffer_df = pd.DataFrame(buffer_rows, index=buffer_dates)
    df_with_buffer = pd.concat([df, buffer_df])
    
    print("\n\n" + "="*80)
    print("WITH BUFFER DAYS (809 + 5 = 814 days)")
    print("="*80)
    debug_buffer_regime(df_with_buffer)


if __name__ == "__main__":
    main()
