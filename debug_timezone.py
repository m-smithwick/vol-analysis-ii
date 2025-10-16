#!/usr/bin/env python3
"""
Debug script to identify timezone issues in the news analysis code
"""

from datetime import datetime, timedelta
import pandas as pd
import pytz
import sys

# Import the modules we need to test
from data_manager import get_intraday_data
from news_influence import calculate_news_influence_score, analyze_multiple_days
from news_analysis import analyze_news_influence

def print_timezone_info(dt, name):
    """Print timezone information about a datetime object"""
    print(f"{name}: {dt} | TZ: {dt.tzinfo}")

def debug_timezone_issue():
    """Debug the timezone issue in the news analysis code"""
    print("\n===== TIMEZONE DEBUG =====")
    
    # Get today's date
    today = datetime.now()
    print_timezone_info(today, "Today")
    
    # Try with a single specific day
    test_day = datetime.now() - timedelta(days=1)
    print(f"\nTesting with date: {test_day.strftime('%Y-%m-%d')}")
    
    try:
        # Get intraday data for AAPL
        print("\nFetching intraday data...")
        df = get_intraday_data(
            ticker="AAPL",
            days=3,
            interval="1h"
        )
        
        print(f"Data index timezone: {df.index.tzinfo}")
        print(f"First timestamp: {df.index[0]}, tzinfo: {df.index[0].tzinfo}")
        print(f"Last timestamp: {df.index[-1]}, tzinfo: {df.index[-1].tzinfo}")
        
        # Test the calculate_news_influence_score function
        print("\nTesting calculate_news_influence_score...")
        try:
            # Explicitly make test_day timezone-naive
            if test_day.tzinfo is not None:
                test_day = test_day.replace(tzinfo=None)
                
            # Filter data to relevant range for the test
            date_from = test_day - timedelta(days=1)
            date_to = test_day + timedelta(days=1)
            
            # Ensure dates are timezone-naive for consistent comparison
            if df.index.tzinfo is not None:
                print("Converting dataframe index to timezone-naive...")
                df.index = df.index.tz_localize(None)
            
            print(f"Date from: {date_from} (tzinfo: {date_from.tzinfo})")
            print(f"Date to: {date_to} (tzinfo: {date_to.tzinfo})")
            
            # Filter to relevant date range
            mask = (df.index >= date_from) & (df.index <= date_to)
            test_df = df.loc[mask]
            
            if test_df.empty:
                print("⚠️ No data available for selected date range")
            else:
                print(f"Filtered data range: {test_df.index[0]} to {test_df.index[-1]}")
                
                result = calculate_news_influence_score(test_df, "AAPL", test_day)
                print("✅ calculate_news_influence_score worked successfully")
                print(f"Classification: {result['classification']}")
        except Exception as e:
            print(f"❌ Error in calculate_news_influence_score: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Test analyze_multiple_days
        print("\nTesting analyze_multiple_days...")
        try:
            start_date = datetime.now() - timedelta(days=5)
            end_date = datetime.now() - timedelta(days=2)
            
            # Explicitly make dates timezone-naive
            if start_date.tzinfo is not None:
                start_date = start_date.replace(tzinfo=None)
            if end_date.tzinfo is not None:
                end_date = end_date.replace(tzinfo=None)
                
            print(f"Start date: {start_date} (tzinfo: {start_date.tzinfo})")
            print(f"End date: {end_date} (tzinfo: {end_date.tzinfo})")
            
            results = analyze_multiple_days(
                ticker="AAPL",
                start_date=start_date,
                end_date=end_date,
                interval="1h"
            )
            
            print("✅ analyze_multiple_days worked successfully")
            print(f"Results: {len(results)} days analyzed")
        except Exception as e:
            print(f"❌ Error in analyze_multiple_days: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Test full analyze_news_influence function
        print("\nTesting analyze_news_influence...")
        try:
            results = analyze_news_influence(
                ticker="AAPL",
                days_back=3,
                interval="1h",
                save_to_file=False
            )
            
            print("✅ analyze_news_influence worked successfully")
            print(f"Results: {len(results) if results else 0} days analyzed")
        except Exception as e:
            print(f"❌ Error in analyze_news_influence: {str(e)}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ Error during debugging: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n===== END DEBUG =====")

if __name__ == "__main__":
    debug_timezone_issue()
