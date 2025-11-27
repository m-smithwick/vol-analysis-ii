"""
Check if buffer data has all required columns for charting.
"""

import pandas as pd
import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)


def check_columns(df, label):
    """Check which columns exist and their data types."""
    print(f"\n{'='*80}")
    print(f"{label}")
    print("="*80)
    
    required_for_chart = [
        'Close', 'Volume', 'VWAP', 'Support_Level', 'OBV', 'AD_Line', 
        'OBV_MA', 'AD_MA', 'Volume_MA', 'Phase', 'Accumulation_Score', 
        'Exit_Score', 'Strong_Buy_display', 'Moderate_Buy_display', 
        'Stealth_Accumulation_display', 'Confluence_Signal_display', 
        'Volume_Breakout_display', 'Profit_Taking_display', 
        'Distribution_Warning_display', 'Sell_Signal_display', 
        'Momentum_Exhaustion_display', 'Stop_Loss_display',
        'Recent_Swing_Low', 'Recent_Swing_High', 'SMA_50', 'SMA_200',
        'Event_Day', 'Overall_Regime_OK'
    ]
    
    print(f"\n📋 Column check:")
    missing = []
    for col in required_for_chart:
        if col in df.columns:
            dtype = df[col].dtype
            has_nan = df[col].isna().any()
            print(f"   ✅ {col}: {dtype} (NaN: {has_nan})")
        else:
            print(f"   ❌ {col}: MISSING")
            missing.append(col)
    
    if missing:
        print(f"\n⚠️  Missing columns: {missing}")
    else:
        print(f"\n✅ All required columns present")
    
    return len(missing) == 0


def main():
    # Load real SPY data
    excel_path = os.path.join(parent_dir, 'results_volume/SPY_6mo_20221208_20251125_data.xlsx')
    df = pd.read_excel(excel_path, sheet_name='Analysis_Data')
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    
    # Set regime
    df['Overall_Regime_OK'] = False
    df.iloc[-1, df.columns.get_loc('Overall_Regime_OK')] = True
    
    # Check original data
    check_columns(df, "ORIGINAL DATA (809 days)")
    
    # Add buffer days
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
    
    # Check buffer data
    check_columns(df_with_buffer, "WITH BUFFER DAYS (814 days)")
    
    # Check last few rows in detail
    print(f"\n{'='*80}")
    print("LAST 5 ROWS DETAIL")
    print("="*80)
    for idx in df_with_buffer.tail(5).index:
        pos = df_with_buffer.index.get_loc(idx)
        print(f"\nPosition {pos}: {idx.strftime('%Y-%m-%d')}")
        print(f"   Overall_Regime_OK: {df_with_buffer.loc[idx, 'Overall_Regime_OK']}")
        print(f"   Close: {df_with_buffer.loc[idx, 'Close']}")
        print(f"   Volume: {df_with_buffer.loc[idx, 'Volume']}")
        print(f"   SMA_50: {df_with_buffer.loc[idx, 'SMA_50']}")
        print(f"   Recent_Swing_Low: {df_with_buffer.loc[idx, 'Recent_Swing_Low']}")


if __name__ == "__main__":
    main()
