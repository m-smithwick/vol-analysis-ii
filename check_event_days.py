#!/usr/bin/env python3
"""
Quick script to verify ATR Event Day filter implementation
"""

import pandas as pd
import sys
sys.path.append('.')
from data_manager import get_smart_data
import indicators
import signal_generator

def main():
    print('🧪 Testing ATR Event Day Filter Implementation')
    print('='*50)
    
    # Load the raw data for AAPL
    df = get_smart_data('AAPL', '12mo')
    print(f'📊 Loaded {len(df)} days of raw data for AAPL')

    # Test ATR calculation
    print('\n🔢 Testing ATR calculation...')
    df['TR'], df['ATR20'] = indicators.calculate_atr(df, period=20)
    print(f'✅ ATR calculation complete')
    print(f'   TR range: {df["TR"].min():.2f} to {df["TR"].max():.2f}')
    print(f'   ATR20 range: {df["ATR20"].min():.2f} to {df["ATR20"].max():.2f}')
    print(f'   ATR20 mean: {df["ATR20"].mean():.2f}')

    # Test event day detection (need to calculate Relative_Volume first)
    print('\n🚨 Testing event day detection...')
    df['Relative_Volume'] = indicators.calculate_volume_surprise(df, window=20)
    df['Event_Day'] = indicators.detect_event_days(df, atr_multiplier=2.5, volume_threshold=2.0)
    event_count = df['Event_Day'].sum()
    print(f'✅ Event day detection complete')
    print(f'   Event Days detected: {event_count} out of {len(df)} days ({event_count/len(df)*100:.1f}%)')

    # Show event days if any
    event_days = df[df['Event_Day'] == True]
    if len(event_days) > 0:
        print(f'\n📅 Event Days found:')
        for idx, row in event_days.tail(10).iterrows():
            vol_mean = df['Volume'].rolling(20).mean().loc[idx]
            vol_ratio = row['Volume'] / vol_mean if pd.notna(vol_mean) and vol_mean > 0 else 0
            atr_mean = df['ATR20'].rolling(20).mean().loc[idx] 
            atr_ratio = row['ATR20'] / atr_mean if pd.notna(atr_mean) and atr_mean > 0 else 0
            print(f'   {idx.strftime("%Y-%m-%d")}: ATR={row["ATR20"]:.2f} ({atr_ratio:.1f}x), Volume={vol_ratio:.1f}x, Close=${row["Close"]:.2f}')
    else:
        print('\n✅ No event days detected in this period (normal volatility)')
    
    # Show recent ATR values for context
    print(f'\n📈 Recent ATR20 values:')
    for idx, row in df.tail(5).iterrows():
        vol_mean = df['Volume'].rolling(20).mean().loc[idx]
        vol_ratio = row['Volume'] / vol_mean if pd.notna(vol_mean) and vol_mean > 0 else 0
        print(f'   {idx.strftime("%Y-%m-%d")}: ATR20={row["ATR20"]:.2f}, Vol_Ratio={vol_ratio:.1f}x, Event_Day={row["Event_Day"]}')
    
    # Test entry signal generation with event filtering
    print('\n🎯 Testing entry signal generation with event day filtering...')
    
    # Test one entry signal function to verify filtering works
    df['Strong_Buy_Signal'] = signal_generator.generate_strong_buy_signals(df)
    strong_buy_count = df['Strong_Buy_Signal'].sum()
    
    # Also test without event filtering for comparison
    df_no_filter = df.copy()
    df_no_filter['Event_Day'] = False  # Disable event filtering
    df_no_filter['Strong_Buy_No_Filter'] = signal_generator.generate_strong_buy_signals(df_no_filter)
    no_filter_count = df_no_filter['Strong_Buy_No_Filter'].sum()
    
    print(f'✅ Entry signal filtering test complete')
    print(f'   Strong Buy signals WITH event filtering: {strong_buy_count}')
    print(f'   Strong Buy signals WITHOUT event filtering: {no_filter_count}')
    
    if event_count > 0 and no_filter_count > strong_buy_count:
        print(f'   ✅ Event day filtering is working! ({no_filter_count - strong_buy_count} signals filtered)')
    elif event_count == 0:
        print(f'   ✅ No event days to filter (both counts should be equal)')
    else:
        print(f'   ⚠️  Event day filtering may not be working as expected')
    
    # Show any recent entry signals
    print(f'\n📊 Recent entry signals:')
    recent_signals = False
    for idx, row in df.tail(10).iterrows():
        if row['Strong_Buy_Signal']:
            recent_signals = True
            print(f'   {idx.strftime("%Y-%m-%d")}: Strong Buy - Event_Day={row["Event_Day"]}, Price=${row["Close"]:.2f}')
    
    if not recent_signals:
        print('   No recent Strong Buy signals found')
    
    print(f'\n✅ ATR Event Day Filter implementation test complete!')

if __name__ == '__main__':
    main()
