#!/usr/bin/env python3
"""
Debug the specific calculation issue in calculate_historical_regime_series.
"""

import pandas as pd
import numpy as np
from regime_filter import load_benchmark_data, get_sector_etf
from data_manager import get_smart_data

def debug_regime_calculation():
    """Debug step-by-step regime calculation."""
    
    ticker = 'AAPL'
    print(f"Debugging regime calculation for {ticker}")
    
    # Create test DataFrame (same as in real backtest)
    df = get_smart_data(ticker, period='12mo')
    test_df = df.iloc[-60:].copy()  # Last 60 days: 2025-08-22 to 2025-11-14
    
    print(f"Test DataFrame: {len(test_df)} rows from {test_df.index.min().date()} to {test_df.index.max().date()}")
    
    # Step 1: Calculate date range with buffer (like in the function)
    start_date = test_df.index.min() - pd.DateOffset(months=12)  # Extra buffer for 200-day MA
    end_date = test_df.index.max()
    
    print(f"Date range for benchmarks: {start_date.date()} to {end_date.date()}")
    
    # Step 2: Load sector ETF data
    sector_etf = get_sector_etf(ticker)
    print(f"Sector ETF: {sector_etf}")
    
    sector_data = load_benchmark_data(sector_etf, period=None,
                                     start_date=start_date,
                                     end_date=end_date)
    
    print(f"Sector data loaded: {len(sector_data)} rows from {sector_data.index.min().date()} to {sector_data.index.max().date()}")
    
    # Step 3: Calculate 50-day MA
    sector_data['MA50'] = sector_data['Close'].rolling(50, min_periods=50).mean()
    sector_data['Sector_Regime_OK'] = sector_data['Close'] > sector_data['MA50']
    
    # Check values in the test period
    test_period_sector = sector_data[
        (sector_data.index >= test_df.index.min()) & 
        (sector_data.index <= test_df.index.max())
    ].copy()
    
    print(f"\nSector data in test period:")
    print(f"  Rows: {len(test_period_sector)}")
    if len(test_period_sector) > 0:
        above_count = test_period_sector['Sector_Regime_OK'].sum()
        total_count = len(test_period_sector.dropna(subset=['MA50']))
        print(f"  Above 50MA: {above_count}/{total_count} ({above_count/total_count*100:.1f}%)")
        
        # Show some examples
        print(f"\nFirst 5 and last 5 values:")
        sample_data = pd.concat([
            test_period_sector.dropna(subset=['MA50']).head(5),
            test_period_sector.dropna(subset=['MA50']).tail(5)
        ])
        
        for idx, row in sample_data.iterrows():
            above = 'ABOVE' if row['Sector_Regime_OK'] else 'BELOW'
            print(f"    {idx.date()}: ${row['Close']:.2f} vs ${row['MA50']:.2f} ({above})")
    
    # Step 4: Test the timezone normalization and reindexing (the likely bug)
    print(f"\n🔍 TESTING REINDEXING LOGIC:")
    
    # Normalize timezones - convert all to timezone-naive for comparison
    if sector_data.index.tz is not None:
        print(f"  Sector data has timezone: {sector_data.index.tz}")
        sector_data.index = sector_data.index.tz_localize(None)
    else:
        print(f"  Sector data is timezone-naive")
    
    # Also normalize the target DataFrame index
    df_index_normalized = test_df.index
    if df_index_normalized.tz is not None:
        print(f"  Test DF has timezone: {df_index_normalized.tz}")
        df_index_normalized = df_index_normalized.tz_localize(None)
    else:
        print(f"  Test DF is timezone-naive")
    
    print(f"  Test DF index range: {df_index_normalized.min().date()} to {df_index_normalized.max().date()}")
    print(f"  Sector index range: {sector_data.index.min().date()} to {sector_data.index.max().date()}")
    
    # Step 5: Do the reindexing (this is where the bug likely is)
    print(f"\n📊 REINDEXING TEST:")
    
    sector_regime_raw = sector_data['Sector_Regime_OK']
    print(f"  Raw sector regime: {sector_regime_raw.sum()}/{len(sector_regime_raw.dropna())} True")
    
    sector_regime_reindexed = sector_regime_raw.reindex(
        df_index_normalized, 
        method='ffill'  # Forward-fill for non-trading days
    ).fillna(False)  # Conservative: missing data = regime FAIL
    
    print(f"  After reindexing: {sector_regime_reindexed.sum()}/{len(sector_regime_reindexed)} True")
    
    # Check which dates don't have exact matches
    print(f"\n🔍 DATE ALIGNMENT CHECK:")
    
    test_dates = set(df_index_normalized)
    sector_dates = set(sector_data.index)
    
    missing_in_sector = test_dates - sector_dates
    if missing_in_sector:
        print(f"  Dates in test DF but missing in sector data: {len(missing_in_sector)}")
        for date in sorted(missing_in_sector)[:5]:  # Show first 5
            print(f"    {date.date()}")
    else:
        print(f"  ✅ All test dates have sector data")
    
    # Show the final result comparison
    print(f"\n📊 FINAL COMPARISON:")
    print(f"  Expected (direct calculation): {above_count}/{total_count} True")
    print(f"  Got (reindexed): {sector_regime_reindexed.sum()}/{len(sector_regime_reindexed)} True")
    
    if sector_regime_reindexed.sum() == len(sector_regime_reindexed):
        print(f"  🚨 BUG CONFIRMED: Reindexing is causing all True values!")
        
        # Let's debug the reindexing step by step
        print(f"\n🔍 DETAILED REINDEXING DEBUG:")
        
        # Check what happens with each test date
        for i, test_date in enumerate(df_index_normalized[:10]):  # First 10 dates
            # Find the closest sector date
            sector_before = sector_data[sector_data.index <= test_date]
            if len(sector_before) > 0:
                closest_sector_date = sector_before.index.max()
                closest_regime_value = sector_data.loc[closest_sector_date, 'Sector_Regime_OK']
                reindexed_value = sector_regime_reindexed.iloc[i]
                
                print(f"    {test_date.date()}: closest sector {closest_sector_date.date()} = {closest_regime_value}, reindexed = {reindexed_value}")
            else:
                print(f"    {test_date.date()}: no sector data before this date")
    else:
        print(f"  ✅ Reindexing appears to be working correctly")

if __name__ == '__main__':
    debug_regime_calculation()
