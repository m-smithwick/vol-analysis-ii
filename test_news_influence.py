#!/usr/bin/env python3
"""
Test script to verify the timezone fixes for news_influence module.
"""

import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import pytz

# Import the fixed modules
from data_manager import get_intraday_data, clear_cache
from news_influence import analyze_multiple_days

def test_timezone_handling():
    """Test that the timezone fix works for the specific error case."""
    
    # Clear any existing cache for AAPL
    print("Clearing AAPL cache...")
    clear_cache(ticker="AAPL")
    
    # Define the test dates
    today = datetime.now()
    start_date = today - timedelta(days=10)
    end_date = today
    
    print(f"\n🔍 Testing date handling...")
    print(f"Test period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Print timezone information for debugging
    print(f"Current time (naive): {datetime.now()}")
    print(f"Current time (UTC): {datetime.now(pytz.UTC)}")
    
    # Test fetching intraday data
    print("\n📈 Fetching intraday data for AAPL...")
    try:
        df = get_intraday_data(ticker="AAPL", days=10, interval="1h")
        print(f"✅ Successfully fetched {len(df)} data points")
        print(f"Date range: {df.index[0]} to {df.index[-1]}")
        print(f"Index timezone info: {df.index.tzinfo}")
        
        # Check if any rows have timezone-aware datetimes
        tz_aware = any(idx.tzinfo is not None for idx in df.index if hasattr(idx, 'tzinfo'))
        print(f"Any timezone-aware dates in index: {tz_aware}")
    except Exception as e:
        print(f"❌ Error fetching intraday data: {str(e)}")
        return
    
    # Test the analyze_multiple_days function
    print("\n📊 Testing analyze_multiple_days with AAPL...")
    try:
        results = analyze_multiple_days(
            ticker="AAPL",
            start_date=start_date, 
            end_date=end_date,
            interval="1h"
        )
        print(f"✅ Successfully analyzed {len(results)} days")
        
        # Print a summary of the results
        for result in results:
            print(f"  - {result['date']}: Classification: {result['classification']}, Confidence: {result['confidence']:.2f}")
            
        print("\n🎉 All tests passed! The timezone fixes are working.")
    except Exception as e:
        print(f"❌ Error in analyze_multiple_days: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_timezone_handling()
