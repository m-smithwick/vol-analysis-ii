#!/usr/bin/env python3
"""
Simplified test script for timezone issues
"""

from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

def test_timezone_normalization():
    """Test consistent timezone handling with AAPL data"""
    print("\n===== SIMPLIFIED TIMEZONE TEST =====")
    
    # Download a small amount of data directly
    print("Downloading AAPL data for a single day...")
    ticker = "AAPL"
    
    # This will have timezone-aware index
    df = yf.download(ticker, period="1d", interval="1h", auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    
    # Check if the index is timezone-aware
    print(f"Original data index timezone: {df.index.tzinfo}")
    
    # Normalize to timezone-naive
    print("\nNormalizing to timezone-naive...")
    if df.index.tzinfo is not None:
        df_naive = df.copy()
        df_naive.index = df_naive.index.tz_localize(None)
        print(f"Normalized data index timezone: {df_naive.index.tzinfo}")
        
        # Try combining with another dataframe
        print("\nTrying to combine with another dataframe...")
        # Create a simple dataframe with timezone-naive index
        dates = [datetime.now() + timedelta(hours=i) for i in range(5)]
        df2 = pd.DataFrame({'Close': [100, 101, 102, 103, 104]}, index=dates)
        print(f"Second dataframe index timezone: {df2.index.tzinfo}")
        
        # This would fail if we don't normalize
        print("\nAttempting to concatenate without normalization...")
        try:
            # This will fail due to timezone mismatch
            combined = pd.concat([df, df2])
            combined = combined[~combined.index.duplicated(keep='last')]
            combined.sort_index(inplace=True)
            print("✅ Combined without normalization (this should not happen)")
        except TypeError as e:
            print(f"❌ Error as expected: {str(e)}")
            
        # Try again with proper normalization
        print("\nAttempting to concatenate with normalization...")
        try:
            # This should succeed with normalization
            combined = pd.concat([df_naive, df2])
            combined = combined[~combined.index.duplicated(keep='last')]
            combined.sort_index(inplace=True)
            print("✅ Combined successfully with normalization")
            print(f"Combined index timezone: {combined.index.tzinfo}")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    else:
        print("Data is already timezone-naive")
    
    print("===== TEST COMPLETE =====")

if __name__ == "__main__":
    test_timezone_normalization()
