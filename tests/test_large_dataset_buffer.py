"""
Test Large Dataset with Buffer Days

Add empty buffer days beyond the last real data point to test if Plotly
has issues rendering shapes that extend to the exact end of the dataset.
"""

import pandas as pd
import sys
import os
import numpy as np

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from chart_builder_plotly import generate_analysis_chart


def create_test_data_with_buffer(buffer_days=5):
    """
    Load real SPY data and add buffer days at the end.
    
    Args:
        buffer_days: Number of empty days to add at the end
    """
    # Load real SPY data as template
    excel_path = os.path.join(parent_dir, 'results_volume/SPY_6mo_20221208_20251125_data.xlsx')
    df = pd.read_excel(excel_path, sheet_name='Analysis_Data')
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    
    # Verify regime: All FALSE except last day TRUE
    df['Overall_Regime_OK'] = False
    df.iloc[-1, df.columns.get_loc('Overall_Regime_OK')] = True
    
    print("="*80)
    print(f"BUFFER DAY TEST: {len(df)} real days + {buffer_days} buffer days")
    print("="*80)
    
    # Store original last date info
    last_real_date = df.index[-1]
    last_real_pos = len(df) - 1
    last_regime = df.iloc[-1]['Overall_Regime_OK']
    last_close = df.iloc[-1]['Close']
    
    print(f"\n📅 Last REAL trading day:")
    print(f"   Position: {last_real_pos}")
    print(f"   Date: {last_real_date.strftime('%Y-%m-%d')}")
    print(f"   Regime: {last_regime} ({'GREEN' if last_regime else 'RED'})")
    print(f"   Close: ${last_close:.2f}")
    
    # Add buffer days
    buffer_dates = pd.date_range(
        start=last_real_date + pd.Timedelta(days=1), 
        periods=buffer_days, 
        freq='D'
    )
    
    buffer_rows = []
    for date in buffer_dates:
        # Copy last row and modify for buffer
        row = df.iloc[-1].copy()
        row['Close'] = last_close  # Keep price constant
        row['High'] = last_close
        row['Low'] = last_close
        row['Open'] = last_close
        row['Overall_Regime_OK'] = last_regime  # Keep regime status
        row['Volume'] = 0  # Zero volume marks it as buffer
        row['VWAP'] = last_close
        buffer_rows.append(row)
    
    # Create buffer DataFrame
    buffer_df = pd.DataFrame(buffer_rows, index=buffer_dates)
    
    # Concatenate
    df_with_buffer = pd.concat([df, buffer_df])
    
    print(f"\n📊 Dataset after adding buffer:")
    print(f"   Total days: {len(df_with_buffer)} ({len(df)} real + {buffer_days} buffer)")
    print(f"   Last position: {len(df_with_buffer) - 1}")
    
    print(f"\n📅 Last 7 days (including buffer):")
    for i, idx in enumerate(df_with_buffer.tail(7).index):
        pos = len(df_with_buffer) - 7 + i
        val = df_with_buffer.loc[idx, 'Overall_Regime_OK']
        volume = df_with_buffer.loc[idx, 'Volume']
        is_buffer = volume == 0
        marker = "🔲 [BUFFER]" if is_buffer else "📅 [REAL]"
        print(f"   Position {pos}: {idx.strftime('%Y-%m-%d')} = {val} ({'GREEN' if val else 'RED'}) {marker}")
    
    return df_with_buffer, last_real_date


def main():
    # Test with 5 buffer days
    df, last_real_date = create_test_data_with_buffer(buffer_days=5)
    
    # Generate chart
    output_path = os.path.join(parent_dir, 'results_volume/TEST_BUFFER_809days_plus_5.html')
    
    print(f"\n📈 Generating chart...")
    try:
        generate_analysis_chart(
            df=df,
            ticker="TEST_BUFFER",
            period="809d+5buffer",
            save_path=output_path,
            show=False
        )
        
        print(f"✅ Chart saved to: {output_path}")
        print(f"\n{'='*80}")
        print("🔍 VERIFICATION:")
        print("="*80)
        print(f"📂 Open: TEST_BUFFER_809days_plus_5.html")
        print(f"\n🎯 Check the last REAL trading day ({last_real_date.strftime('%Y-%m-%d')}):")
        print(f"   Expected: Should be GREEN (regime=TRUE)")
        print(f"   Buffer days after it should also be GREEN")
        print(f"\n💡 If last real day is now GREEN:")
        print(f"   → Confirms Plotly has boundary rendering issue")
        print(f"   → Fix: Always extend shapes slightly beyond data OR add buffer")
        print(f"\n💡 If last real day is still RED:")
        print(f"   → Problem is more complex than boundary rendering")
        print(f"   → Need to investigate subplot/shape layer interaction")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
