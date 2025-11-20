#!/usr/bin/env python3
"""
Check XLK trend analysis to understand why sector regime is always True.
"""

import pandas as pd
from data_manager import get_smart_data
from regime_filter import get_sector_etf

def check_sector_trend():
    ticker = 'AAPL'
    sector_etf = get_sector_etf(ticker)
    print(f'AAPL maps to sector ETF: {sector_etf}')

    # Load XLK data
    data = get_smart_data(sector_etf, period='12mo')
    print(f'\nXLK data: {len(data)} rows from {data.index.min().date()} to {data.index.max().date()}')

    # Calculate 50-day MA
    data['MA50'] = data['Close'].rolling(50, min_periods=50).mean()
    data['Above_50MA'] = data['Close'] > data['MA50']

    # Check recent values
    recent = data.dropna(subset=['MA50']).tail(10)
    print(f'\nRecent XLK vs 50MA:')
    for idx, row in recent.iterrows():
        above = 'ABOVE' if row['Above_50MA'] else 'BELOW'
        print(f'{idx.date()}: ${row["Close"]:.2f} vs ${row["MA50"]:.2f} ({above})')

    # Check if ALL values are above 50MA
    all_data = data.dropna(subset=['MA50'])
    above_count = all_data['Above_50MA'].sum()
    total_count = len(all_data)
    print(f'\nSummary: {above_count}/{total_count} days above 50MA ({above_count/total_count*100:.1f}%)')

    # Check for any days below 50MA
    below_days = all_data[~all_data['Above_50MA']]
    if len(below_days) > 0:
        print(f'\nDays BELOW 50MA:')
        for idx, row in below_days.head().iterrows():
            print(f'  {idx.date()}: ${row["Close"]:.2f} vs ${row["MA50"]:.2f}')
    else:
        print('\nNo days found below 50MA - XLK has been in strong uptrend!')
        
    return above_count == total_count

if __name__ == '__main__':
    all_above = check_sector_trend()
    if all_above:
        print('\n✅ CONCLUSION: XLK sector regime is legitimately always True')
        print('   This is NOT a bug - XLK has been above 50MA for entire period!')
    else:
        print('\n⚠️  CONCLUSION: XLK has mixed regime - there may be a calculation issue')
