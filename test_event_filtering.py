#!/usr/bin/env python3
"""
Simple test to verify event day filtering logic works
"""

import pandas as pd
import numpy as np

def test_event_filtering():
    print('🧪 Testing Event Day Filtering Logic')
    print('='*40)
    
    # Create sample data with some event days
    dates = pd.date_range('2025-01-01', periods=10, freq='D')
    df = pd.DataFrame({
        'Date': dates,
        'Close': [100, 102, 105, 103, 101, 98, 95, 97, 99, 101],
        'Event_Day': [False, False, True, False, False, True, False, False, False, False]
    })
    df.set_index('Date', inplace=True)
    
    print(f'📊 Sample data created with {df["Event_Day"].sum()} event days')
    
    # Test the filtering logic used in signal_generator.py
    # This is the exact code from generate_strong_buy_signals()
    event_day_filter = ~df['Event_Day'] if 'Event_Day' in df.columns else True
    
    # Create some mock entry signals
    mock_signals = pd.Series([True, True, True, True, True, True, True, True, True, True], index=df.index)
    
    # Apply event day filter
    filtered_signals = mock_signals & event_day_filter
    
    print(f'\n📈 Results:')
    print(f'   Original signals: {mock_signals.sum()}')
    print(f'   Filtered signals: {filtered_signals.sum()}')
    print(f'   Signals filtered out: {mock_signals.sum() - filtered_signals.sum()}')
    
    print(f'\n📅 Signal details:')
    for date, row in df.iterrows():
        original = mock_signals[date]
        filtered = filtered_signals[date]
        event_day = row['Event_Day']
        status = 'FILTERED' if original and not filtered else 'ALLOWED'
        print(f'   {date.strftime("%Y-%m-%d")}: Event_Day={event_day}, Signal={status}')
    
    # Verify filtering worked correctly
    expected_filtered = df['Event_Day'].sum()
    actual_filtered = mock_signals.sum() - filtered_signals.sum()
    
    if expected_filtered == actual_filtered:
        print(f'\n✅ Event day filtering working correctly!')
        print(f'   Expected {expected_filtered} signals filtered, got {actual_filtered}')
    else:
        print(f'\n❌ Event day filtering not working correctly!')
        print(f'   Expected {expected_filtered} signals filtered, got {actual_filtered}')

if __name__ == '__main__':
    test_event_filtering()
